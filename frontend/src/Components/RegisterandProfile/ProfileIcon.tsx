import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './ProfileIcon.css';

const ProfileIcon: React.FC = () => {
    const navigate = useNavigate();
    const { isAuthenticated, user, logout } = useAuth();

    const handleProfileClick = () => {
        if (isAuthenticated) {
            navigate('/profile');
        } else {
            navigate('/login');
        }
    };

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    return (
        <div className="profile-icon-container">
            {isAuthenticated ? (
                <div className="user-controls">
                    <span className="user-name">{user?.name || 'Пользователь'}</span>
                    <div className="profile-icon" onClick={handleProfileClick}>
                        <span>👤</span>
                    </div>
                    <button className="logout-button" onClick={handleLogout}>
                        Выйти
                    </button>
                </div>
            ) : (
                <div className="profile-icon" onClick={() => navigate('/login')}>
                    <span>👤</span>
                </div>
            )}
        </div>
    );
};

export default ProfileIcon;