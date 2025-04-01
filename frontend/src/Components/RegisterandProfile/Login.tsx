import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getApiBaseUrl } from '../../utils/config';
import { api } from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
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
      const loginResult = await api.auth.login(email, password);
      
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
      
      // Небольшая задержка перед переходом, чтобы контекст успел обновиться
      setTimeout(() => {
        navigate(from || '/');
      }, 100);
    } catch (error: any) {
      setError(error.message || 'Произошла ошибка при входе');
      setIsLoading(false);
    }
  };

  const goToRegister = () => {
    navigate('/register');
  };

  return (
    <div className="login-container">
      <h2>Вход</h2>
      {error && <div className="error-message">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email">Email:</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="password">Пароль:</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Загрузка...' : 'Войти'}
        </button>
      </form>
      <div className="register-link">
        <p>Нет аккаунта? <button onClick={goToRegister}>Зарегистрироваться</button></p>
      </div>
    </div>
  );
};

export default Login;
