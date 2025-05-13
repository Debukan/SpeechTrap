import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Alert, AlertDescription } from '../ui/alert';

const Profile: React.FC = () => {
    const { user, isAuthenticated, updatePassword } = useAuth();
    const navigate = useNavigate();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [successMessage, setSuccessMessage] = useState('');

    const gameWords = [
        'Табу', 'Слово', 'Ассоциация', 'Описание', 'Загадка', 
        'Угадай', 'Синоним', 'Команда', 'Фраза', 'Общение',
        'Игра', 'Объяснение', 'Секрет', 'Профиль', 'Аккаунт'
    ];

    useEffect(() => {
        if (!isAuthenticated) {
            navigate('/login', { state: { from: '/profile' } });
        }
    }, [isAuthenticated, navigate]);

    const handlePasswordChange = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccessMessage('');

        if (newPassword !== confirmPassword) {
            setError('Новые пароли не совпадают');
            return;
        }

        if (newPassword.length < 8) {
            setError('Пароль должен содержать минимум 8 символов');
            return;
        }

        try {
            setIsLoading(true);
            await updatePassword(currentPassword, newPassword);
            setSuccessMessage('Пароль успешно изменён!');
            setTimeout(() => {
                setIsModalOpen(false);
                setCurrentPassword('');
                setNewPassword('');
                setConfirmPassword('');
                setSuccessMessage('');
            }, 2000);
        } catch (err: any) {
            setError(err.message || 'Ошибка при смене пароля');
        } finally {
            setIsLoading(false);
        }
    };

    if (!isAuthenticated || !user) {
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
                        <div className="p-8 bg-gradient-to-br from-white to-blue-50 relative">
                            <div className="text-center mb-6">
                                <h2 className="text-3xl font-bold text-blue-800 mb-2">Профиль</h2>
                                <p className="text-blue-600 opacity-75">Пользователь не авторизован</p>
                            </div>
                            
                            <Button 
                                onClick={() => navigate('/login')} 
                                className="menu-button w-full h-14 bg-gradient-to-r from-blue-600 to-blue-800 hover:from-blue-700 hover:to-blue-900 text-white text-lg font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
                            >
                                <div className="flex items-center justify-center h-full">
                                    <span className="mr-3 flex-shrink-0">🔑</span>
                                    <span>Войти в аккаунт</span>
                                </div>
                            </Button>
                        </div>
                    </div>
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
                            <div className="absolute -top-2 -left-2 text-5xl opacity-20">👤</div>
                            <div className="absolute -bottom-2 -right-2 text-5xl opacity-20">📋</div>
                            <h2 className="text-3xl font-bold text-blue-800 mb-2">Профиль</h2>
                            <p className="text-blue-600 opacity-75 text-base">Управление учетной записью</p>
                        </div>
                        
                        <div className="bg-white/80 rounded-xl p-6 shadow-md border border-blue-100 mb-6">
                            <div className="flex items-center">
                                <div className="h-12 w-12 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white text-xl font-bold shadow-md">
                                    {user.name.charAt(0).toUpperCase()}
                                </div>
                                <div className="ml-4">
                                    <h3 className="font-bold text-blue-800">{user.name}</h3>
                                    <p className="text-sm text-blue-600">{user.email}</p>
                                </div>
                            </div>
                        </div>
                        
                        <div className="space-y-4">
                            <Button 
                                onClick={() => setIsModalOpen(true)}
                                className="menu-button w-full h-12 bg-gradient-to-r from-blue-600 to-blue-800 hover:from-blue-700 hover:to-blue-900 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
                            >
                                <div className="flex items-center justify-center h-full">
                                    <span className="mr-3 flex-shrink-0">🔒</span>
                                    <span>Сменить пароль</span>
                                </div>
                            </Button>
                            
                            <Button 
                                onClick={() => navigate('/')}
                                className="menu-button w-full h-12 bg-gradient-to-r from-purple-600 to-purple-800 hover:from-purple-700 hover:to-purple-900 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
                            >
                                <div className="flex items-center justify-center h-full">
                                    <span className="mr-3 flex-shrink-0">↩️</span>
                                    <span>Вернуться на главную</span>
                                </div>
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            {isModalOpen && (
                <div className="fixed inset-0 flex justify-center items-center z-50 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white rounded-xl shadow-xl overflow-hidden max-w-md w-full relative z-10 animate-fadeIn">
                        <div className="p-6 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white">
                            <h3 className="text-xl font-bold">Смена пароля</h3>
                            <p className="text-sm opacity-80">Введите текущий и новый пароль</p>
                        </div>
                        
                        <form onSubmit={handlePasswordChange} className="p-6 space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="currentPassword" className="text-blue-800 font-semibold">Текущий пароль:</Label>
                                <Input
                                    id="currentPassword"
                                    type="password"
                                    value={currentPassword}
                                    onChange={(e) => setCurrentPassword(e.target.value)}
                                    required
                                    className="h-10 border-2 border-blue-200 focus:border-blue-500 focus:ring-blue-200"
                                />
                            </div>
                            
                            <div className="space-y-2">
                                <Label htmlFor="newPassword" className="text-blue-800 font-semibold">Новый пароль:</Label>
                                <Input
                                    id="newPassword"
                                    type="password"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    required
                                    className="h-10 border-2 border-blue-200 focus:border-blue-500 focus:ring-blue-200"
                                />
                                <p className="text-xs text-blue-500">Минимум 8 символов</p>
                            </div>
                            
                            <div className="space-y-2">
                                <Label htmlFor="confirmPassword" className="text-blue-800 font-semibold">Подтвердите пароль:</Label>
                                <Input
                                    id="confirmPassword"
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    required
                                    className="h-10 border-2 border-blue-200 focus:border-blue-500 focus:ring-blue-200"
                                />
                            </div>

                            {error && (
                                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-center">
                                    <p className="text-red-600 text-sm">{error}</p>
                                </div>
                            )}
                            
                            {successMessage && (
                                <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-center">
                                    <p className="text-green-600 text-sm">{successMessage}</p>
                                </div>
                            )}
                            
                            <div className="flex space-x-3 pt-4">
                                <Button
                                    type="button"
                                    onClick={() => {
                                        setIsModalOpen(false);
                                        setError('');
                                        setSuccessMessage('');
                                        setCurrentPassword('');
                                        setNewPassword('');
                                        setConfirmPassword('');
                                    }}
                                    className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800"
                                >
                                    Отмена
                                </Button>
                                
                                <Button
                                    type="submit"
                                    disabled={isLoading}
                                    className="flex-1 bg-gradient-to-r from-blue-600 to-blue-800 hover:from-blue-700 hover:to-blue-900 text-white"
                                >
                                    {isLoading ? 'Сохранение...' : 'Сохранить'}
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Profile;