import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getApiBaseUrl } from '../../utils/config';
import { api } from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import './Login.css';

interface LocationState {
  from?: string;
}

const Login: React.FC = () => {
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { from } = (location.state as LocationState) || { from: '/' };
  const apiBaseUrl = getApiBaseUrl();
  const { login } = useAuth();

  const gameWords = [
    'Табу', 'Слово', 'Ассоциация', 'Описание', 'Загадка', 
    'Угадай', 'Синоним', 'Команда', 'Фраза', 'Общение',
    'Игра', 'Объяснение', 'Секрет', 'Вход', 'Аккаунт'
  ];

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const loginResult = await api.auth.login(email.trim(), password);

      if (loginResult.error) {
        throw new Error(loginResult.error);
      }

      const { access_token } = loginResult.data!;

      // Получаем данные профиля
      const profileResult = await api.auth.getProfile(access_token);

      if (profileResult.error) {
        throw new Error(profileResult.error);
      }

      // Типизация данных пользователя
      const userData = profileResult.data as {
        id: number;
        name: string;
        email: string;
      };

      await login(access_token, userData);

      toast.success('Успешная авторизация!', {
        duration: 4000,
      });
      // Небольшая задержка перед переходом
      setTimeout(() => {
        navigate(from || '/');
      }, 100);
    } catch (error: any) {
      setError(error.message || 'Произошла ошибка при входе');
    } finally {
      setIsLoading(false);
    }
  };

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
              opacity: 0.15
            }}
          >
            {word}
          </div>
        ))}
      </div>
      
      <div className="flex justify-center items-center">
        <div className="w-full max-w-md bg-white rounded-xl shadow-xl overflow-hidden relative z-10">
          <div className="absolute -top-10 -left-10 w-24 h-24 bg-purple-200 rounded-full opacity-50 speech-bubble-decoration"></div>
          <div className="absolute -bottom-10 -right-10 w-28 h-28 bg-blue-200 rounded-full opacity-50 speech-bubble-decoration"></div>
          
          <div className="p-8 bg-gradient-to-br from-white to-blue-50 relative">
            <div className="absolute inset-0 opacity-10 bg-repeat" style={{ 
              backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 63c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm57-13c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9-21c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM60 91c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM35 41c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM12 60c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z' fill='%232563eb' fill-opacity='0.2' fill-rule='evenodd'/%3E%3C/svg%3E\")"
            }}></div>
            
            <div className="text-center mb-6 relative">
              <div className="absolute -top-2 -left-2 text-5xl opacity-20">🔑</div>
              <div className="absolute -bottom-2 -right-2 text-5xl opacity-20">🔐</div>
              <h2 className="text-3xl font-bold text-blue-800 mb-2">Вход</h2>
              <p className="text-blue-600 opacity-75 text-base">Войдите в свой аккаунт</p>
            </div>
            
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-center">
                <p className="text-red-600">{error}</p>
              </div>
            )}
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-blue-800 font-semibold">Email:</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  required
                  className="h-12 border-2 border-blue-200 focus:border-blue-500 focus:ring-blue-200 px-4"
                  placeholder="Введите ваш email"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-blue-800 font-semibold">Пароль:</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  required
                  className="h-12 border-2 border-blue-200 focus:border-blue-500 focus:ring-blue-200 px-4"
                  placeholder="Введите ваш пароль"
                />
              </div>

              <Button 
                type="submit" 
                disabled={isLoading}
                className="menu-button w-full h-14 bg-gradient-to-r from-blue-600 to-blue-800 hover:from-blue-700 hover:to-blue-900 text-white text-lg font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center mt-6"
              >
                <div className="flex items-center justify-center h-full">
                  <span className="mr-3 flex-shrink-0">🔓</span>
                  <span>{isLoading ? 'Вход...' : 'Войти'}</span>
                </div>
              </Button>
            </form>
            
            <div className="relative flex items-center justify-center my-6">
              <div className="absolute left-0 right-0 h-px bg-blue-100"></div>
              <span className="relative px-4 bg-gradient-to-r from-white to-blue-50 text-blue-500 font-medium">или</span>
            </div>
            
            <Button 
              onClick={() => navigate('/register')}
              className="menu-button w-full h-12 bg-gradient-to-r from-purple-600 to-purple-800 hover:from-purple-700 hover:to-purple-900 text-white text-base font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
              disabled={isLoading}
            >
              <div className="flex items-center justify-center h-full">
                <span className="mr-3 flex-shrink-0">✏️</span>
                <span>Нет аккаунта? Зарегистрироваться</span>
              </div>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
