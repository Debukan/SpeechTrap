import React from 'react';
import { useNavigate } from 'react-router-dom';
import './RoomOwnerVision.css';

const ROV: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="menu-container">

            <h2>СЛОВО</h2>
            <h3>Запрещено использовать:...</h3>
            <label>Отправить сообщение
                <input type="text"/>
            </label>


        </div>
    );
};

export default ROV;