import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from '../../utils/axios-config';
import { getApiBaseUrl } from '../../utils/config';
import { useAuth } from '../../context/AuthContext';
import './JoinRoom.css';

interface Player {
    id: number;
    name: string;
    role?: string;
    score?: number;
}

interface Room {
    id: number;
    code: string;
    status: string;
    players: Player[];
    player_count: number;
    max_players: number;
    current_round: number;
    rounds_total: number;
    time_per_round: number;
    is_full: boolean;
}

const JoinRoom: React.FC = () => {
    const [roomCode, setRoomCode] = useState<string>('');
    const [error, setError] = useState<string | null>(null);
    const [joining, setJoining] = useState<boolean>(false);
    const [checkingStatus, setCheckingStatus] = useState(true);
    const navigate = useNavigate();
    const apiBaseUrl = getApiBaseUrl();
    const { user, isAuthenticated } = useAuth();

    // Проверка авторизации и активных комнат при загрузке компонента
    useEffect(() => {
        if (!isAuthenticated) {
            navigate('/login', { state: { from: '/joinroom' } });
            return;
        }

        // Проверка, находится ли пользователь уже в какой-либо активной комнате
        const checkActiveRooms = async () => {
            setCheckingStatus(true);
            try {
                const response = await axios.get(`${apiBaseUrl}/api/rooms/active`);
                const activeRooms: Room[] = response.data;
                
                // Проверка, является ли пользователь участником какой-либо активной комнаты
                const userRooms = activeRooms.filter((room: Room) => 
                    room.players.some((player: Player) => player.name === user?.name)
                );
                
                if (userRooms.length > 0) {
                    // Если пользователь уже в комнате, перенаправляем в неё
                    const existingRoom = userRooms[0];
                    setError(`Вы уже находитесь в комнате ${existingRoom.code}`);
                    setTimeout(() => {
                        navigate(`/room/${existingRoom.code}`);
                    }, 2000);
                }
            } catch (err) {
                console.error('Ошибка при проверке активных комнат:', err);
            } finally {
                setCheckingStatus(false);
            }
        };

        checkActiveRooms();
    }, [isAuthenticated, navigate, apiBaseUrl, user]);

    // Обработчик присоединения к комнате по коду
    const handleJoinRoom = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!roomCode.trim()) {
            setError('Пожалуйста, введите код комнаты');
            return;
        }

        if (!isAuthenticated || !user) {
            navigate('/login', { state: { from: '/join-room' } });
            return;
        }

        setJoining(true);
        setError(null);

        try {
            console.log(`Проверка существования комнаты ${roomCode}`);
            
            // Проверка существование комнаты
            await axios.get(`${apiBaseUrl}/api/rooms/${roomCode}`);
            
            console.log(`Присоединение к комнате ${roomCode} пользователя ${user.id}`);
            
            // Присоединение к комнате
            const joinResponse = await axios.post(`${apiBaseUrl}/api/rooms/join/${roomCode}/${user.id}`);
            console.log('Ответ от сервера при присоединении:', joinResponse.data);
            
            navigate(`/room/${roomCode}`);
        } catch (err) {
            console.error('Ошибка при присоединении к комнате:', err);
            
            if (axios.isAxiosError(err) && err.response) {
                if (err.response.status === 401) {
                    navigate('/login', { state: { from: '/join-room' } });
                } else if (err.response.status === 404) {
                    setError('Комната с таким кодом не найдена');
                } else {
                    setError(err.response.data.detail || 'Не удалось присоединиться к комнате');
                }
            } else {
                setError('Произошла ошибка при соединении с сервером');
            }
        } finally {
            setJoining(false);
        }
    };

    const handleCreateRoom = () => {
        navigate('/createroom');
    };

    // Если пользователь не авторизован, не рендерим контент
    if (!isAuthenticated) {
        return null;
    }

    if (checkingStatus) {
        return (
            <div className="join-room">
                <h1>Проверка статуса...</h1>
                <p>Пожалуйста, подождите</p>
            </div>
        );
    }

    return (
        <div className="join-room-container">
            <h2>Присоединиться к комнате</h2>
            
            {error && <div className="error-message">{error}</div>}
            
            <form onSubmit={handleJoinRoom}>
                <div className="form-group">
                    <label htmlFor="roomCode">Код комнаты:</label>
                    <input
                        type="text"
                        id="roomCode"
                        value={roomCode}
                        onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
                        placeholder="Введите 6-значный код комнаты"
                        maxLength={6}
                        required
                        autoComplete="off"
                    />
                </div>
                
                <button 
                    type="submit" 
                    className="join-button"
                    disabled={joining || !roomCode.trim()}
                >
                    {joining ? 'Присоединение...' : 'Присоединиться к комнате'}
                </button>
            </form>
            
            <div className="divider">или</div>
            
            <button 
                onClick={handleCreateRoom}
                className="create-button"
            >
                Создать новую комнату
            </button>
            
            <button 
                onClick={() => navigate('/')}
                className="back-button"
            >
                Вернуться в главное меню
            </button>
        </div>
    );
};

export default JoinRoom;
