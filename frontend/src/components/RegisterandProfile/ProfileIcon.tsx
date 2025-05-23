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
    <div className="flex items-center gap-3">
      {isAuthenticated ? (
        <>
          <div 
            className="profile-icon-button flex items-center justify-center bg-gradient-to-r from-blue-500 to-blue-700 cursor-pointer transition-all duration-300"
            onClick={handleProfileClick}
          >
            <span className="text-white">
              {user?.name?.charAt(0)?.toUpperCase() || 'У'}
            </span>
          </div>
          <button 
            onClick={handleLogout}
            className="logout-button bg-gradient-to-r from-red-500 to-red-700 text-white py-2 px-4 rounded-lg text-sm font-medium shadow-md hover:from-red-600 hover:to-red-800 transition-all duration-200 flex items-center justify-center"
          >
            Выйти
          </button>
        </>
      ) : (
        <button 
          onClick={() => navigate('/login')}
          className="login-button bg-gradient-to-r from-blue-500 to-blue-700 text-white py-2 px-4 rounded-lg text-sm font-medium shadow-md hover:from-blue-600 hover:to-blue-800 transition-all duration-200 flex items-center justify-center"
        >
          Войти
        </button>
      )}
    </div>
  );
};

export default ProfileIcon;