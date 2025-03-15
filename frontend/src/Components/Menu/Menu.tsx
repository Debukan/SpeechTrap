import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Menu.css';

const Menu: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="menu-container">
            <h2>Меню</h2>
            <nav className="menu">
                <ul>
                    <li>
                        <button onClick={() => navigate('/createroom')}>Создать комнату</button>
                    </li>
                    <li>
                        <button onClick={() => navigate('/register')}>Регистрация</button>
                    </li>
                </ul>
            </nav>
        </div>
    );
};

export default Menu;