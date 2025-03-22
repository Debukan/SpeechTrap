import React, { useState, useEffect } from "react";
import apiClient from "../api/apiClient";

interface Player {
  id: string;
  username: string;
  score: number;
}

const Scoreboard: React.FC = () => {
  const [players, setPlayers] = useState<Player[]>([]);

  useEffect(() => {
    const fetchScores = async () => {
      try {
        const response = await apiClient.get("/api/players/scores");
        setPlayers(response.data);
      } catch (error) {
        console.error("Error fetching scores:", error);
      }
    };

    fetchScores();
    const interval = setInterval(fetchScores, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h2>Scoreboard</h2>
      <ul>
        {players.map((player) => (
          <li key={player.id}>
            {player.username}: {player.score} points
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Scoreboard;