import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getApiBaseUrl } from '../../utils/config';
import { testCorsSettings } from '../../utils/debug';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Card } from '../ui/card';
import { toast } from 'sonner';

import './Register.css';

const Register: React.FC = () => {
  const [name, setName] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const navigate = useNavigate();
  const apiBaseUrl = getApiBaseUrl();

  // Валидация формы
  const validateForm = (): boolean => {
    if (name.trim().length === 0) {
      setError('Имя не может быть пустым');
      return false;
    }

    if (email.trim().length === 0) {
      setError('Email не может быть пустым');
      return false;
    }

    if (!email.includes('@')) {
      setError('Email должен содержать символ @');
      return false;
    }

    if (password.length < 6) {
      setError('Пароль должен содержать минимум 6 символов');
      return false;
    }

    return true;
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');

    if (!validateForm()) return;

    setIsLoading(true);

    try {
      const response = await fetch(`${apiBaseUrl}/api/users/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        credentials: 'omit',
        body: JSON.stringify({ name, email, password }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          errorText.includes('email уже существует')
            ? 'Пользователь с таким email уже существует'
            : `Ошибка при регистрации (${response.status})`,
        );
      }

      toast.success('Регистрация успешна!', {
        description: 'Теперь вы можете войти в систему.',
        duration: 4000,
      });
      navigate('/login');
    } catch (error: any) {
      setError(error.message || 'Произошла ошибка при регистрации');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto p-6 rounded-lg shadow-lg bg-gradient-to-br from-cyan-100 to-cyan-300">
      <h2 className="text-center text-2xl font-semibold mb-6 text-gray-800">Регистрация</h2>
      {error && (
        <div className="mb-4 text-red-600 font-medium">{error}</div>
      )}
      <form onSubmit={handleSubmit} className="space-y-5">

        <Label htmlFor="name">Имя:</Label>

        <Input
          id="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isLoading}
          required
        />


        <Label htmlFor="email">Email:</Label>

        <Input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={isLoading}
          required
        />
        <Label htmlFor="password">Пароль:</Label>

        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={isLoading}
          required
        />


        <Button type="submit" disabled={isLoading} className="w-full">
          {isLoading ? 'Загрузка...' : 'Зарегистрироваться'}
        </Button>
      </form>

      <div className="mt-6 text-center">
        <p className="text-gray-700">
                    Уже есть аккаунт?{' '}
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="text-white-600 hover:underline font-medium"
            disabled={isLoading}
          >
                        Войти
          </button>
        </p>
      </div>
    </div>
  );
};

export default Register;