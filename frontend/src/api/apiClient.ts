import axios from 'axios';
import { getApiBaseUrl } from '../utils/config';

// Получение базового URL API из конфигурации
const API_BASE_URL = getApiBaseUrl();

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Добавляем токен авторизации к каждому запросу, если он доступен
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Интерфейсы для API игры
export interface User {
  id: string;
  username: string;
}

export interface GameState {
  currentWord: string;
  players: { id: string; username: string; score: number }[];
  round: number;
  status: 'WAITING' | 'PLAYING' | 'FINISHED';
  timeLeft?: number;
  currentPlayer?: string;
  rounds_total: number;
  time_per_round?: number;
}

// API для получения списка пользователей
export const fetchUsers = async () => {
  try {
    const response = await apiClient.get('/api/users');
    return response.data;
  } catch (error) {
    console.error('Error fetching users:', error);
    throw error;
  }
};

// API для игры
export const gameApi = {
  // Получение состояния игры
  getGameState: async (roomCode: string): Promise<GameState> => {
    try {
      const response = await apiClient.get(`/api/game/${roomCode}/state`);
      return response.data;
    } catch (error) {
      console.error('Error fetching game state:', error);
      throw error;
    }
  },
  
  // Начало игры
  startGame: async (roomCode: string): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await apiClient.post(`/api/game/${roomCode}/start`);
      return response.data;
    } catch (error) {
      console.error('Error starting game:', error);
      throw error;
    }
  },
  
  // Завершение хода
  endTurn: async (roomCode: string): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await apiClient.post(`/api/game/${roomCode}/end-turn`);
      return response.data;
    } catch (error) {
      console.error('Error ending turn:', error);
      throw error;
    }
  },
  
  // Выход из игры
  leaveGame: async (roomCode: string): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await apiClient.post(`/api/game/${roomCode}/leave`);
      return response.data;
    } catch (error) {
      console.error('Error leaving game:', error);
      throw error;
    }
  },
  
  // Отправка догадки
  submitGuess: async (roomCode: string, guess: string): Promise<{ correct: boolean; message: string }> => {
    try {
      const response = await apiClient.post(`/api/game/${roomCode}/guess`, { guess });
      return response.data;
    } catch (error) {
      console.error('Error submitting guess:', error);
      throw error;
    }
  },

  sendChatMessage: async (roomCode: string, message: string) => {
    const response = await apiClient.post(`/api/game/${roomCode}/chat`, { message });
    return response.data;
  },
};

export default apiClient;
