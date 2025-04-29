import React, { useState, useEffect, useContext, useRef, useCallback } from "react";
import apiClient, { gameApi } from "../../api/apiClient";
import { useParams, useNavigate } from "react-router-dom";
import { UserContext } from "../../context/UserContext";
import { getApiBaseUrl } from "../../utils/config";
import axios from '../../utils/axios-config';
import ChatBox from '../Chat/ChatBox';
import { ChatMessage } from '../../types/chat';
import { useToast } from '@chakra-ui/react';
import "./GameBoard.css";

interface Player {
  id: string;
  username: string;
  score: number;
  role?: string;
}

interface GameState {
  currentWord: string;
  associations?: string[];
  players: { id: string; username: string; score: number, role: string; }[];
  round: number;
  status: 'WAITING' | 'PLAYING' | 'FINISHED';
  timeLeft?: number;
  currentPlayer?: string;
  rounds_total: number;
  time_per_round?: number;
}

const GameBoard: React.FC = () => {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [guess, setGuess] = useState<string>("");
  const { roomCode } = useParams<{ roomCode: string }>();
  const { user, setUser } = useContext(UserContext);
  const navigate = useNavigate();
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const [timerStartTime, setTimerStartTime] = useState<number | null>(null);
  const [timePerRound, setTimePerRound] = useState<number>(60);
  const wsRef = useRef<WebSocket | null>(null);
  const apiBaseUrl = getApiBaseUrl();
  const wsBaseUrl = apiBaseUrl.replace('http', 'ws');
  const timerIntervalRef = useRef<number | null>(null);
  const [initialLoadComplete, setInitialLoadComplete] = useState<boolean>(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  
  const isConnecting = useRef(false);
  const isComponentMounted = useRef(true);
  const connectionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const toast = useToast();

  // Устанавливаем isComponentMounted в false при размонтировании компонента
  useEffect(() => {
    // Компонент смонтирован
    isComponentMounted.current = true;
    
    return () => {
      // Компонент размонтирован - очищаем все таймауты
      isComponentMounted.current = false;
      
      if (connectionTimeoutRef.current) {
        clearTimeout(connectionTimeoutRef.current);
        connectionTimeoutRef.current = null;
      }
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    console.log("User context in GameBoard:", user);
  }, [user]);

  useEffect(() => {
    // Проверяем наличие пользователя в контексте
    if (!user) {
      console.log('Пользователь не найден в контексте, пытаемся восстановить из localStorage');
      
      try {
        const savedUser = localStorage.getItem('user');
        if (savedUser) {
          const parsedUser = JSON.parse(savedUser);
          console.log('Восстановлен пользователь из localStorage:', parsedUser);
          
          setUser(parsedUser);
        } else {
          console.log('Пользователь не найден в localStorage');
        }
      } catch (error) {
        console.error('Ошибка при восстановлении пользователя:', error);
      }
    }
  }, [user, setUser]);

  // Мемоизированная функция для получения состояния игры
  const fetchGameState = useCallback(async () => {
    if (!roomCode || !isComponentMounted.current) return;

    try {
      setLoading(true);
      const data = await gameApi.getGameState(roomCode);
      
      // Проверяем, что компонент всё ещё смонтирован
      if (!isComponentMounted.current) return;

      const playersWithRoles = data.players.map((player: any) => {
        if (!player.role && player.id === data.currentPlayer) {
          return {
            ...player,
            role: 'EXPLAINING'
          };
        }
        
        return {
          ...player,
          role: player.role || 'GUESSING'
        };
      });

      setGameState({
        ...data,
        players: playersWithRoles
      });

      if (data.timeLeft !== undefined && data.timeLeft !== null) {
        setTimeLeft(data.timeLeft);
        const roundTime = data.time_per_round || timePerRound;
        setTimePerRound(roundTime);
        const startTime = Date.now() / 1000 - (roundTime - data.timeLeft);
        setTimerStartTime(startTime);
        console.log(`Timer initialized: timeLeft=${data.timeLeft}, roundTime=${roundTime}, startTime=${startTime}`);
      }

      setError(null);
      setInitialLoadComplete(true);
    } catch (error) {
      console.error("Error fetching game state:", error);
      if (isComponentMounted.current) {
        setError("Не удалось загрузить состояние игры");
      }
    } finally {
      if (isComponentMounted.current) {
        setLoading(false);
      }
    }
  }, [roomCode, timePerRound]);

  // Мемоизированная функция для создания WebSocket соединения
  const connectWebSocket = useCallback(() => {
    // Проверяем что компонент все еще смонтирован
    if (!isComponentMounted.current) {
      console.log('Компонент размонтирован, WebSocket соединение не создается');
      return;
    }
    
    // Проверяем, что еще не создаем соединение и предыдущее не активно
    if (isConnecting.current) {
      console.log('Соединение уже в процессе создания, пропускаем');
      return;
    }
    
    if (wsRef.current && 
        (wsRef.current.readyState === WebSocket.CONNECTING || 
         wsRef.current.readyState === WebSocket.OPEN)) {
      console.log('Уже есть активное подключение WebSocket');
      return;
    }

    console.log('Попытка подключения WebSocket с параметрами:', { 
      userExists: Boolean(user), 
      userId: user?.id, 
      roomCode,
      wsBaseUrl 
    });

    if (!user || !roomCode) return;

    isConnecting.current = true;

    // Закрываем предыдущее соединение, если оно существует
    if (wsRef.current) {
      console.log('Закрытие предыдущего WebSocket соединения');
      try {
        wsRef.current.close(1000, 'Новое соединение создается');
      } catch (e) {
        console.warn('Ошибка при закрытии предыдущего соединения:', e);
      }
      wsRef.current = null;
    }

    try {
      const wsUrl = `${wsBaseUrl}/api/ws/${roomCode}/${user.id}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log(`WebSocket connection opened to game ${roomCode}`);
        isConnecting.current = false;
        fetchGameState();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Проверяем, смонтирован ли еще компонент
          if (!isComponentMounted.current) return;

          if (data.type === 'chat_message') {
            console.log('Получено сообщение чата:', data);
            setChatMessages(prev => [...prev, data]);
          } else if (data.type === 'game_state_update') {
            console.log('Получено обновление состояния игры:', data.game_state);
            setGameState(prevState => {
              if (!prevState) return data.game_state;

              if (data.game_state.currentWord) {
                return data.game_state;
              }
              
              return {
                ...data.game_state,
                currentWord: data.game_state.currentWord || prevState.currentWord
              };
            });
            
            // Обновляем таймер если получен новый
            if (data.game_state.timeLeft !== undefined && data.game_state.time_per_round) {
              setTimeLeft(data.game_state.timeLeft);
              setTimePerRound(data.game_state.time_per_round);
              
              // Рассчитываем время начала раунда
              const startTime = Date.now() / 1000 - (data.game_state.time_per_round - data.game_state.timeLeft);
              setTimerStartTime(startTime);
            }
          } else if (data.type === 'turn_changed') {
            fetchGameState();

            // Обновляем таймер если получен новый
            if (data.new_timer) {
              setTimerStartTime(data.timer_start);
              setTimePerRound(data.time_per_round || timePerRound);
              setTimeLeft(data.time_per_round || timePerRound);
            }
          } else if (data.type === 'game_finished') {
            toast({
              title: "Игра завершена!",
              status: "info",
              duration: 4000,
              isClosable: true,
              position: 'top',
            });
            navigate(`/room/${roomCode}`);
          } else if (data.type === 'game_started') {
            console.log('Получено сообщение о начале игры в игровом режиме');
            fetchGameState();
            if (data.timer_start && data.time_per_round) {
              setTimerStartTime(data.timer_start);
              setTimePerRound(data.time_per_round);
              setTimeLeft(data.time_per_round);
            }
          } else if (data.type === 'correct_guess') {
            toast({
              title: "Правильно!",
              description: data.message,
              status: "success",
              duration: 4000,
              isClosable: true,
              position: 'top',
            });
            fetchGameState();

            // Обновляем таймер если получен новый
            if (data.new_timer) {
              setTimerStartTime(data.timer_start);
              setTimePerRound(data.time_per_round);
              setTimeLeft(data.time_per_round);
            }
          } else if (data.type === 'wrong_guess') {
            console.log(`Игрок ${data.player_id} неправильно угадал: ${data.guess}`);
          } else if (data.type === 'game_finished') {
            toast({
              title: "Игра завершена!",
              status: "info",
              duration: 4000,
              isClosable: true,
              position: 'top',
            });
            navigate(`/room/${roomCode}`);
          } else if (data.type === 'player_left') {
            console.log('Игрок вышел из игры:', data);
            
            const playerId = data.player_id || (data.player && data.player.id);
            console.log('Удаляем игрока с ID:', playerId);
            
            if (playerId) {
              setGameState(prevState => {
                if (!prevState) return prevState;
                
                const updatedPlayers = prevState.players.filter(p => p.id !== playerId.toString());
                console.log('Обновленный список игроков:', updatedPlayers);
                
                return {
                  ...prevState,
                  players: updatedPlayers
                };
              });
            }
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        isConnecting.current = false;
      };

      ws.onclose = (event) => {
        console.log(`WebSocket closed with code ${event.code}`);
        isConnecting.current = false;

        if (event.code !== 1000 && event.code !== 1001 && isComponentMounted.current && user && roomCode) {
          console.log('Планируем восстановление WebSocket соединения...');
          
          // Очищаем предыдущий таймаут, если он был
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }
          
          // Устанавливаем новый таймаут
          reconnectTimeoutRef.current = setTimeout(() => {
            // Проверяем, что компонент всё еще смонтирован
            if (isComponentMounted.current) {
              console.log('Восстановление WebSocket соединения...');
              connectWebSocket();
            }
          }, 3000);
        }
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('Error creating WebSocket:', e);
      isConnecting.current = false;
    }
  }, [fetchGameState, roomCode, user, wsBaseUrl]);

  // Загрузка состояния игры и установка WebSocket соединения
  useEffect(() => {
    if (user && roomCode && isComponentMounted.current) {
      // Очищаем предыдущий таймаут, если он был
      if (connectionTimeoutRef.current) {
        clearTimeout(connectionTimeoutRef.current);
      }
      
      // Устанавливаем новый таймаут с небольшой задержкой
      connectionTimeoutRef.current = setTimeout(() => {
        if (isComponentMounted.current) {
          connectWebSocket();
        }
      }, 200);
    }

    return () => {
      if (wsRef.current) {
        console.log('Закрытие WebSocket соединения при размонтировании компонента');
        
        try {
          wsRef.current.close(1000, 'Компонент размонтирован');
        } catch (e) {
          console.warn('Ошибка при закрытии WebSocket соединения:', e);
        }
        
        wsRef.current = null;
      }
      
      // Очищаем таймер при размонтировании компонента
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
    };
  }, [roomCode, user, connectWebSocket]);

  // Запускаем таймер обратного отсчета
  useEffect(() => {
    // Не запускаем таймер, пока не получили начальные данные или в неактивной игре
    if (timerStartTime === null || !initialLoadComplete || gameState?.status !== 'PLAYING') return;

    // Очищаем предыдущий интервал, если он существует
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
    }

    // Функция для обновления таймера
    const updateTimer = () => {
      const now = Date.now() / 1000;
      const elapsed = now - timerStartTime;
      const remaining = Math.max(0, Math.floor(timePerRound - elapsed));

      setTimeLeft(remaining);

      // Если таймер дошел до нуля, останавливаем его
      if (remaining <= 0) {
        if (timerIntervalRef.current) {
          clearInterval(timerIntervalRef.current);
          timerIntervalRef.current = null;
        }
      }
    };

    updateTimer();

    // Создаем новый интервал для обновления таймера
    const intervalId = window.setInterval(updateTimer, 1000);
    timerIntervalRef.current = intervalId;

    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    };
  }, [timerStartTime, timePerRound, gameState?.status, initialLoadComplete]);

  const handleSendChatMessage = async (message: string) => {
    try {
      await axios.post(`${apiBaseUrl}/api/game/${roomCode}/chat`, { message });
    } catch (error) {
      console.error('Ошибка при отправке сообщения в чат:', error);
    }
  };

  const isExplainingPlayer = () => {
    if (!gameState || !user) return false;
    
    const currentPlayer = gameState.players.find((player: Player) => player.username === user.name);

    if (!currentPlayer) {
      return false;
    }

    return (currentPlayer.role?.toUpperCase() === 'EXPLAINING' || 
          currentPlayer.role === 'EXPLAINING');
  };

  // Обработчик отправки догадки
  const handleSubmitGuess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!roomCode || !guess.trim()) return;

    try {
      setLoading(true);
      const result = await gameApi.submitGuess(roomCode, guess);

      setGuess("");

      if (result.correct) {
        toast({
          title: "Правильно!",
          description: "Вы угадали слово.",
          status: "success",
          duration: 4000,
          isClosable: true,
          position: 'top',
        });
      }
    } catch (error) {
      console.error("Error submitting guess:", error);
      setError("Не удалось отправить догадку");
    } finally {
      setLoading(false);
    }
  };

  // Обработчик выхода из игры
  const handleLeaveGame = async () => {
    if (!roomCode) return;

    // Сначала закрываем WebSocket-соединение и очищаем все таймауты
    if (wsRef.current) {
      console.log('Закрытие WebSocket-соединения перед выходом из игры');
      try {
        wsRef.current.close(1000, 'Игрок вышел из игры');
      } catch (e) {
        console.warn('Ошибка при закрытии WebSocket:', e);
      }
      wsRef.current = null;
    }
    
    // Очищаем таймеры перед выходом
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    
    // Очищаем таймауты для переподключения и создания соединений
    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
      connectionTimeoutRef.current = null;
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Используем таймаут для гарантированного перенаправления
    const redirectTimeout = setTimeout(() => {
      console.log('Выполняется запасной перенаправление после таймаута');
      navigate('/', { replace: true });
    }, 1500);

    try {
      console.log('Отправка запроса на выход из игры...');
      await gameApi.leaveGame(roomCode);
      console.log('Успешный выход из игры');
    } catch (apiError: any) {
      console.error("Ошибка при выходе из игры:", apiError);
    } finally {
      clearTimeout(redirectTimeout);
      
      console.log('Перенаправление на главную страницу после выхода');
      navigate('/', { replace: true });
    }
  };

  // Форматирование времени
  const formatTime = (seconds: number | null) => {
    if (seconds === null) return "--:--";
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const getTimerClass = () => {
    if (!timeLeft) return '';
    if (timeLeft <= 10) return 'danger';
    if (timeLeft <= 20) return 'warning';
    return '';
  };

  if (error) {
    return (
      <div className="error-container">
        <h2>Ошибка</h2>
        <p>{error}</p>
        <button onClick={() => navigate('/')}>Вернуться на главную</button>
      </div>
    );
  }

  return (
    <div className="game-container">
      <h1>Игра в комнате: {roomCode}</h1>

      {gameState ? (
        <div className="game-content">
          <div className="game-info">
            <p><strong>Раунд:</strong> {gameState.round} из {gameState.rounds_total}</p>
            {isExplainingPlayer() && gameState.currentWord && (
              <div className="current-word">
                <p><strong>Ваше слово:</strong> {gameState.currentWord}</p>
                
                {gameState.associations && gameState.associations.length > 0 && (
                  <div className="forbidden-words">
                    <p><strong>Запрещено использовать:</strong></p>
                    <ul className="associations-list">
                      {gameState.associations.map((association, index) => (
                        <li key={index} className="forbidden-word">{association}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                <p className="word-instruction">Объясните это слово другим игрокам, не используя его и однокоренные слова</p>
             </div>
            )}

            <div className={`timer-display ${getTimerClass()}`}>
              <p><strong>Оставшееся время:</strong> {formatTime(timeLeft)}</p>
              <div className="progress-bar">
                <div
                  className="progress"
                  style={{
                    width: `${timeLeft !== null ? (timeLeft / timePerRound) * 100 : 0}%`,
                    backgroundColor: timeLeft !== null && timeLeft < 10 ? '#ff0000' :
                      timeLeft !== null && timeLeft < 20 ? '#ffc107' : '#4caf50'
                  }}
                ></div>
              </div>
            </div>
          </div>

          {gameState.status === 'PLAYING' && (
            <div className="game-actions">
              {isExplainingPlayer() ? (
                <div className="player-controls">
                  <p>Ваш ход! Объясните слово другим игрокам.</p>
                </div>
              ) : (
                <div className="guess-form">
                  <form onSubmit={handleSubmitGuess}>
                    <input
                      type="text"
                      value={guess}
                      onChange={(e) => setGuess(e.target.value)}
                      placeholder="Введите вашу догадку..."
                      disabled={loading}
                    />
                    <button
                      type="submit"
                      disabled={loading || !guess.trim()}
                    >
                      Отправить
                    </button>
                  </form>
                </div>
              )}
            </div>
          )}

          <div className="players-section">
            <h3>Игроки</h3>
            <ul className="players-list">
              {gameState.players.map((player) => (
                <li
                  key={player.id}
                  className={`player-item ${player.id === gameState.currentPlayer ? 'current-player' : ''}`}
                >
                  {player.username}: {player.score} очков
                  {player.id === user?.id && " (Вы)"}
                  {player.id === gameState.currentPlayer && " (Ходит)"}
                </li>
              ))}
            </ul>
          </div>

          <button
            className="leave-game-btn"
            onClick={handleLeaveGame}
          >
            Покинуть игру
          </button>
        </div>
      ) : (
        <div className="loading-container">
          <p>Загрузка состояния игры...</p>
          <div className="spinner"></div>
        </div>
      )}
      <ChatBox 
        roomCode={roomCode || ''}
        isExplaining={isExplainingPlayer()}
        messages={chatMessages}
        onSendMessage={handleSendChatMessage}
      />
    </div>
  );
};

export default GameBoard;