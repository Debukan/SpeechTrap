import React from 'react';
import './Menu.css';

interface ChrProps {
    isOpen: boolean;
}

const Chr: React.FC<ChrProps> = ({ isOpen }) => {
    return (
        <>
            <h1>Комнаты</h1>
            <div>
              <button> ТИПО КОМНАТА </button>
            </div>

        </>
);
}

export default Chr;