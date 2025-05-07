import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Input } from "../ui/input";
import { Label } from "../ui/label";
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

        if (newPassword.length < 6) {
            setError('Пароль должен содержать минимум 6 символов');
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
            <div className="max-w-md mx-auto p-5 border border-gray-300 rounded-lg bg-gradient-to-br from-cyan-100 to-cyan-300 shadow-lg">
                <h2 className="text-center mb-5 text-black text-2xl">Профиль</h2>
                <p>Пользователь не авторизован.</p>
                <Button onClick={() => navigate('/login')} className="w-full py-3 mt-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition">
                    Войти
                </Button>
            </div>
        );
    }

    return (
        <div className="max-w-md mx-auto p-5 border border-gray-300 rounded-lg bg-gradient-to-br from-cyan-100 to-cyan-300 shadow-lg">
            <h2 className="text-center mb-5 text-black text-2xl">Профиль</h2>
            <div className="bg-white bg-opacity-80 p-4 rounded-md mb-5 border border-gray-200 backdrop-blur-sm">
                <p><strong>Имя:</strong> {user.name}</p>
                <p><strong>Email:</strong> {user.email}</p>
            </div>

            <Button
                onClick={() => setIsModalOpen(true)}
                className="w-full py-3 mt-2 bg-blue-400 text-white rounded-md hover:bg-blue-500 transition"
            >
                Сменить пароль
            </Button>

            <Button onClick={() => navigate('/')} className="w-full py-3 mt-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition">
                Вернуться на главную
            </Button>

            {isModalOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-[1000]">
                    <div className="bg-gradient-to-br from-yellow-200 to-green-200 p-6 rounded-md w-full max-w-sm border border-gray-300 shadow-lg">
                        <h3 className="text-center mb-4 text-black text-xl">Смена пароля</h3>
                        <form onSubmit={handlePasswordChange}>
                            <div className="mb-4">
                                <Label className="block mb-1 font-bold text-gray-800">Текущий пароль:</Label>
                                <Input
                                    type="password"
                                    value={currentPassword}
                                    onChange={(e) => setCurrentPassword(e.target.value)}
                                    required
                                    className="w-full p-2 border border-gray-300 rounded-md bg-white bg-opacity-80"
                                />
                            </div>
                            <div className="mb-4">
                                <Label className="block mb-1 font-bold text-gray-800">Новый пароль:</Label>
                                <Input
                                    type="password"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    required
                                    className="w-full p-2 border border-gray-300 rounded-md bg-white bg-opacity-80"
                                />
                            </div>
                            <div className="mb-4">
                                <Label className="block mb-1 font-bold text-gray-800">Подтвердите пароль:</Label>
                                <Input
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    required
                                    className="w-full p-2 border border-gray-300 rounded-md bg-white bg-opacity-80"
                                />
                            </div>

                            {error && (
                                <div className="text-red-600 mb-4 p-[10px] bg-white bg-opacity-[0.7] rounded-md text-center">{error}</div>
                            )}
                            {successMessage && (
                                <div className="text-green-600 mb-[10px] p-[10px] bg-white bg-opacity-[0.7] rounded-md text-center">{successMessage}</div>
                            )}

                            <div className="flex gap-x-[10px] mt-[20px]">
                                <Button
                                    type="submit"
                                    disabled={isLoading}
                                    className={`flex-grow py-[12px] ${isLoading ? 'bg-green' : 'bg-green'} text-white rounded-md transition`}
                                >
                                    {isLoading ? 'Сохранение...' : 'Сохранить изменения'}
                                </Button>
                                <Button
                                    type="button"
                                    onClick={() => {
                                        setIsModalOpen(false);
                                        setError('');
                                        setSuccessMessage('');
                                    }}
                                    className="flex-grow py-[12px] border border-black text-black rounded-md hover:bg-black hover:bg-opacity-[0.1]"
                                >
                                    Отмена
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