import React from 'react';
import { useNavigate } from 'react-router-dom';
import './ProfileIcon.css';

const ProfileIcon = () => {
    const navigate = useNavigate();

    const handleProfileClick = () => {
        navigate('/profile'); // Переход на страницу профиля
    };

    return (
        <div className="profile-icon" onClick={handleProfileClick}>
            <span>👤</span>
        </div>
    );
};

export default ProfileIcon;