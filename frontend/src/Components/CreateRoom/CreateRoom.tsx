import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import "./CreateRoom.css";

const CreateRoom = () => {
    const [roomName, setRoomName] = useState('');
    const [maxPlayers, setMaxPlayers] = useState(2);
    const [roundTime, setRoundTime] = useState(1);
    const [rounds, setRounds] = useState(3);
    const [difficulty, setDifficulty] = useState('basic');
    const navigate = useNavigate();

    const handleCreateRoom = () => {
        const roomData = {
            roomName,
            maxPlayers,
            roundTime,
            rounds,
            difficulty,
        };
        const roomId = '12345'; //это просто пример, по факту здесь будет от сервера
        navigate(`/room/${roomId}`);
    };

    return (
        <div className="create-room">
            <h1>Создание комнаты</h1>
            <label>
                Имя комнаты:
                <input
                    type="text"
                    value={roomName}
                    onChange={(e) => setRoomName(e.target.value)}
                />
            </label>
            <label>
                Количество игроков: {maxPlayers}
                <input
                    type="range"
                    className="slider"
                    value={maxPlayers}
                    min="2"
                    max="6"
                    step="1"
                    onChange={(e) => setMaxPlayers(Number(e.target.value))}
                />
            </label>
            <label>
                Таймер на раунд (минуты): {roundTime}
                <input
                    type="range"
                    className="slider"
                    value={roundTime}
                    min="1"
                    max="5"
                    step="1"
                    onChange={(e) => setRoundTime(Number(e.target.value))}
                />
            </label>
            <label>
                Количество раундов: {rounds}
                <input
                    type="range"
                    className="slider"
                    value={rounds}
                    min="1"
                    max="10"
                    step="1"
                    onChange={(e) => setRounds(Number(e.target.value))}
                />
            </label>
            <label>
                Сложность:
                <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                >
                    <option value="basic">Базовый</option>
                    <option value="medium">Средний</option>
                    <option value="hard">Сложный</option>
                </select>
            </label>
            <button onClick={handleCreateRoom}>Создать комнату</button>
        </div>
    );
};

export default CreateRoom;