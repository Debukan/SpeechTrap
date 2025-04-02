import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import axios from '../../utils/axios-config';
import { getApiBaseUrl } from '../../utils/config';
import { useAuth } from '../../context/AuthContext';
import { gameApi } from '../../api/apiClient';
import './Room.css';

interface Player {
    id: number;
    name: string;
    role?: string;
    score?: number;
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
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('WebSocket message received:', data);

                    if (data.type === 'room_update') {
                        console.log('Room update received with players:', data.room.players);
                        setRoom(data.room);
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
                    } else if (data.type === 'player_left') {
                        const playerId = data.player_id || 
                                        (data.player && data.player.id) || 
                                        data.user_id;
                        
                        if (!playerId) {
                            console.error('No player ID in player_left message:', data);
                            fetchRoomData();
                            return;
                        }

                        console.log(`Player left: ID=${playerId}, Message: ${data.message || 'No message'}`);

                        setRoom(prevRoom => {
                            if (!prevRoom) return prevRoom;

                            const filteredPlayers = prevRoom.players.filter(p => p.id !== playerId);
                            
                            if (filteredPlayers.length !== prevRoom.players.length) {
                                return {
                                    ...prevRoom,
                                    players: filteredPlayers,
                                    player_count: prevRoom.player_count - 1
                                };
                            }
                            return prevRoom;
                        });
                    } else if (data.type === 'game_started') {
                        console.log('Получено сообщение о начале игры');
                        setRoom(prevRoom => prevRoom ? {...prevRoom, status: 'PLAYING'} : null);
                        navigate(`/game/${roomId}`);
                    } else if (data.type === 'room_closed') {
                        alert('Комната была закрыта создателем');
                        navigate('/');
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
                
                if (event.code === 1000 || event.code === 1001) {
                } else if (event.code === 1008 || event.code === 403) {
                    if (event.reason && event.reason.includes('not found')) {
                        alert('Комната была закрыта или не существует');
                        navigate('/');
                    }
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
            }
        };
    }, [roomId, user, wsBaseUrl, navigate]);

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
            
            alert(joinResponse.data.message || 'Вы успешно присоединились к комнате');
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
                alert(err.response.data.detail || 'Не удалось закрыть комнату');
            } else {
                alert('Произошла ошибка при соединении с сервером');
            }
            setDeleting(false);
        }
    };

    const handleStartGame = async () => {
        if (!roomId || !room) {
            return;
        }
        
        if (room.player_count < 2) {
            alert('Для начала игры необходимо минимум 2 игрока');
            return;
        }
        
        if (room.status !== 'waiting') {
            alert('Игра уже была запущена');
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
                alert(err.response.data.detail || 'Не удалось запустить игру');
            } else {
                alert('Произошла ошибка при соединении с сервером');
            }
        } finally {
            setDeleting(false);
        }
    };

    const handleLeaveRoom = async () => {
        if (!roomId || !user || !isUserJoined()) return;

        try {
            await gameApi.leaveGame(roomId);
            console.log('Успешно покинул комнату:', roomId);

            if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
                socketRef.current.close(1000, 'User left the room');
            }
            
            navigate('/');
        } catch (error) {
            console.error('Ошибка при выходе из комнаты:', error);
            navigate('/');
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
                <p>Текущий раунд: {room.current_round} из {room.rounds_total}</p>
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
                                <span className="player-score">{typeof player.score === 'number' ? `${player.score} очков` : '0 очков'}</span>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

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