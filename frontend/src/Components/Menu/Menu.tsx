import React from 'react';
import './Menu.css';

interface MenuProps {
    isOpen: boolean;
}

const Menu: React.FC<MenuProps> = ({ isOpen }) => {
    return (
        <>

            <button>Создать комнату</button>
            <button>Присоединиться к комнате</button>
        </>
    );
}

export default Menu;