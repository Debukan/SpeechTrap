import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import axios from '../../utils/axios-config';
import { getApiBaseUrl } from '../../utils/config';
import { useAuth } from '../../context/AuthContext';
import ChatBox from '../Chat/ChatBox';
import { ChatMessage } from '../../types/chat';
import './Room.css';
import { useToast } from '@chakra-ui/react';

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
    const toast = useToast();

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
                console.log('Игра уже запущена, перенаправляем в игру');
                navigate(`/game/${roomId}`);
                return;
            }
            
            if (justCreated && user && !response.data.players.some((p: Player) => p.name === user.name)) {
                const updatedRoom = { 
                    ...response.data,
                    players: response.data.players
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
                console.log(`WebSocket connection opened to room ${roomId}`);
                fetchRoomData();
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.id && processedMessages.current.has(data.id)) {
                        console.log(`Message with ID=${data.id} already processed, skipping.`);
                        return;
                    }

                    if (data.id) {
                        processedMessages.current.add(data.id);
                    }
                    
                    if (data.type === 'chat_message') {
                        console.log('Получено сообщение чата:', data);
                        setChatMessages(prev => [...prev, data]);
                    } else if (data.type === 'room_update') {
                        console.log('Room update received:', data.room);
                        setRoom(data.room);
                    } else if (data.type === 'player_left') {
                        console.log(`Player left: ID=${data.player_id}, Message: ${data.message}`);
                        setRoom((prevRoom) => {
                            if (!prevRoom) return prevRoom;

                            // Проверяем, существует ли игрок в списке
                            const playerExists = prevRoom.players.some(player => player.id === data.player_id);
                            if (!playerExists) {
                                console.log(`Player with ID=${data.player_id} not found, skipping update.`);
                                return prevRoom;
                            }

                            // Удаляем игрока из списка
                            const updatedPlayers = prevRoom.players.filter(player => player.id !== data.player_id);
                            console.log('Updated players list after user_left/player_left:', updatedPlayers);

                            return {
                                ...prevRoom,
                                players: updatedPlayers,
                                player_count: Math.max(prevRoom.player_count - 1, 0),
                            };
                        });
                    } else if (data.type === 'game_state_update') {
                        console.log('Received game_state_update, checking game state');
                    } else if (data.type === 'player_joined') {
                        console.log('Player joined:', data.player);
                        setRoom(prevRoom => {
                            if (!prevRoom) return prevRoom;

                            const playerExists = prevRoom.players.some(p => p.id === data.player.id);

                            if (playerExists) return prevRoom;

                            const playerWithDefaults = {
                                ...data.player,
                                score: data.player.score ?? 0,
                                role: data.player.role ?? 'waiting'
                            };

                            return {
                                ...prevRoom,
                                players: [...prevRoom.players, playerWithDefaults],
                                player_count: prevRoom.player_count + 1
                            };
                        });
                    } else if (data.type === 'game_started') {
                        console.log('Получено сообщение о начале игры');
                        // Устанавливаем статус комнаты как "playing"
                        console.log('Текущий пользователь перед переходом:', user);
                        if (user) {
                            console.log('Сохраняем данные пользователя в localStorage перед переходом');
                            localStorage.setItem('user', JSON.stringify(user));
                        }
                        setRoom(prevRoom => prevRoom ? {...prevRoom, status: 'playing'} : null);
                        if (socketRef.current) {
                            socketRef.current.close(1000, 'Game started, leaving room');
                        }                       
                        // Перенаправляем пользователя в игру
                        console.log(`Перенаправление на игру: /game/${roomId}`);
                        setTimeout(() => {
                            if (socketRef.current) {
                                socketRef.current.close(1000, 'Game started, leaving room');
                            }
                            console.log(`Перенаправление на игру: /game/${roomId}`);
                            navigate(`/game/${roomId}`);
                        }, 100);
                    } else if (data.type === 'room_closed') {
                        if (socketRef.current) {
                            socketRef.current.close(1000, 'Room closed by owner');
                        }
                        toast({
                            title: 'Комната была закрыта создателем',
                            status: 'info',
                            duration: 4000,
                            isClosable: true,
                            position: 'top',
                        });
                        navigate('/', { replace: true });
                    } else if (data.type === 'player_score_updated') {
                        console.log('Player score updated:', data);
                        setRoom(prevRoom => {
                            if (!prevRoom) return prevRoom;
                            
                            return {
                                ...prevRoom,
                                players: prevRoom.players.map(player => 
                                    player.id === data.player_id 
                                        ? {...player, score: data.score} 
                                        : player
                                )
                            };
                        });
                    }
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                    fetchRoomData();
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                fetchRoomData();
            };

            ws.onclose = (event) => {
                console.log(`WebSocket closed with code ${event.code}, reason: ${event.reason}`);
                const isPlaying = room?.status?.toLowerCase() === "playing";
                console.log(`Текущий статус комнаты при закрытии соединения: ${room?.status}`);
                if (event.code === 1000 || event.code === 1001) {
                    console.log('Нормальное закрытие соединения');
                    if (isPlaying) {
                        console.log('Перенаправляем на страницу игры после нормального закрытия WebSocket');
                        navigate(`/game/${roomId}`);
                    }
                } else if (event.code === 1008 || event.code === 403) {
                    if (event.reason && event.reason.includes('not found')) {
                        toast({
                            title: 'Комната была закрыта или не существует',
                            status: 'info',
                            duration: 4000,
                            isClosable: true,
                            position: 'top',
                        });
                        navigate('/');
                    }
                } else if (isPlaying) {
                    console.log('Обнаружена активная игра, перенаправляем на страницу игры');
                    navigate(`/game/${roomId}`);
                } else {
                    console.log('Attempting to reconnect WebSocket...');
                    setTimeout(connectWebSocket, 3000);
                }
            };

            socketRef.current = ws;
        };

        connectWebSocket();

        return () => {
            if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
                socketRef.current.close();
                console.log('WebSocket closed on room unmount');
            }
        };
    }, [roomId, user, wsBaseUrl, navigate, isAuthenticated, apiBaseUrl, toast]);

    const handleSendChatMessage = async (message: string) => {
        if (!roomId || !user) return;
    
        try {
            await axios.post(`${apiBaseUrl}/api/rooms/${roomId}/chat`, { message });
        } catch (error) {
            console.error('Ошибка при отправке сообщения в чат:', error);
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
            
            toast({
                title: 'Успешно!',
                description: joinResponse.data.message || 'Вы успешно присоединились к комнате',
                status: 'success',
                duration: 4000,
                isClosable: true,
                position: 'top',
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

        if (!window.confirm('Вы уверены, что хотите закрыть комнату? Все игроки будут удалены из неё.')) {
            return;
        }

        setDeleting(true);

        try {
            if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
                socketRef.current.close(1000, 'Room closed by owner');
            }
            
            await axios.delete(`${apiBaseUrl}/api/rooms/${roomId}`);
            navigate('/');
        } catch (err) {
            if (axios.isAxiosError(err) && err.response) {
                toast({
                    title: 'Ошибка',
                    description: err.response.data.detail || 'Не удалось закрыть комнату',
                    status: 'error',
                    duration: 4000,
                    isClosable: true,
                    position: 'top',
                });
            } else {
                toast({
                    title: 'Ошибка',
                    description: 'Произошла ошибка при соединении с сервером',
                    status: 'error',
                    duration: 4000,
                    isClosable: true,
                    position: 'top',
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
            toast({
                title: 'Недостаточно игроков',
                description: 'Для начала игры необходимо минимум 2 игрока',
                status: 'warning',
                duration: 4000,
                isClosable: true,
                position: 'top',
            });
            return;
        }
        
        if (room.status !== 'waiting') {
            toast({
                title: 'Игра уже запущена',
                status: 'info',
                duration: 4000,
                isClosable: true,
                position: 'top',
            });
            return;
        }
        
        try {
            setDeleting(true);
            
            console.log(`Пытаемся начать игру в комнате ${roomId}`);
            
            const response = await axios.post(`${apiBaseUrl}/api/game/${roomId}/start`);
            console.log('Ответ сервера при запуске игры:', response.data);
            
            setTimeout(() => {
                navigate(`/game/${roomId}`);
            }, 500);
        } catch (err) {
            console.error('Ошибка при запуске игры:', err);
            if (axios.isAxiosError(err) && err.response) {
                toast({
                    title: 'Ошибка',
                    description: err.response.data.detail || 'Не удалось запустить игру',
                    status: 'error',
                    duration: 4000,
                    isClosable: true,
                    position: 'top',
                });
            } else {
                toast({
                    title: 'Ошибка',
                    description: 'Произошла ошибка при соединении с сервером',
                    status: 'error',
                    duration: 4000,
                    isClosable: true,
                    position: 'top',
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
            console.log('Успешно покинул лобби:', roomId);
            
            // Перенаправляем после небольшой задержки
            setTimeout(() => {
                navigate('/', { replace: true });
            }, 100);
        } catch (error) {
            console.error('Ошибка при выходе из лобби:', error);
            navigate('/', { replace: true });
        }
    };

    if (!isAuthenticated) {
        return null;
    }

    if (loading) {
        return <div className="menu-container">Загрузка данных комнаты...</div>;
    }

    if (error) {
        return <div className="menu-container">
            <h2>Ошибка</h2>
            <p>{error}</p>
            <button onClick={() => navigate('/')}>Вернуться на главную</button>
        </div>;
    }

    if (!room) {
        return <div className="menu-container">
            <h2>Комната не найдена</h2>
            <button onClick={() => navigate('/')}>Вернуться на главную</button>
        </div>;
    }

    return (
        <div className="menu-container">
            <h2>Комната: {room.code}</h2>
            <div className="room-info">
                <p>Всего раундов: {room.rounds_total}</p>
                <p>Игроков: {room.player_count} из {room.max_players}</p>
                <p>Время раунда: {Math.floor(room.time_per_round / 60)} мин.</p>
                <p>Статус комнаты: {room.status === 'waiting' ? 'Ожидание' : room.status}</p>
            </div>

            <div className="players-list">
                <h3>Игроки в лобби:</h3>
                {room.players.length === 0 ? (
                    <p>Ожидание игроков...</p>
                ) : (
                    <ul>
                        {room.players.map((player) => (
                            <li key={player.id} className={player.name === user?.name ? 'current-player' : ''}>
                                {player.name} {player.name === user?.name ? '(Вы)' : ''}
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

            <div className="actions">
                {isUserJoined() ? (
                    <>
                        {isRoomCreator() && (
                            <button 
                                id="start-game-button"
                                className="start-button"
                                onClick={(e) => {
                                    e.preventDefault();
                                    console.log('Кнопка нажата!');
                                    handleStartGame();
                                }}
                                style={{
                                    cursor: room && room.player_count >= 2 && room.status === 'waiting' ? 'pointer' : 'not-allowed',
                                    backgroundColor: room && room.player_count >= 2 && room.status === 'waiting' ? '#ff9800' : '#cccccc',
                                    position: 'relative',
                                    zIndex: 10
                                }}
                                disabled={!(room && room.player_count >= 2 && room.status === 'waiting')}
                            >
                                {deleting ? 'Запуск игры...' : 'Начать игру'}
                            </button>
                        )}

                        {!(room && room.player_count >= 2 && room.status === 'waiting') && (
                            <p style={{ color: 'red', fontSize: '0.9em' }}>
                                Для начала игры необходимо минимум 2 игрока и статус комнаты "Ожидание".
                            </p>
                        )}

                        {!isRoomCreator() && room.status === 'waiting' && (
                            <div className="waiting-message">
                                Ожидание запуска игры создателем комнаты...
                            </div>
                        )}

                        {room && room.players.length > 0 && room.players[0].name === user?.name && (
                            <button 
                                onClick={handleCloseRoom}
                                disabled={deleting}
                                className="danger-button"
                            >
                                {deleting ? 'Закрытие...' : 'Закрыть лобби'}
                            </button>
                        )}
                    </>
                ) : (
                    <button 
                        onClick={handleJoinRoom} 
                        disabled={joining || (room ? room.is_full : false)}
                    >
                        {joining ? 'Присоединение...' : 'Присоединиться к комнате'}
                    </button>
                )}

                <button 
                    onClick={isUserJoined() ? handleLeaveRoom : () => navigate('/')} 
                    className="secondary-button"
                >
                    {isUserJoined() ? 'Выйти из комнаты' : 'Вернуться на главную'}
                </button>
            </div>
        </div>
    );
};

export default Room;