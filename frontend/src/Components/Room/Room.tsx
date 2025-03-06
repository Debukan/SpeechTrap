import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';

interface Player {
    id: string;
    name: string;
}

const Room: React.FC = () => {
    const { roomId } = useParams<{ roomId: string }>(); //roomId из URL
    const [players, setPlayers] = useState<Player[]>([]);

    useEffect(() => {
        // Загрузка данных о комнате и игроках
        const fetchRoomData = async () => {
            try {
                // здесь заменим на запрос к api(щас это просто пример)
                const roomData = {
                    id: roomId,
                    players: [
                        { id: '1', name: 'Игрок 1' },
                        { id: '2', name: 'Игрок 2' },
                    ],
                };

                setPlayers(roomData.players);
            } catch (error) {
                console.error('Ошибка при загрузке данных:', error);
            }
        };

        fetchRoomData();
    }, [roomId]);

    const handleStartGame = () => {
        console.log('Игра началась!');
    };

    return (
        <div className="menu-container">
            <h2>Комната: {roomId}</h2>
            <div>
                <h3>Игроки в лобби:</h3>
                <ul>
                    {players.map((player) => (
                        <li key={player.id}>{player.name}</li>
                    ))}
                </ul>
            </div>
            <button onClick={handleStartGame}>Начать игру</button>
        </div>
    );
};

export default Room;