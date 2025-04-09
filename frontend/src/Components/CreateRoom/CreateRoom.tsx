import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import "./CreateRoom.css";
import axios from '../../utils/axios-config';
import { getApiBaseUrl } from '../../utils/config';
import { useAuth } from '../../context/AuthContext';

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

const CreateRoom = () => {
    const [maxPlayers, setMaxPlayers] = useState(2);
    const [roundTime, setRoundTime] = useState(1);
    const [rounds, setRounds] = useState(3);
    const [difficulty, setDifficulty] = useState('basic');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [checkingStatus, setCheckingStatus] = useState(true);
    const [skipActiveCheck, setSkipActiveCheck] = useState(false);
    const navigate = useNavigate();
    const apiBaseUrl = getApiBaseUrl();
    const { isAuthenticated, user } = useAuth();

    // Проверка авторизации и активных комнат при загрузке компонента
    useEffect(() => {
        if (!isAuthenticated) {
            // Если пользователь не авторизован, перенаправляем на страницу входа
            navigate('/login', { state: { from: '/createroom' } });
            return;
        }

        // Пропуск проверку активных комнат, если установлен флаг
        if (skipActiveCheck) {
            setCheckingStatus(false);
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
    }, [isAuthenticated, navigate, apiBaseUrl, user, skipActiveCheck]);

    // Функция для генерации случайного шестизначного кода комнаты
    const generateRoomCode = () => {
        const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        let result = '';
        const charactersLength = characters.length;
        
        for (let i = 0; i < 6; i++) {
            result += characters.charAt(Math.floor(Math.random() * charactersLength));
        }
        
        return result;
    };

    const handleCreateRoom = async () => {
        // Дополнительная проверка авторизации перед отправкой запроса
        if (!isAuthenticated || !user) {
            navigate('/login', { state: { from: '/createroom' } });
            return;
        }

        setIsLoading(true);
        setError('');
        
        const roomData = {
            code: generateRoomCode(),
            max_players: maxPlayers,
            time_per_round: roundTime * 60,
            rounds_total: rounds,
            difficulty,
        };
        
        try {
            // Установка флага, чтобы пропустить проверку активных комнат после создания
            setSkipActiveCheck(true);
            
            const response = await axios.post(`${apiBaseUrl}/api/rooms/create`, roomData);
            
            navigate(`/room/${response.data.code}?justCreated=true`);
        } catch (err) {
            console.error('Ошибка при создании комнаты:', err);
            if (axios.isAxiosError(err) && err.response) {
                if (err.response.status === 401) {
                    // Если получили ошибку авторизации, перенаправляем на страницу входа
                    navigate('/login', { state: { from: '/createroom' } });
                } else {
                    setError(err.response.data.detail || 'Не удалось создать комнату');
                }
            } else {
                setError('Произошла ошибка при соединении с сервером');
            }
            setSkipActiveCheck(false);
        } finally {
            setIsLoading(false);
        }
    };

    // Если пользователь не авторизован, не рендерим контент
    if (!isAuthenticated) {
        return null;
    }

    if (checkingStatus) {
        return (
            <div className="create-room">
                <h1>Проверка статуса...</h1>
                <p>Пожалуйста, подождите</p>
            </div>
        );
    }

    return (
        <div className="create-room">
            <h1>Создание комнаты</h1>
            
            {error && <div className="error-message">{error}</div>}
            
            <label>
                Количество игроков: {maxPlayers}
                <input
                    type="range"
                    className="slider"
                    min="2"
                    max="8"
                    value={maxPlayers}
                    onChange={(e) => setMaxPlayers(parseInt(e.target.value))}
                />
            </label>
            
            <label>
                Время раунда (мин): {roundTime}
                <input
                    type="range"
                    className="slider"
                    min="1"
                    max="5"
                    value={roundTime}
                    onChange={(e) => setRoundTime(parseInt(e.target.value))}
                />
            </label>
            
            <label>
                Количество раундов: {rounds}
                <input
                    type="range"
                    className="slider"
                    min="1"
                    max="20"
                    value={rounds}
                    onChange={(e) => setRounds(parseInt(e.target.value))}
                />
            </label>
            
            <label>
                Сложность:
                <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                >
                    <option value="basic">Базовый</option>
                    <option value="medium">Средний</option>
                    <option value="hard">Сложный</option>
                </select>
            </label>
            
            <button 
                onClick={handleCreateRoom} 
                disabled={isLoading || error.includes('Вы уже находитесь в комнате')}
            >
                {isLoading ? 'Создание...' : 'Создать комнату'}
            </button>
        </div>
    );
};

export default CreateRoom;