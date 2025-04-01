import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Menu.css';
import { useAuth } from '../../context/AuthContext';

const Menu: React.FC = () => {
    const navigate = useNavigate();
    const { isAuthenticated } = useAuth();

    const handleCreateRoom = () => {
        if (isAuthenticated) {
            navigate('/createroom');
        } else {
            navigate('/login', { state: { from: '/createroom' } });
        }
    };

    const handleJoinRoom = () => {
        if (isAuthenticated) {
            navigate('/join-room');
        } else {
            navigate('/login', { state: { from: '/join-room' } });
        }
    };

    const handleLogin = () => {
        navigate('/login');
    };

    const handleRegister = () => {
        navigate('/register');
    };

    return (
        <div className="menu-container">
            <h2>Главное меню</h2>
            
            {isAuthenticated ? (
                <>
                    <button onClick={handleCreateRoom}>Создать комнату</button>
                    <button onClick={handleJoinRoom}>Присоединиться к комнате</button>
                </>
            ) : (
                <>
                    <button onClick={handleLogin}>Войти</button>
                    <button onClick={handleRegister}>Зарегистрироваться</button>
                    <p className="login-prompt">Войдите или зарегистрируйтесь, чтобы создать или присоединиться к комнате</p>
                </>
            )}
        </div>
    );
};

export default Menu;