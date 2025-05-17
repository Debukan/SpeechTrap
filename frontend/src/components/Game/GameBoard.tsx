import React, { useState, useEffect, useContext, useRef, useCallback } from 'react';
import { isDev } from '../../utils/config';
import apiClient, { gameApi } from '../../api/apiClient';
import { useParams, useNavigate } from 'react-router-dom';
import { UserContext } from '../../context/UserContext';
import { getApiBaseUrl } from '../../utils/config';
import axios from '../../utils/axios-config';
import ChatBox from '../Chat/ChatBox';
import { ChatMessage } from '../../types/chat';
import { toast } from 'sonner';
import './GameBoard.css';

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
  const [guess, setGuess] = useState<string>('');
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

  const gameWords = [
    'Табу', 'Слово', 'Ассоциация', 'Описание', 'Загадка', 
    'Угадай', 'Синоним', 'Команда', 'Фраза', 'Общение',
    'Игра', 'Объяснение', 'Секрет', 'Запрет', 'Подсказка',
  ];

  const renderForbiddenWords = React.useMemo(() => {
    if (!gameState?.associations || !gameState.associations.length) return null;
    
    return gameState.associations.map((word, index) => (
      <div key={index} className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-medium">
        {word}
      </div>
    ));
  }, [gameState?.associations]);

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
    if (isDev()) {
      console.log('User context in GameBoard:', user);
    }
  }, [user]);

  useEffect(() => {
    // Проверяем наличие пользователя в контексте
    if (!user) {
      if (isDev()) {
        console.log('Пользователь не найден в контексте, пытаемся восстановить из localStorage');
      }
      try {
        const savedUser = localStorage.getItem('user');
        if (savedUser) {
          const parsedUser = JSON.parse(savedUser);
          if (isDev()) {
            console.log('Восстановлен пользователь из localStorage:', parsedUser);
          }
          setUser(parsedUser);
        } else {
          if (isDev()) {
            console.log('Пользователь не найден в localStorage');
          }
        }
      } catch (error) {
        if (isDev()) {
          console.error('Ошибка при восстановлении пользователя:', error);
        }
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
            role: 'EXPLAINING',
          };
        }
        
        return {
          ...player,
          role: player.role || 'GUESSING',
        };
      });

      setGameState({
        ...data,
        players: playersWithRoles,
      });

      if (data.timeLeft !== undefined && data.timeLeft !== null) {
        setTimeLeft(data.timeLeft);
        const roundTime = data.time_per_round || timePerRound;
        setTimePerRound(roundTime);
        const startTime = Date.now() / 1000 - (roundTime - data.timeLeft);
        setTimerStartTime(startTime);
        if (isDev()) {
          console.log(`Timer initialized: timeLeft=${data.timeLeft}, roundTime=${roundTime}, startTime=${startTime}`);
        }
      }

      setError(null);
      setInitialLoadComplete(true);
    } catch (error) {
      if (isDev()) {
        console.error('Error fetching game state:', error);
      }
      if (isComponentMounted.current) {
        setError('Не удалось загрузить состояние игры');
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
      if (isDev()) {
        console.log('Компонент размонтирован, WebSocket соединение не создается');
      }
      return;
    }
    
    // Проверяем, что еще не создаем соединение и предыдущее не активно
    if (isConnecting.current) {
      if (isDev()) {
        console.log('Соединение уже в процессе создания, пропускаем');
      }
      return;
    }
    
    if (wsRef.current && 
        (wsRef.current.readyState === WebSocket.CONNECTING || 
         wsRef.current.readyState === WebSocket.OPEN)) {
      if (isDev()) {
        console.log('Уже есть активное подключение WebSocket');
      }
      return;
    }

    if (isDev()) {
      console.log('Попытка подключения WebSocket с параметрами:', { 
        userExists: Boolean(user), 
        userId: user?.id, 
        roomCode,
        wsBaseUrl, 
      });
    }

    if (!user || !roomCode) return;

    isConnecting.current = true;

    // Закрываем предыдущее соединение, если оно существует
    if (wsRef.current) {
      if (isDev()) {
        console.log('Закрытие предыдущего WebSocket соединения');
      }
      try {
        wsRef.current.close(1000, 'Новое соединение создается');
      } catch (e) {
        if (isDev()) {
          console.warn('Ошибка при закрытии предыдущего соединения:', e);
        }
      }
      wsRef.current = null;
    }

    try {
      const wsUrl = `${wsBaseUrl}/api/ws/${roomCode}/${user.id}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (isDev()) {
          console.log(`WebSocket connection opened to game ${roomCode}`);
        }
        isConnecting.current = false;
        fetchGameState();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Проверяем, смонтирован ли еще компонент
          if (!isComponentMounted.current) return;

          if (data.type === 'chat_message') {
            if (isDev()) {
              console.log('Получено сообщение чата:', data);
            }
            setChatMessages(prev => [...prev, data]);
          } else if (data.type === 'game_state_update') {
            if (isDev()) {
              console.log('Получено обновление состояния игры:', data.game_state);
            }
            setGameState(prevState => {
              if (!prevState) return data.game_state;

              const playersWithRoles = data.game_state.players.map((player: any) => {
                if (player.id === data.game_state.currentPlayer) {
                  return {
                    ...player,
                    role: 'EXPLAINING',
                  };
                }
                return {
                  ...player,
                  role: player.role || 'GUESSING',
                };
              });

              const preservedAssociations = data.game_state.associations || prevState.associations;

              if (data.game_state.currentWord) {
                return {
                  ...data.game_state,
                  players: playersWithRoles,
                  associations: preservedAssociations,
                };
              }
              
              return {
                ...data.game_state,
                players: playersWithRoles,
                currentWord: data.game_state.currentWord || prevState.currentWord,
                associations: preservedAssociations,
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
            if (isDev()) {
              console.log(data);
            }

            // Обновляем таймер если получен новый
            if (data.new_timer) {
              setTimerStartTime(data.timer_start);
              setTimePerRound(data.time_per_round || timePerRound);
              setTimeLeft(data.time_per_round || timePerRound);
            }
          } else if (data.type === 'game_finished') {
            toast.info('Игра завершена!');
            navigate(`/room/${roomCode}`);
          } else if (data.type === 'game_started') {
            if (isDev()) {
              console.log('Получено сообщение о начале игры в игровом режиме');
            }
            fetchGameState();
            if (data.timer_start && data.time_per_round) {
              setTimerStartTime(data.timer_start);
              setTimePerRound(data.time_per_round);
              setTimeLeft(data.time_per_round);
            }
          } else if (data.type === 'correct_guess') {
            toast.success('Правильно!', {
              description: data.message,
              duration: 4000,
            });
            fetchGameState();

            // Обновляем таймер если получен новый
            if (data.new_timer) {
              setTimerStartTime(data.timer_start);
              setTimePerRound(data.time_per_round);
              setTimeLeft(data.time_per_round);
            }
          } else if (data.type === 'wrong_guess') {
            if (isDev()) {
              console.log(`Игрок ${data.player_id} неправильно угадал: ${data.guess}`);
            }
          } else if (data.type === 'player_left') {
            if (isDev()) {
              console.log('Игрок вышел из игры:', data);
            }
            
            const playerId = data.player_id || (data.player && data.player.id);
            if (isDev()) {
              console.log('Удаляем игрока с ID:', playerId);
            }
            
            if (playerId) {
              setGameState(prevState => {
                if (!prevState) return prevState;
                
                const updatedPlayers = prevState.players.filter(p => p.id !== playerId.toString());
                if (isDev()) {
                  console.log('Обновленный список игроков:', updatedPlayers);
                }
                
                return {
                  ...prevState,
                  players: updatedPlayers,
                };
              });
            }
          }
        } catch (error) {
          if (isDev()) {
            console.error('Error parsing WebSocket message:', error);
          }
        }
      };

      ws.onerror = (error) => {
        if (isDev()) {
          console.error('WebSocket error:', error);
        }
        isConnecting.current = false;
      };

      ws.onclose = (event) => {
        if (isDev()) {
          console.log(`WebSocket closed with code ${event.code}`);
        }
        isConnecting.current = false;

        if (event.code !== 1000 && event.code !== 1001 && isComponentMounted.current && user && roomCode) {
          if (isDev()) {
            console.log('Планируем восстановление WebSocket соединения...');
          }
          
          // Очищаем предыдущий таймаут, если он был
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }
          
          // Устанавливаем новый таймаут
          reconnectTimeoutRef.current = setTimeout(() => {
            // Проверяем, что компонент всё еще смонтирован
            if (isComponentMounted.current) {
              if (isDev()) {
                console.log('Восстановление WebSocket соединения...');
              }
              connectWebSocket();
            }
          }, 3000);
        }
      };

      wsRef.current = ws;
    } catch (e) {
      if (isDev()) {
        console.error('Error creating WebSocket:', e);
      }
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
        if (isDev()) {
          console.log('Закрытие WebSocket соединения при размонтировании компонента');
        }
        
        try {
          wsRef.current.close(1000, 'Компонент размонтирован');
        } catch (e) {
          if (isDev()) {
            console.warn('Ошибка при закрытии WebSocket соединения:', e);
          }
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
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.status === 400) {
          toast.error('Сообщение не отправлено', {
            description: error.response.data.detail || 'Вы использовали запрещенные слова в сообщении',
            duration: 4000,
          });
        } else {
          toast.error('Ошибка при отправке сообщения', {
            description: error.response.data.detail || 'Попробуйте еще раз',
            duration: 4000,
          });
        }
      } else {
        toast.error('Ошибка соединения', {
          description: 'Не удалось отправить сообщение',
          duration: 4000,
        });
      }
      
      if (isDev()) {
        console.error('Ошибка при отправке сообщения в чат:', error);
      }
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

      setGuess('');

      if (result.correct) {
        toast.success('Правильно!', {
          description: 'Вы угадали слово.',
          duration: 4000,
        });
      }
    } catch (error) {
      if (isDev()) {
        console.error('Error submitting guess:', error);
      }
      setError('Не удалось отправить догадку');
    } finally {
      setLoading(false);
    }
  };

  // Обработчик выхода из игры
  const handleLeaveGame = async () => {
    if (!roomCode) return;

    // Сначала закрываем WebSocket-соединение и очищаем все таймауты
    if (wsRef.current) {
      if (isDev()) {
        console.log('Закрытие WebSocket-соединения перед выходом из игры');
      }
      try {
        wsRef.current.close(1000, 'Игрок вышел из игры');
      } catch (e) {
        if (isDev()) {
          console.warn('Ошибка при закрытии WebSocket:', e);
        }
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
      if (isDev()) {
        console.log('Выполняется запасной перенаправление после таймаута');
      }
      navigate('/', { replace: true });
    }, 1500);

    try {
      if (isDev()) {
        console.log('Отправка запроса на выход из игры...');
      }
      await gameApi.leaveGame(roomCode);
      if (isDev()) {
        console.log('Успешный выход из игры');
      }
    } catch (apiError: any) {
      if (isDev()) {
        console.error('Ошибка при выходе из игры:', apiError);
      }
    } finally {
      clearTimeout(redirectTimeout);
      
      if (isDev()) {
        console.log('Перенаправление на главную страницу после выхода');
      }
      navigate('/', { replace: true });
    }
  };

  // Форматирование времени
  const formatTime = (seconds: number | null) => {
    if (seconds === null) return '--:--';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const formatTimeWithAnimation = (seconds: number | null) => {
    if (seconds === null) return <>--<span className="px-1">:</span>--</>;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    const isDanger = seconds <= 10;
    const isWarning = seconds <= 20 && seconds > 10;
    
    const digitClass = isDanger 
      ? 'bg-red-100 px-2 py-1 rounded-md border border-red-300' 
      : isWarning 
        ? 'bg-orange-50 px-2 py-1 rounded-md border border-orange-200' 
        : 'bg-blue-50 px-2 py-1 rounded-md';
    
    return (
      <>
        <span className={digitClass}>{minutes.toString().padStart(2, '0')}</span>
        <span className={`time-separator px-1 font-bold ${isDanger ? 'text-red-600' : isWarning ? 'text-orange-500' : ''}`}>:</span>
        <span className={digitClass}>{remainingSeconds.toString().padStart(2, '0')}</span>
      </>
    );
  };

  const getTimerClass = () => {
    if (!timeLeft) return '';
    if (timeLeft <= 10) return 'danger';
    if (timeLeft <= 20) return 'warning';
    return '';
  };

  if (error) {
    return (
      <div className="game-board-container min-h-screen relative">
        <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
          <div className="absolute -top-20 -right-20 w-64 h-64 bg-blue-200 rounded-full opacity-20 blur-3xl"></div>
          <div className="absolute top-1/3 -left-20 w-80 h-80 bg-purple-200 rounded-full opacity-20 blur-3xl"></div>
          <div className="absolute -bottom-20 right-1/3 w-72 h-72 bg-blue-200 rounded-full opacity-20 blur-3xl"></div>
          
          {gameWords.map((word, index) => (
            <div 
              key={index}
              className="floating-word absolute"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                animationDelay: `${Math.random() * 20}s`,
                animationDuration: `${25 + Math.random() * 15}s`,
                transform: `rotate(${Math.random() * 30 - 15}deg)`,
                fontSize: `${1 + Math.random() * 0.8}rem`,
                opacity: 0.15,
              }}
            >
              {word}
            </div>
          ))}
        </div>

        <div className="container mx-auto p-4 relative z-10">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-[80vh]">
              <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
              <p className="text-xl font-semibold text-blue-800">Загрузка игры...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-[80vh]">
              <div className="bg-white p-8 rounded-xl shadow-lg max-w-lg w-full">
                <div className="text-red-500 mb-4 text-3xl text-center">⚠️</div>
                <h2 className="text-2xl font-bold text-center text-red-600 mb-4">Ошибка</h2>
                <p className="text-center text-gray-700 mb-6">{error}</p>
                <button 
                  onClick={() => navigate('/')}
                  className="w-full h-12 bg-gradient-to-r from-blue-600 to-blue-800 hover:from-blue-700 hover:to-blue-900 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
                >
                  <span className="mr-2">↩️</span>
                  <span>Вернуться в главное меню</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white/90 backdrop-blur-sm rounded-xl shadow-xl border border-blue-100 overflow-hidden">
              <div className="p-4 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white relative">
                <div className="absolute inset-0 opacity-10">
                  <div className="absolute inset-0 bg-repeat" style={{ 
                    backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'20\' height=\'20\' viewBox=\'0 0 20 20\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'0.2\' fill-rule=\'evenodd\'%3E%3Ccircle cx=\'3\' cy=\'3\' r=\'3\'/%3E%3Ccircle cx=\'13\' cy=\'13\' r=\'3\'/%3E%3C/g%3E%3C/svg%3E")', 
                  }}></div>
                </div>
                
                <div className="flex justify-between items-center relative z-10">
                  <div>
                    <h1 className="text-xl font-bold">Комната: {roomCode}</h1>
                  </div>
                  
                  <button 
                    className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors shadow-md hover:shadow-lg flex items-center"
                    onClick={handleLeaveGame}
                  >
                    <span className="mr-2">🚪</span>
                    Покинуть игру
                  </button>
                </div>
              </div>
              
              <div className="p-6">
                <div className="grid md:grid-cols-3 gap-6">
                  <div className="md:col-span-1 space-y-6">
                    <div className="bg-blue-50 rounded-xl p-4 shadow-md border border-blue-100">
                      <h2 className="text-lg font-bold text-blue-800 mb-3 border-b border-blue-200 pb-2">Игроки</h2>
                      <div className="space-y-2">
                        {gameState?.players.map((player) => (
                          <div key={player.id} className="flex justify-between items-center p-2 rounded-lg bg-white shadow-sm border border-blue-50">
                            <div className="flex items-center">
                              <div className={`w-3 h-3 rounded-full mr-2 ${player.role === 'EXPLAINING' ? 'bg-yellow-500' : 'bg-green-500'}`}></div>
                              <span className="font-medium">{player.username}</span>
                              {player.role === 'EXPLAINING' && <span className="ml-2 text-xs bg-yellow-100 text-yellow-800 py-1 px-2 rounded-full">Объясняет</span>}
                            </div>
                            <div className="bg-blue-100 px-3 py-1 rounded-full text-blue-800 font-bold">{player.score}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="md:col-span-2 space-y-4">
                    {gameState?.status === 'PLAYING' && (
                      <div>
                        {isExplainingPlayer() ? (
                          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 shadow-lg relative overflow-hidden">
                            <div className="absolute -top-6 -right-6 w-16 h-16 bg-yellow-300 rounded-full opacity-30"></div>
                            <div className="absolute bottom-1/3 -left-6 w-20 h-20 bg-yellow-200 rounded-full opacity-20"></div>
                            <h3 className="text-center text-xl font-bold text-yellow-800 mb-4 relative z-10">Объясните это слово</h3>
                            <div className="word-card text-center p-4 bg-white rounded-lg border-2 border-yellow-300 shadow-md relative z-10">
                              <p className="text-3xl font-bold text-yellow-800">{gameState.currentWord}</p>
                            </div>
                            {gameState.associations && gameState.associations.length > 0 && (
                              <div className="mt-4 relative z-10">
                                <h4 className="text-center font-semibold text-yellow-700 mb-2">Запрещённые слова:</h4>
                                <div className="flex flex-wrap justify-center gap-2">
                                  {renderForbiddenWords}
                                </div>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 shadow-lg relative overflow-hidden">
                            <div className="absolute -top-6 -right-6 w-16 h-16 bg-yellow-300 rounded-full opacity-30"></div>
                            <div className="absolute bottom-1/3 -left-6 w-20 h-20 bg-yellow-200 rounded-full opacity-20"></div>
                            <h3 className="text-center text-xl font-bold text-yellow-800 mb-4 relative z-10">Угадайте слово</h3>
                            <div className="word-card text-center p-4 bg-white rounded-lg border-2 border-yellow-300 shadow-md relative z-10">
                              <p className="text-3xl font-bold text-yellow-800">{gameState.currentWord}</p>
                            </div>
                            {gameState.associations && gameState.associations.length > 0 && (
                              <div className="mt-4 relative z-10">
                                <h4 className="text-center font-semibold text-yellow-700 mb-2">Запрещённые слова:</h4>
                                <div className="flex flex-wrap justify-center gap-2">
                                  {renderForbiddenWords}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    <div className="bg-white rounded-xl shadow-lg border border-blue-100 overflow-hidden mt-0">
                      <ChatBox
                        roomCode={roomCode || ''}
                        isExplaining={isExplainingPlayer()}
                        messages={chatMessages}
                        onSendMessage={handleSendChatMessage}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-blue-50 to-white relative overflow-hidden">
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-20 -right-20 w-64 h-64 bg-blue-200 rounded-full opacity-20 blur-3xl"></div>
        <div className="absolute top-1/3 -left-20 w-80 h-80 bg-purple-200 rounded-full opacity-20 blur-3xl"></div>
        <div className="absolute -bottom-20 right-1/3 w-72 h-72 bg-blue-200 rounded-full opacity-20 blur-3xl"></div>
        
        {gameWords.map((word, index) => (
          <div 
            key={index}
            className="floating-word absolute"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 20}s`,
              animationDuration: `${25 + Math.random() * 15}s`,
              transform: `rotate(${Math.random() * 30 - 15}deg)`,
              fontSize: `${1 + Math.random() * 0.8}rem`,
              opacity: 0.15,
            }}
          >
            {word}
          </div>
        ))}
      </div>

      <div className="absolute -top-10 left-1/4 w-20 h-20 bg-purple-200 rounded-full opacity-30 speech-bubble-decoration"></div>
      <div className="absolute -bottom-10 right-1/4 w-24 h-24 bg-blue-200 rounded-full opacity-30 speech-bubble-decoration"></div>
      
      <div className="container mx-auto px-4 pt-14 pb-4 relative z-10">
        {gameState && !loading && !error && (
          <div className="flex justify-center items-center mb-6 game-info-container">
            <div className="flex gap-10 px-8 py-5 bg-white/95 backdrop-blur-sm rounded-2xl shadow-xl border border-blue-100 items-center game-info-bar" 
              style={{
                boxShadow: '0 10px 25px -5px rgba(59, 130, 246, 0.1), 0 8px 10px -6px rgba(59, 130, 246, 0.1), 0 0 5px rgba(99, 102, 241, 0.2)',
              }}>
              <div className="flex flex-col items-center">
                <span className="text-blue-800 font-medium text-sm mb-2">
                  <span className="info-icon">🎮</span>
                  Раунд
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-3xl font-bold text-blue-700 round-number" style={{ textShadow: '0 0 1px rgba(0,0,0,0.1)' }}>
                    {gameState.round}/{gameState.rounds_total}
                  </span>
                </div>
              </div>
              
              <div className="h-14 w-px bg-gray-200"></div>
              
              <div className="flex flex-col items-center">
                <span className="text-blue-800 font-medium text-sm mb-2">
                  <span className="info-icon">⏱️</span>
                  Осталось времени
                </span>
                <div 
                  className={`text-3xl font-bold font-mono timer-wrap time-digits ${
                    timeLeft && timeLeft <= 10 ? 'danger-parent' : ''
                  }`} 
                  style={{ letterSpacing: '0.05em' }}
                >
                  <div className={
                    timeLeft && timeLeft <= 10 
                      ? 'text-red-600 time-danger danger-flash' 
                      : timeLeft && timeLeft <= 20 
                        ? 'text-orange-500 time-warning' 
                        : 'text-blue-700'
                  }>
                    {formatTimeWithAnimation(timeLeft)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {loading ? (
          <div className="flex flex-col items-center justify-center h-[80vh]">
            <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
            <p className="text-xl font-semibold text-blue-800">Загрузка игры...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-[80vh]">
            <div className="bg-white p-8 rounded-xl shadow-lg max-w-lg w-full">
              <div className="text-red-500 mb-4 text-3xl text-center">⚠️</div>
              <h2 className="text-2xl font-bold text-center text-red-600 mb-4">Ошибка</h2>
              <p className="text-center text-gray-700 mb-6">{error}</p>
              <button 
                onClick={() => navigate('/')}
                className="w-full h-12 bg-gradient-to-r from-blue-600 to-blue-800 hover:from-blue-700 hover:to-blue-900 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
              >
                <span className="mr-2">↩️</span>
                <span>Вернуться в главное меню</span>
              </button>
            </div>
          </div>
        ) : gameState ? (
          <div className="bg-white/90 backdrop-blur-sm rounded-xl shadow-xl border border-blue-100 overflow-hidden">
            <div className="p-4 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white relative">
              <div className="absolute inset-0 opacity-10">
                <div className="absolute inset-0 bg-repeat" style={{ 
                  backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'20\' height=\'20\' viewBox=\'0 0 20 20\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'0.2\' fill-rule=\'evenodd\'%3E%3Ccircle cx=\'3\' cy=\'3\' r=\'3\'/%3E%3Ccircle cx=\'13\' cy=\'13\' r=\'3\'/%3E%3C/g%3E%3C/svg%3E")', 
                }}></div>
              </div>
              
              <div className="flex justify-between items-center relative z-10">
                <div>
                  <h1 className="text-xl font-bold">Комната: {roomCode}</h1>
                </div>
                
                <button 
                  className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors shadow-md hover:shadow-lg flex items-center"
                  onClick={handleLeaveGame}
                >
                  <span className="mr-2">🚪</span>
                  Покинуть игру
                </button>
              </div>
            </div>
            
            <div className="p-6">
              <div className="grid md:grid-cols-3 gap-6">
                <div className="md:col-span-1 space-y-6">
                  <div className="bg-blue-50 rounded-xl p-4 shadow-md border border-blue-100">
                    <h2 className="text-lg font-bold text-blue-800 mb-3 border-b border-blue-200 pb-2">Игроки</h2>
                    <div className="space-y-2">
                      {gameState.players.map((player) => (
                        <div key={player.id} className="flex justify-between items-center p-2 rounded-lg bg-white shadow-sm border border-blue-50">
                          <div className="flex items-center">
                            <div className={`w-3 h-3 rounded-full mr-2 ${player.role === 'EXPLAINING' ? 'bg-yellow-500' : 'bg-green-500'}`}></div>
                            <span className="font-medium">{player.username}</span>
                            {player.role === 'EXPLAINING' && <span className="ml-2 text-xs bg-yellow-100 text-yellow-800 py-1 px-2 rounded-full">Объясняет</span>}
                          </div>
                          <div className="bg-blue-100 px-3 py-1 rounded-full text-blue-800 font-bold">{player.score}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="md:col-span-2 space-y-4">
                  {gameState.status === 'PLAYING' && (
                    <div>
                      {isExplainingPlayer() ? (
                        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 shadow-lg relative overflow-hidden">
                          <div className="absolute -top-6 -right-6 w-16 h-16 bg-yellow-300 rounded-full opacity-30"></div>
                          <div className="absolute bottom-1/3 -left-6 w-20 h-20 bg-yellow-200 rounded-full opacity-20"></div>
                          <h3 className="text-center text-xl font-bold text-yellow-800 mb-4 relative z-10">Объясните это слово</h3>
                          <div className="word-card text-center p-4 bg-white rounded-lg border-2 border-yellow-300 shadow-md relative z-10">
                            <p className="text-3xl font-bold text-yellow-800">{gameState.currentWord}</p>
                          </div>
                          {gameState.associations && gameState.associations.length > 0 && (
                            <div className="mt-4 relative z-10">
                              <h4 className="text-center font-semibold text-yellow-700 mb-2">Запрещённые слова:</h4>
                              <div className="flex flex-wrap justify-center gap-2">
                                {renderForbiddenWords}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="bg-green-50 border border-green-200 rounded-xl p-6 shadow-lg relative overflow-hidden">
                          <div className="absolute -top-6 -left-6 w-16 h-16 bg-green-300 rounded-full opacity-30"></div>
                          <div className="absolute bottom-1/3 -right-6 w-20 h-20 bg-green-200 rounded-full opacity-20"></div>
                          <h3 className="text-center text-xl font-bold text-green-800 mb-4 relative z-10">Угадайте слово</h3>
                          <form onSubmit={handleSubmitGuess} className="flex gap-2 relative z-10">
                            <input
                              type="text"
                              value={guess}
                              onChange={(e) => setGuess(e.target.value)}
                              placeholder="Введите ваш вариант..."
                              className="flex-grow p-3 rounded-lg border-2 border-green-300 focus:border-green-500 focus:ring focus:ring-green-200 focus:ring-opacity-50 transition-all"
                            />
                            <button
                              type="submit"
                              className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white font-semibold py-2 px-4 rounded-lg shadow-md hover:shadow-lg transition-all flex items-center"
                            >
                              <span className="mr-2">✅</span>
                              Ответить
                            </button>
                          </form>
                        </div>
                      )}
                    </div>
                  )}
                  
                  <div className="bg-white rounded-xl shadow-lg border border-blue-100 overflow-hidden mt-0">
                    <ChatBox
                      roomCode={roomCode || ''}
                      isExplaining={isExplainingPlayer()}
                      messages={chatMessages}
                      onSendMessage={handleSendChatMessage}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-[80vh]">
            <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
            <p className="text-xl font-semibold text-blue-800">Подготовка игры...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default GameBoard;