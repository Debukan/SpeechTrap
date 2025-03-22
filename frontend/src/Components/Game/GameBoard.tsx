import React, { useState, useEffect } from "react";
import apiClient from "../api/apiClient";

interface GameState {
  currentWord: string;
  players: { id: string; username: string; score: number }[];
  round: number;
}

const GameBoard: React.FC = () => {
  const [gameState, setGameState] = useState<GameState | null>(null);

  useEffect(() => {
    const fetchGameState = async () => {
      try {
        const response = await apiClient.get("/api/game/state");
        setGameState(response.data);
      } catch (error) {
        console.error("Error fetching game state:", error);
      }
    };

    fetchGameState();
    const interval = setInterval(fetchGameState, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h2>Game Board</h2>
      {gameState ? (
        <div>
          <p><strong>Current Word:</strong> {gameState.currentWord}</p>
          <p><strong>Round:</strong> {gameState.round}</p>
          <h3>Players</h3>
          <ul>
            {gameState.players.map((player) => (
              <li key={player.id}>
                {player.username}: {player.score} points
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p>Loading game state...</p>
      )}
    </div>
  );
};

export default GameBoard;