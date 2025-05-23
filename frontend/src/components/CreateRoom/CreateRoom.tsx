import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from '../../utils/axios-config';
import { getApiBaseUrl } from '../../utils/config';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Slider } from '../ui/slider';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../ui/select';
import './CreateRoom.css';

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

export default function CreateRoom() {
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

  const gameWords = [
    'Табу', 'Слово', 'Ассоциация', 'Описание', 'Загадка', 
    'Угадай', 'Синоним', 'Команда', 'Фраза', 'Общение',
    'Игра', 'Объяснение', 'Секрет', 'Запрет', 'Подсказка',
  ];

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/createroom' } });
      return;
    }

    if (skipActiveCheck) {
      setCheckingStatus(false);
      return;
    }

    const checkActiveRooms = async () => {
      setCheckingStatus(true);
      try {
        const response = await axios.get(`${apiBaseUrl}/api/rooms/active`);
        const activeRooms: Room[] = response.data;
        const userRooms = activeRooms.filter((room) =>
          room.players.some((player) => player.name === user?.name),
        );
        if (userRooms.length > 0) {
          const existingRoom = userRooms[0];
          setError(`Вы уже находитесь в комнате ${existingRoom.code}`);
          setTimeout(() => {
            navigate(`/room/${existingRoom.code}`);
          }, 2000);
        }
      } catch (err) {
        // console.error('Ошибка при проверке активных комнат:', err);
      } finally {
        setCheckingStatus(false);
      }
    };

    checkActiveRooms();
  }, [isAuthenticated, navigate, apiBaseUrl, user, skipActiveCheck]);

  const generateRoomCode = () => {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    return Array.from({ length: 6 }, () =>
      characters.charAt(Math.floor(Math.random() * characters.length)),
    ).join('');
  };

  const handleCreateRoom = async () => {
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
      setSkipActiveCheck(true);
      const response = await axios.post(`${apiBaseUrl}/api/rooms/create`, roomData);
      navigate(`/room/${response.data.code}?justCreated=true`);
    } catch (err) {
      // console.error('Ошибка при создании комнаты:', err);
      if (axios.isAxiosError(err) && err.response) {
        if (err.response.status === 401) {
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

  if (!isAuthenticated) return null;

  if (checkingStatus) {
    return (
      <div className="container mx-auto px-4 py-8 flex justify-center items-center h-full">
        <div className="bg-white rounded-xl shadow-lg p-8 text-center">
          <h2 className="text-2xl font-bold text-blue-800 mb-4">Проверка статуса...</h2>
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-blue-600">Пожалуйста, подождите</p>
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
      
      <div className="flex justify-center items-center">
        <div className="w-full max-w-lg bg-white rounded-xl shadow-xl overflow-hidden relative z-10">
          <div className="absolute -top-10 -left-10 w-24 h-24 bg-purple-200 rounded-full opacity-50 speech-bubble-decoration"></div>
          <div className="absolute -bottom-10 -right-10 w-28 h-28 bg-blue-200 rounded-full opacity-50 speech-bubble-decoration"></div>
          
          <div className="p-8 bg-gradient-to-br from-white to-blue-50 relative">
            <div className="absolute inset-0 opacity-10 bg-repeat" style={{ 
              backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'100\' height=\'100\' viewBox=\'0 0 100 100\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cpath d=\'M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 63c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm57-13c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9-21c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM60 91c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM35 41c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM12 60c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z\' fill=\'%232563eb\' fill-opacity=\'0.2\' fill-rule=\'evenodd\'/%3E%3C/svg%3E")',
            }}></div>
            
            <div className="text-center mb-6 relative">
              <div className="absolute -top-2 -left-2 text-5xl opacity-20">🔧</div>
              <div className="absolute -bottom-2 -right-2 text-5xl opacity-20">🏠</div>
              <h2 className="text-3xl font-bold text-blue-800 mb-2">Создание комнаты</h2>
              <p className="text-blue-600 opacity-75 text-base">Настройте параметры игры</p>
            </div>
            
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-center">
                <p className="text-red-600">{error}</p>
              </div>
            )}
            
            <div className="space-y-6">
              <div className="p-4 bg-white rounded-lg shadow-sm">
                <div className="mb-5">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-blue-800 font-semibold">Количество игроков:</span>
                    <span className="text-blue-800 font-bold bg-blue-100 px-3 py-1 rounded-full">{maxPlayers}</span>
                  </div>
                  <Slider
                    min={2}
                    max={8}
                    step={1}
                    value={[maxPlayers]}
                    onValueChange={([val]: number[]) => setMaxPlayers(val)}
                    className="slider-custom"
                  />
                  <div className="flex justify-between text-xs text-blue-500 mt-1">
                    <span>2</span>
                    <span>8</span>
                  </div>
                </div>

                <div className="mb-5">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-blue-800 font-semibold">Время раунда (мин):</span>
                    <span className="text-blue-800 font-bold bg-blue-100 px-3 py-1 rounded-full">{roundTime}</span>
                  </div>
                  <Slider
                    min={1}
                    max={5}
                    step={1}
                    value={[roundTime]}
                    onValueChange={([val]: number[]) => setRoundTime(val)}
                    className="slider-custom"
                  />
                  <div className="flex justify-between text-xs text-blue-500 mt-1">
                    <span>1</span>
                    <span>5</span>
                  </div>
                </div>

                <div className="mb-5">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-blue-800 font-semibold">Количество раундов:</span>
                    <span className="text-blue-800 font-bold bg-blue-100 px-3 py-1 rounded-full">{rounds}</span>
                  </div>
                  <Slider
                    min={1}
                    max={20}
                    step={1}
                    value={[rounds]}
                    onValueChange={([val]: number[]) => setRounds(val)}
                    className="slider-custom"
                  />
                  <div className="flex justify-between text-xs text-blue-500 mt-1">
                    <span>1</span>
                    <span>20</span>
                  </div>
                </div>

                <div className="mb-3">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-blue-800 font-semibold">Сложность:</span>
                  </div>
                  <div className="select-container w-full relative pointer-events-auto">
                    <Select value={difficulty} onValueChange={setDifficulty}>
                      <SelectTrigger className="w-full select-trigger bg-white border-2 border-blue-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all duration-200 h-12 text-blue-800 cursor-pointer">
                        <SelectValue placeholder="Выберите сложность" />
                      </SelectTrigger>
                      <SelectContent className="z-50">
                        <SelectItem value="basic" className="cursor-pointer">Базовая</SelectItem>
                        <SelectItem value="medium" className="cursor-pointer">Средняя</SelectItem>
                        <SelectItem value="hard" className="cursor-pointer">Сложная</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
              
              <Button 
                onClick={handleCreateRoom}
                disabled={isLoading || error.includes('Вы уже находитесь в комнате')}
                className="menu-button w-full h-14 bg-gradient-to-r from-blue-600 to-blue-800 hover:from-blue-700 hover:to-blue-900 text-white text-lg font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
              >
                <div className="flex items-center justify-center h-full">
                  <span className="mr-3 flex-shrink-0">🏠</span>
                  <span>{isLoading ? 'Создание...' : 'Создать комнату'}</span>
                </div>
              </Button>
              
              <Button 
                onClick={() => navigate('/')}
                className="menu-button w-full h-12 bg-gradient-to-r from-gray-500 to-gray-600 hover:from-gray-600 hover:to-gray-700 text-white text-base font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
              >
                <div className="flex items-center justify-center h-full">
                  <span className="mr-3 flex-shrink-0">↩️</span>
                  <span>Вернуться в главное меню</span>
                </div>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
