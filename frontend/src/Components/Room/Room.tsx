import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import axios from '../../utils/axios-config';
import { getApiBaseUrl } from '../../utils/config';
import { useAuth } from '../../context/AuthContext';
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

    // Проверка авторизации при первой загрузке
    useEffect(() => {
        if (!isAuthenticated && roomId) {
            navigate('/login', { state: { from: `/room/${roomId}` } });
        }
    }, [isAuthenticated, roomId, navigate]);

    // Проверка, присоединился ли текущий пользователь к комнате
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
            // Получаем информацию о комнате по коду
            const response = await axios.get(`${apiBaseUrl}/api/rooms/${roomId}`);
            setRoom(response.data);
            
            if (justCreated && user && !response.data.players.some((p: Player) => p.name === user.name)) {
                console.log('Room just created, marking user as joined');
                const updatedRoom = { 
                    ...response.data,
                    players: response.data.players
                };
                setRoom(updatedRoom);
            }
        } catch (err) {
            console.error('Ошибка при получении данных комнаты:', err);
            if (axios.isAxiosError(err) && err.response) {
                setError(err.response.data.detail || 'Не удалось загрузить данные комнаты');
            } else {
                setError('Произошла ошибка при соединении с сервером');
            }
        } finally {
            setLoading(false);
        }
    };

    // Инициализация WebSocket подключения
    useEffect(() => {
        if (!roomId) return;

        fetchRoomData();

        const connectWebSocket = () => {
            if (!user) {
                console.log('WebSocket не инициализирован: пользователь не авторизован');
                return;
            }

            const wsUrl = `${wsBaseUrl}/api/ws/${roomId}/${user.id}`;
            console.log('Connecting to WebSocket:', wsUrl);

            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('WebSocket подключение установлено');
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === 'room_update') {
                        setRoom(data.room);
                    } else if (data.type === 'player_joined') {
                        setRoom(prevRoom => {
                            if (!prevRoom) return prevRoom;

                            const playerExists = prevRoom.players.some(p => p.id === data.player.id);

                            if (playerExists) return prevRoom;

                            return {
                                ...prevRoom,
                                players: [...prevRoom.players, data.player],
                                player_count: prevRoom.player_count + 1
                            };
                        });
                    } else if (data.type === 'player_left') {
                        // Обновление списка игроков, если кто-то покинул комнату
                        setRoom(prevRoom => {
                            if (!prevRoom) return prevRoom;

                            return {
                                ...prevRoom,
                                players: prevRoom.players.filter(p => p.id !== data.player_id),
                                player_count: prevRoom.player_count - 1
                            };
                        });
                    } else if (data.type === 'game_started') {
                        // Обновление статуса игры
                        setRoom(prevRoom => prevRoom ? {...prevRoom, status: 'PLAYING'} : null);
                    } else if (data.type === 'room_closed') {
                        alert('Комната была закрыта создателем');
                        navigate('/');
                    }
                } catch (error) {
                    console.error('Ошибка при обработке сообщения WebSocket:', error);
                }
            };

            ws.onerror = (error) => {
                console.error('Ошибка WebSocket:', error);
            };

            ws.onclose = (event) => {
                console.log('WebSocket соединение закрыто:', event.code, event.reason);
                
                // Проверяем, была ли комната закрыта специально или произошел разрыв соединения
                if (event.code === 1000 || event.code === 1001) {
                    console.log('Закрытие WebSocket');
                } else if (event.code === 1008 || event.code === 403) {
                    console.log('Комната не существует или доступ запрещен');
                    if (event.reason && event.reason.includes('not found')) {
                        alert('Комната была закрыта или не существует');
                        navigate('/');
                    }
                } else {
                    console.log('Неожиданное закрытие соединения, пытаемся переподключиться');
                    setTimeout(connectWebSocket, 3000);
                }
            };

            socketRef.current = ws;
        };

        connectWebSocket();

        // Закрытие соединения при размонтировании компонента
        return () => {
            if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
                socketRef.current.close();
            }
        };
    }, [roomId, user, wsBaseUrl, navigate]);

    // Обработчик присоединения к комнате
    const handleJoinRoom = async () => {
        if (!isAuthenticated) {
            navigate('/login', { state: { from: `/room/${roomId}` } });
            return;
        }

        if (!roomId || !user) return;

        setJoining(true);
        setJoinError(null);

        try {
            console.log(`Присоединение к комнате ${roomId} пользователя ${user.id}`);
            
            const joinResponse = await axios.post(`${apiBaseUrl}/api/rooms/join/${roomId}/${user.id}`);
            console.log('Ответ от сервера при присоединении:', joinResponse.data);
            
            const response = await axios.get(`${apiBaseUrl}/api/rooms/${roomId}`);
            setRoom(response.data);
            
            alert(joinResponse.data.message || 'Вы успешно присоединились к комнате');
        } catch (err) {
            console.error('Ошибка при присоединении к комнате:', err);
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

    // Функция для закрытия лобби
    const handleCloseRoom = async () => {
        if (!roomId || !user) return;

        if (!window.confirm('Вы уверены, что хотите закрыть комнату? Все игроки будут удалены из неё.')) {
            return;
        }

        setDeleting(true);

        try {
            // Закрываем WebSocket соединение перед удалением комнаты
            if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
                socketRef.current.close(1000, 'Room closed by owner');
            }
            
            await axios.delete(`${apiBaseUrl}/api/rooms/${roomId}`);
            navigate('/');
        } catch (err) {
            console.error('Ошибка при закрытии комнаты:', err);
            if (axios.isAxiosError(err) && err.response) {
                alert(err.response.data.detail || 'Не удалось закрыть комнату');
            } else {
                alert('Произошла ошибка при соединении с сервером');
            }
            setDeleting(false);
        }
    };

    const handleStartGame = () => {
        console.log('Игра началась!');
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
                <p>Статус комнаты: {room.status === 'WAITING' ? 'Ожидание' : room.status}</p>
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
                                {player.score !== undefined && <span className="player-score">{player.score} очков</span>}
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            {joinError && <div className="error-message">{joinError}</div>}

            <div className="actions">
                {isUserJoined() ? (
                    <>
                        <button 
                            onClick={handleStartGame}
                            disabled={room.player_count < 2 || room.status !== 'WAITING'}
                        >
                            Начать игру
                        </button>

                        {/* Добавляем кнопку закрытия лобби, если пользователь - первый в списке игроков (создатель) */}
                        {room.players.length > 0 && room.players[0].name === user?.name && (
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
                        disabled={joining || room.is_full}
                    >
                        {joining ? 'Присоединение...' : 'Присоединиться к комнате'}
                    </button>
                )}

                <button onClick={() => navigate('/')} className="secondary-button">
                    Вернуться на главную
                </button>
            </div>
        </div>
    );
};

export default Room;