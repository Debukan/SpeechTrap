import React from 'react';
import './Menu.css';

interface ChrProps {
    isOpen: boolean;
}

const ChooseRoom: React.FC<ChrProps> = ({ isOpen }) => {
    return (
        <>
            <div className="menu-container">
                <label>Введите  id комнаты
                    <input type="text"/>
                </label>
                <button>
                    Войти по id комнаты
                </button>
                <h1>Комнаты</h1>
                <div>
                    <button> ТИПО КОМНАТА </button>
                </div>
            </div>
        </>
);
}

export default ChooseRoom;