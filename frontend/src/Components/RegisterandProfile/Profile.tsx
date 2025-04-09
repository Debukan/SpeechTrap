import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './Profile.css';

const Profile: React.FC = () => {
    const { user, isAuthenticated } = useAuth();
    const navigate = useNavigate();

    // Если пользователь не авторизован, перенаправляем на страницу логина
    React.useEffect(() => {
        if (!isAuthenticated) {
            navigate('/login', { state: { from: '/profile' } });
        }
    }, [isAuthenticated, navigate]);

    if (!isAuthenticated || !user) {
        return (
            <div className="profile-container">
                <h2>Профиль</h2>
                <p>Пользователь не авторизован.</p>
                <button onClick={() => navigate('/login')} className="login-button">
                    Войти
                </button>
            </div>
        );
    }

    return (
        <div className="profile-container">
            <h2>Профиль</h2>
            <div className="user-info">
                <p><strong>Имя:</strong> {user.name}</p>
                <p><strong>Email:</strong> {user.email}</p>
            </div>
            <button onClick={() => navigate('/')} className="back-button">
                Вернуться на главную
            </button>
        </div>
    );
};

export default Profile;