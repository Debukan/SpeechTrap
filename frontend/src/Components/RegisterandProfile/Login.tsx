import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getApiBaseUrl } from '../../utils/config';
import { api } from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Card } from "../ui/card";
import './Login.css';

interface LocationState {
  from?: string;
}

interface LoginProps {
  onLogin: (token: string, userData: any) => void;
}

const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { from } = (location.state as LocationState) || { from: '/' };
  const apiBaseUrl = getApiBaseUrl();
  const { login } = useAuth();

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
      onLogin(access_token, userData);

      // Небольшая задержка перед переходом
      setTimeout(() => {
        navigate(from || '/');
      }, 100);
    } catch (error: any) {
      setError(error.message || 'Произошла ошибка при входе');
    } finally {
      setIsLoading(false); // Убедитесь, что состояние загрузки сбрасывается
    }
  };

  return (

        <Card className="max-w-md mx-auto p-6 rounded-lg shadow-lg bg-gradient-to-br from-cyan-100 to-cyan-300">
          <h2 className="text-center text-2xl font-bold mb-4">Вход</h2>
          {error && <div className="error-message text-red-500">{error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <Label htmlFor="email" className="block text-gray-700 font-medium mb-1">Email:</Label>
              <Input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="border border-gray-300 rounded-lg p-2 w-full focus:outline-none focus:ring focus:ring-white-500 transition duration-200"
              />
            </div>
            <div className="mb-4">
              <Label htmlFor="password" className="block text-gray-700 font-medium mb-1">Пароль:</Label>
              <Input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="border border-gray-300 rounded-lg p-2 w-full focus:outline-none focus:ring focus:ring-white-500 transition duration-200"
              />
            </div>
            <Button type="submit" disabled={isLoading} className={`w-full mt-4 ${isLoading ? 'bg-gray-400' : 'bg-blue-500 hover:bg-blue-600'} transition duration-200`}>
              {isLoading ? (
                  <span className="loader"></span> // Здесь можно добавить спиннер
              ) : (
                  'Войти'
              )}
            </Button>
          </form>
          <div className="register-link mt-4 text-center">
            <p>Нет аккаунта?</p>
            <Button variant="link" onClick={() => navigate('/register')} className="text-white-500 hover:underline">Зарегистрироваться</Button>
          </div>
        </Card>
  );
};

export default Login;
