import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import axios from '../../utils/axios-config';
import { getApiBaseUrl, isDev } from '../../utils/config';
import { useAuth } from '../../context/AuthContext';
import ChatBox from '../Chat/ChatBox';
import { ChatMessage } from '../../types/chat';
import './Room.css';
import { toast } from 'sonner';

interface Player {
    id: number;
    name: string;
    role?: string;
    score?: number;
    score_total?: number;
}

interface RoomData {
    id: number;
    code: string;
    status: string;
    max_players: number;
    current_round: number;
    rounds_total: number;
    time_per_round: number;
    player_count: number;
    is_full: boolean;
    players: Player[];
}

const Room: React.FC = () => {
  const { roomId } = useParams<{ roomId: string }>();
  const location = useLocation();
  const justCreated = new URLSearchParams(location.search).get('justCreated') === 'true';
  const [room, setRoom] = useState<RoomData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [joining, setJoining] = useState<boolean>(false);
  const [joinError, setJoinError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<boolean>(false);
  const apiBaseUrl = getApiBaseUrl();
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const socketRef = useRef<WebSocket | null>(null);
  const wsBaseUrl = apiBaseUrl.replace('http', 'ws');
  const processedMessages = useRef<Set<string>>(new Set());
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState<boolean>(false);

  const gameWords = [
    'Табу', 'Слово', 'Ассоциация', 'Описание', 'Загадка', 
    'Угадай', 'Синоним', 'Команда', 'Фраза', 'Общение',
    'Игра', 'Объяснение', 'Секрет', 'Запрет', 'Подсказка',
  ];

  useEffect(() => {
    if (!isAuthenticated && roomId) {
      navigate('/login', { state: { from: `/room/${roomId}` } });
    }
  }, [isAuthenticated, roomId, navigate]);

  const isUserJoined = () => {
    if (justCreated && user) return true;
    if (!room || !user) return false;
    return room.players.some(player => player.name === user.name);
  };

  const fetchRoomData = async () => {
    if (!roomId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await axios.get(`${apiBaseUrl}/api/rooms/${roomId}`);
      setRoom(response.data);
            
      // Перенаправляем в игру, если она уже запущена
      if (response.data.status === 'playing') {
        if (isDev()) {
          console.log('Игра уже запущена, перенаправляем в игру');
        }
        navigate(`/game/${roomId}`);
        return;
      }
            
      if (justCreated && user && !response.data.players.some((p: Player) => p.name === user.name)) {
        const updatedRoom = { 
          ...response.data,
          players: response.data.players,
        };
        setRoom(updatedRoom);
      }
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        setError(err.response.data.detail || 'Не удалось загрузить данные комнаты');
      } else {
        setError('Произошла ошибка при соединении с сервером');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!roomId) return;

    fetchRoomData();

    const connectWebSocket = () => {
      if (!user) {
        return;
      }

      const wsUrl = `${wsBaseUrl}/api/ws/${roomId}/${user.id}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (isDev()) {
          console.log(`WebSocket connection opened to room ${roomId}`);
        }
        fetchRoomData();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.id && processedMessages.current.has(data.id)) {
            if (isDev()) {
              console.log(`Message with ID=${data.id} already processed, skipping.`);
            }
            return;
          }

          if (data.id) {
            processedMessages.current.add(data.id);
          }
                    
          if (data.type === 'chat_message') {
            if (isDev()) {
              console.log('Получено сообщение чата:', data);
            }
            setChatMessages(prev => [...prev, data]);
          } else if (data.type === 'room_update') {
            if (isDev()) {
              console.log('Room update received:', data.room);
            }
            setRoom(data.room);
          } else if (data.type === 'player_left') {
            if (isDev()) {
              console.log(`Player left: ID=${data.player_id}, Message: ${data.message}`);
            }
            setRoom((prevRoom) => {
              if (!prevRoom) return prevRoom;

              // Проверяем, существует ли игрок в списке
              const playerExists = prevRoom.players.some(player => player.id === data.player_id);
              if (!playerExists) {
                if (isDev()) {
                  console.log(`Player with ID=${data.player_id} not found, skipping update.`);
                }
                return prevRoom;
              }

              // Удаляем игрока из списка
              const updatedPlayers = prevRoom.players.filter(player => player.id !== data.player_id);
              if (isDev()) {
                console.log('Updated players list after user_left/player_left:', updatedPlayers);
              }

              return {
                ...prevRoom,
                players: updatedPlayers,
                player_count: Math.max(prevRoom.player_count - 1, 0),
              };
            });
          } else if (data.type === 'game_state_update') {
            if (isDev()) {
              console.log('Received game_state_update, checking game state');
            }
          } else if (data.type === 'player_joined') {
            if (isDev()) {
              console.log('Player joined:', data.player);
            }
            setRoom(prevRoom => {
              if (!prevRoom) return prevRoom;

              const playerExists = prevRoom.players.some(p => p.id === data.player.id);

              if (playerExists) return prevRoom;

              const playerWithDefaults = {
                ...data.player,
                score: data.player.score ?? 0,
                role: data.player.role ?? 'waiting',
              };

              return {
                ...prevRoom,
                players: [...prevRoom.players, playerWithDefaults],
                player_count: prevRoom.player_count + 1,
              };
            });
          } else if (data.type === 'game_started') {
            if (isDev()) {
              console.log('Получено сообщение о начале игры');
            }
            // Устанавливаем статус комнаты как "playing"
            if (isDev()) {
              console.log('Текущий пользователь перед переходом:', user);
            }
            if (user) {
              if (isDev()) {
                console.log('Сохраняем данные пользователя в localStorage перед переходом');
              }
              localStorage.setItem('user', JSON.stringify(user));
            }
            setRoom(prevRoom => prevRoom ? {...prevRoom, status: 'playing'} : null);
            if (socketRef.current) {
              socketRef.current.close(1000, 'Game started, leaving room');
            }                       
            // Перенаправляем пользователя в игру
            if (isDev()) {
              console.log(`Перенаправление на игру: /game/${roomId}`);
            }
            setTimeout(() => {
              if (socketRef.current) {
                socketRef.current.close(1000, 'Game started, leaving room');
              }
              if (isDev()) {
                console.log(`Перенаправление на игру: /game/${roomId}`);
              }
              navigate(`/game/${roomId}`);
            }, 100);
          } else if (data.type === 'room_closed') {
            if (socketRef.current) {
              socketRef.current.close(1000, 'Room closed by owner');
            }
            toast.info('Комната была закрыта создателем', {
              duration: 4000,
            });
            navigate('/', { replace: true });
          } else if (data.type === 'player_score_updated') {
            if (isDev()) {
              console.log('Player score updated:', data);
            }
            setRoom(prevRoom => {
              if (!prevRoom) return prevRoom;
                            
              return {
                ...prevRoom,
                players: prevRoom.players.map(player => 
                  player.id === data.player_id 
                    ? {...player, score: data.score} 
                    : player,
                ),
              };
            });
          }
        } catch (error) {
          if (isDev()) {
            console.error('Error parsing WebSocket message:', error);
          }
          fetchRoomData();
        }
      };

      ws.onerror = (error) => {
        if (isDev()) {
          console.error('WebSocket error:', error);
        }
        fetchRoomData();
      };

      ws.onclose = (event) => {
        if (isDev()) {
          console.log(`WebSocket closed with code ${event.code}, reason: ${event.reason}`);
        }
        const isPlaying = room?.status?.toLowerCase() === 'playing';
        if (isDev()) {
          console.log(`Текущий статус комнаты при закрытии соединения: ${room?.status}`);
        }
        if (event.code === 1000 || event.code === 1001) {
          if (isDev()) {
            console.log('Нормальное закрытие соединения');
          }
          if (isPlaying) {
            if (isDev()) {
              console.log('Перенаправляем на страницу игры после нормального закрытия WebSocket');
            }
            navigate(`/game/${roomId}`);
          }
        } else if (event.code === 1008 || event.code === 403) {
          if (event.reason && event.reason.includes('not found')) {
            toast.info('Комната была закрыта или не существует', {
              duration: 4000,
            });
            navigate('/');
          }
        } else if (isPlaying) {
          if (isDev()) {
            console.log('Обнаружена активная игра, перенаправляем на страницу игры');
          }
          navigate(`/game/${roomId}`);
        } else {
          if (isDev()) {
            console.log('Attempting to reconnect WebSocket...');
          }
          setTimeout(connectWebSocket, 3000);
        }
      };

      socketRef.current = ws;
    };

    connectWebSocket();

    return () => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.close();
        if (isDev()) {
          console.log('WebSocket closed on room unmount');
        }
      }
    };
  }, [roomId, user, wsBaseUrl, navigate, isAuthenticated, apiBaseUrl]);

  const handleSendChatMessage = async (message: string) => {
    if (!roomId || !user) return;
    
    try {
      await axios.post(`${apiBaseUrl}/api/rooms/${roomId}/chat`, { message });
    } catch (error) {
      if (isDev()) {
        console.error('Ошибка при отправке сообщения в чат:', error);
      }
    }
  };

  const isRoomCreator = () => {
    return !!room && room.players?.length > 0 && room.players[0].name === user?.name;
  };

  const handleJoinRoom = async () => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: `/room/${roomId}` } });
      return;
    }

    if (!roomId || !user) return;

    setJoining(true);
    setJoinError(null);

    try {
      const joinResponse = await axios.post(`${apiBaseUrl}/api/rooms/join/${roomId}/${user.id}`);
      const response = await axios.get(`${apiBaseUrl}/api/rooms/${roomId}`);
      setRoom(response.data);
            
      toast.success('Успешно!', {
        description: joinResponse.data.message || 'Вы успешно присоединились к комнате',
        duration: 4000,
      });
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        if (err.response.status === 401) {
          navigate('/login', { state: { from: `/room/${roomId}` } });
        } else {
          setJoinError(err.response.data.detail || 'Не удалось присоединиться к комнате');
        }
      } else {
        setJoinError('Произошла ошибка при соединении с сервером');
      }
    } finally {
      setJoining(false);
    }
  };

  const handleCloseRoom = async () => {
    if (!roomId || !user) return;
    setIsConfirmDialogOpen(true);
  };

  const confirmCloseRoom = async () => {
    if (!roomId || !user) return;
    setIsConfirmDialogOpen(false);
    setDeleting(true);

    try {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.close(1000, 'Room closed by owner');
      }
            
      await axios.delete(`${apiBaseUrl}/api/rooms/${roomId}`);
      navigate('/');
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        toast.error('Ошибка', {
          description: err.response.data.detail || 'Не удалось закрыть комнату',
          duration: 4000,
        });
      } else {
        toast.error('Ошибка', {
          description: 'Произошла ошибка при соединении с сервером',
          duration: 4000,
        });
      }
      setDeleting(false);
    }
  };

  const handleStartGame = async () => {
    if (!roomId || !room) {
      return;
    }
        
    if (room.player_count < 2) {
      toast.info('Недостаточно игроков', {
        description: 'Для начала игры необходимо минимум 2 игрока',
        duration: 4000,
      });
      return;
    }
        
    if (room.status !== 'waiting') {
      toast.info('Игра уже запущена', {
        duration: 4000,
      });
      return;
    }
        
    try {
      setDeleting(true);
            
      if (isDev()) {
        console.log(`Пытаемся начать игру в комнате ${roomId}`);
      }
            
      const response = await axios.post(`${apiBaseUrl}/api/game/${roomId}/start`);
      if (isDev()) {
        console.log('Ответ сервера при запуске игры:', response.data);
      }
            
      setTimeout(() => {
        navigate(`/game/${roomId}`);
      }, 500);
    } catch (err) {
      if (isDev()) {
        console.error('Ошибка при запуске игры:', err);
      }
      if (axios.isAxiosError(err) && err.response) {
        toast.error('Ошибка', {
          description: err.response.data.detail || 'Не удалось запустить игру',
          duration: 4000,
        });
      } else {
        toast.error('Ошибка', {
          description: 'Произошла ошибка при соединении с сервером',
          duration: 4000,
        });
      }
    } finally {
      setDeleting(false);
    }
  };

  const handleLeaveRoom = async () => {
    if (!roomId || !user || !isUserJoined()) return;

    try {
      // Сначала закрываем WebSocket соединение
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.close(1000, 'User left the room voluntarily');
      }
            
      await axios.post(`${apiBaseUrl}/api/rooms/${roomId}/leave`);
      if (isDev()) {
        console.log('Успешно покинул лобби:', roomId);
      }
            
      // Перенаправляем после небольшой задержки
      setTimeout(() => {
        navigate('/', { replace: true });
      }, 100);
    } catch (error) {
      if (isDev()) {
        console.error('Ошибка при выходе из лобби:', error);
      }
      navigate('/', { replace: true });
    }
  };

  useEffect(() => {
    const handleEscKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isConfirmDialogOpen) {
        setIsConfirmDialogOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscKey);
    return () => {
      document.removeEventListener('keydown', handleEscKey);
    };
  }, [isConfirmDialogOpen]);

  if (!isAuthenticated) {
    return null;
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="text-xl text-blue-600">Загрузка данных комнаты...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-xl p-8 max-w-md mx-auto">
          <h2 className="text-2xl font-bold text-red-600 mb-4">Ошибка</h2>
          <p className="text-gray-700 mb-6">{error}</p>
          <button 
            onClick={() => navigate('/')}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-lg shadow-md hover:from-blue-700 hover:to-indigo-700 transition-all"
          >
            Вернуться на главную
          </button>
        </div>
      </div>
    );
  }

  if (!room) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-xl p-8 max-w-md mx-auto">
          <h2 className="text-2xl font-bold text-blue-600 mb-4">Комната не найдена</h2>
          <button 
            onClick={() => navigate('/')}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-lg shadow-md hover:from-blue-700 hover:to-indigo-700 transition-all"
          >
            Вернуться на главную
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
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
      
      <div className="menu-container bg-white relative z-10">
        <div className="absolute -top-10 -left-10 w-24 h-24 bg-purple-200 rounded-full opacity-50 speech-bubble-decoration"></div>
        <div className="absolute -bottom-10 -right-10 w-28 h-28 bg-blue-200 rounded-full opacity-50 speech-bubble-decoration"></div>
        
        <div className="text-center mb-6 relative pt-4">
          <div className="absolute -top-2 -left-2 text-5xl opacity-20">🎮</div>
          <div className="absolute -bottom-2 -right-2 text-5xl opacity-20">💬</div>
          <h2 className="text-2xl font-bold text-blue-800 mb-3">
            <span>Комната: </span>
            <span className="bg-blue-50 px-2 py-1 rounded-md text-blue-700 font-mono">{room.code}</span>
          </h2>
          <p className="text-blue-600 opacity-75 text-base">Подготовка к игре</p>
        </div>
        
        <div className="room-info">
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center">
              <span className="text-blue-500 mr-2">🎯</span>
              <p>Всего раундов: <span className="font-semibold">{room.rounds_total}</span></p>
            </div>
            <div className="flex items-center">
              <span className="text-blue-500 mr-2">👥</span>
              <p>Игроков: <span className="font-semibold">{room.player_count} из {room.max_players}</span></p>
            </div>
            <div className="flex items-center">
              <span className="text-blue-500 mr-2">⏱️</span>
              <p>Время раунда: <span className="font-semibold">{Math.floor(room.time_per_round / 60)} мин.</span></p>
            </div>
            <div className="flex items-center">
              <span className="text-blue-500 mr-2">📊</span>
              <p>Статус: <span className="font-semibold">{room.status === 'waiting' ? 'Ожидание' : room.status}</span></p>
            </div>
          </div>
        </div>

        <div className="players-list">
          <h3 className="flex items-center text-xl mb-4 justify-center">
            <span className="mr-2">👥</span>
            Игроки в лобби:
          </h3>
          {room.players.length === 0 ? (
            <p className="text-center text-gray-500 italic py-4">Ожидание игроков...</p>
          ) : (
            <ul>
              {room.players.map((player) => (
                <li key={player.id} className={player.name === user?.name ? 'current-player' : ''}>
                  <div className="flex items-center">
                    <div className="h-8 w-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white text-sm font-bold mr-3">
                      {player.name.charAt(0).toUpperCase()}
                    </div>
                    <span>{player.name} {player.name === user?.name ? '(Вы)' : ''}</span>
                  </div>
                  <span className="player-score">
                    {typeof player.score_total === 'number' ? `${player.score_total} очков` : '0 очков'}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {isUserJoined() && (
          <div className="room-chat">
            <ChatBox 
              roomCode={roomId || ''}
              isExplaining={false}
              messages={chatMessages}
              onSendMessage={handleSendChatMessage}
            />
          </div>
        )}

        {joinError && <div className="error-message">{joinError}</div>}

        <div className="actions space-y-4">
          {isUserJoined() ? (
            <>
              {isRoomCreator() && (
                <button 
                  id="start-game-button"
                  className="start-button"
                  onClick={(e) => {
                    e.preventDefault();
                    handleStartGame();
                  }}
                  disabled={!(room && room.player_count >= 2 && room.status === 'waiting')}
                >
                  <div className="flex items-center justify-center">
                    <span className="mr-3">🎮</span>
                    <span>{deleting ? 'Запуск игры...' : 'Начать игру'}</span>
                  </div>
                </button>
              )}

              {!(room && room.player_count >= 2 && room.status === 'waiting') && (
                <p className="text-red-500 text-sm text-center bg-red-50 p-3 rounded-lg">
                  Для начала игры необходимо минимум 2 игрока и статус комнаты &quot;Ожидание&quot;.
                </p>
              )}

              {!isRoomCreator() && room.status === 'waiting' && (
                <div className="waiting-message">
                  <p className="flex items-center justify-center">
                    <span className="mr-2">⌛</span>
                    Ожидание запуска игры создателем комнаты...
                  </p>
                </div>
              )}

              {room && room.players.length > 0 && room.players[0].name === user?.name && (
                <button 
                  onClick={handleCloseRoom}
                  disabled={deleting}
                  className="danger-button"
                >
                  <div className="flex items-center justify-center">
                    <span className="mr-3">🚫</span>
                    <span>{deleting ? 'Закрытие...' : 'Закрыть лобби'}</span>
                  </div>
                </button>
              )}
            </>
          ) : (
            <button 
              onClick={handleJoinRoom} 
              disabled={joining || (room ? room.is_full : false)}
              className="bg-gradient-to-r from-blue-600 to-indigo-600"
            >
              <div className="flex items-center justify-center">
                <span className="mr-3">🚪</span>
                <span>{joining ? 'Присоединение...' : 'Присоединиться к комнате'}</span>
              </div>
            </button>
          )}

          <button 
            onClick={isUserJoined() ? handleLeaveRoom : () => navigate('/')} 
            className="secondary-button"
          >
            <div className="flex items-center justify-center">
              <span className="mr-3">{isUserJoined() ? '🚶' : '🏠'}</span>
              <span>{isUserJoined() ? 'Выйти из комнаты' : 'Вернуться на главную'}</span>
            </div>
          </button>
        </div>
      </div>

      {isConfirmDialogOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 transition-all duration-300"
          onClick={() => setIsConfirmDialogOpen(false)}>
          <div 
            className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4 animate-in fade-in zoom-in duration-200"
            onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-800">Закрыть комнату</h3>
            </div>
            <p className="text-gray-600 mb-6 ml-16">Вы уверены, что хотите закрыть комнату? Все игроки будут удалены из неё.</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setIsConfirmDialogOpen(false)}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-lg transition-colors font-medium border border-gray-200"
              >
                Отмена
              </button>
              <button
                onClick={confirmCloseRoom}
                disabled={deleting}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors font-medium flex items-center"
              >
                {deleting ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Закрытие...
                  </>
                ) : 'Закрыть комнату'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Room;