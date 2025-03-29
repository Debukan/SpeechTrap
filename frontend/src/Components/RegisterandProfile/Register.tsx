import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getApiBaseUrl } from '../../utils/config';
import { api } from '../../utils/api';
import { testCorsSettings } from '../../utils/debug';
import './Register.css';

interface RegisterProps {
    onRegister: (userData: { name: string; email: string; password: string }) => void;
}

const Register: React.FC<RegisterProps> = ({ onRegister }) => {
    const [name, setName] = useState<string>('');
    const [email, setEmail] = useState<string>('');
    const [password, setPassword] = useState<string>('');
    const [error, setError] = useState<string>('');
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const navigate = useNavigate();
    const apiBaseUrl = getApiBaseUrl();

    // Базовая валидация полей формы
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

    // Тестирование CORS при монтировании компонента
    useEffect(() => {
        if (process.env.NODE_ENV === 'development') {
            testCorsSettings()
                .catch(err => console.error('CORS test error:', err));
        }
    }, []);

    const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setError('');
        
        // Валидация формы перед отправкой
        if (!validateForm()) {
            return;
        }
        
        setIsLoading(true);
        
        try {
            console.log('Sending registration data:', { name, email, password });
            
            // Прямой запрос без credentials для обхода проблем с CORS
            const response = await fetch(`${apiBaseUrl}/api/users/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                credentials: 'omit',
                body: JSON.stringify({ name, email, password }),
            });
            
            console.log('Registration response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Registration error response:', errorText);
                throw new Error(
                    errorText.includes('email уже существует') 
                        ? 'Пользователь с таким email уже существует'
                        : `Ошибка при регистрации (${response.status})`
                );
            }
            
            onRegister({ name, email, password });
            
            alert('Регистрация успешна! Теперь вы можете войти в систему.');
            navigate('/login');
        } catch (error: any) {
            console.error('Registration error:', error);
            setError(error.message || 'Произошла ошибка при регистрации');
        } finally {
            setIsLoading(false);
        }
    };

    const goToLogin = () => {
        navigate('/login');
    };

    return (
        <div className="register-container">
            <h2>Регистрация</h2>
            {error && <div className="error-message">{error}</div>}
            <form onSubmit={handleSubmit}>
                <div>
                    <label htmlFor="name">Имя:</label>
                    <input
                        type="text"
                        id="name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                    />
                </div>
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
                    {isLoading ? 'Загрузка...' : 'Зарегистрироваться'}
                </button>
            </form>
            <div className="login-link">
                <p>Уже есть аккаунт? <button onClick={goToLogin}>Войти</button></p>
            </div>
            <div className="debug-info" style={{ marginTop: '20px', fontSize: '12px', color: '#666' }}>
                <p>Статус регистрации: {isLoading ? 'Отправка запроса...' : error ? 'Ошибка' : 'Готов к регистрации'}</p>
            </div>
        </div>
    );
};

export default Register;