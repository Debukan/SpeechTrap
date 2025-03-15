import React from 'react';
import './Profile.css';

interface ProfileProps {
    userData: { name: string; email: string; password: string } | null;
}

const Profile: React.FC<ProfileProps> = ({ userData }) => {
    return (
        <div className="profile-container">
            <h2>Профиль</h2>
            {userData ? (
                <div className="user-info">
                    <p><strong>Имя:</strong> {userData.name}</p>
                    <p><strong>Email:</strong> {userData.email}</p>
                    <p><strong>Пароль:</strong> {userData.password}</p>
                </div>
            ) : (
                <p>Пользователь не авторизован.</p>
            )}
        </div>
    );
};

export default Profile;