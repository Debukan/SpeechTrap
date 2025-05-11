import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from '../../utils/axios-config';
import { getApiBaseUrl } from '../../utils/config';
import { useAuth } from '../../context/AuthContext';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle
} from 'card';
import { Button } from 'button';
import { Label } from 'label';
import { Input } from 'input';
import { Slider } from 'slider';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from 'select';
import { Alert, AlertDescription } from 'alert';

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
          room.players.some((player) => player.name === user?.name)
        );
        if (userRooms.length > 0) {
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

  const generateRoomCode = () => {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    return Array.from({ length: 6 }, () =>
      characters.charAt(Math.floor(Math.random() * characters.length))
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
    } catch (err: any) {
      console.error('Ошибка при создании комнаты:', err);
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
    return <div className="text-center p-8">Проверка статуса...</div>;
  }

  return (
    <div className="flex justify-center p-4">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <CardTitle>Создание комнаты</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && <Alert><AlertDescription>{error}</AlertDescription></Alert>}

          <div className="space-y-2">
            <Label>Количество игроков: {maxPlayers}</Label>
            <Slider
              min={2}
              max={8}
              step={1}
              value={[maxPlayers]}
              onValueChange={([val]) => setMaxPlayers(val)}
            />
          </div>

          <div className="space-y-2">
            <Label>Время раунда (мин): {roundTime}</Label>
            <Slider
              min={1}
              max={5}
              step={1}
              value={[roundTime]}
              onValueChange={([val]) => setRoundTime(val)}
            />
          </div>

          <div className="space-y-2">
            <Label>Количество раундов: {rounds}</Label>
            <Slider
              min={1}
              max={20}
              step={1}
              value={[rounds]}
              onValueChange={([val]) => setRounds(val)}
            />
          </div>

          <div className="space-y-2">
            <Label>Сложность</Label>
            <Select value={difficulty} onValueChange={setDifficulty}>
              <SelectTrigger>
                <SelectValue placeholder="Выберите сложность" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="basic">Базовый</SelectItem>
                <SelectItem value="medium">Средний</SelectItem>
                <SelectItem value="hard">Сложный</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button
            onClick={handleCreateRoom}
            disabled={isLoading || error.includes('Вы уже находитесь в комнате')}
          >
            {isLoading ? 'Создание...' : 'Создать комнату'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}