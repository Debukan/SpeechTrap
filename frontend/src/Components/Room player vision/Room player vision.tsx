import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Room player vision.css.css';

const RPV: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="menu-container">


            <label>Попытайся отгдать слово за это тебе дадут баллы
                <input type="text"/>
            </label>


        </div>
    );
};

export default RPV;