import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Menu.css';

interface MenuProps {
    isOpen: boolean;
}

const Menu: React.FC<MenuProps> = ({ isOpen }) => {
    const navigate = useNavigate();

    return (
        <>
            <button onClick={() => navigate('/createroom')}>Создать комнату</button>
            <button>Присоединиться к комнате</button>
        </>
    );
}

export default Menu;
