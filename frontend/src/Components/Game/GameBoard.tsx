import React, { useState, useEffect, useContext } from "react";
import apiClient, { gameApi } from "../../api/apiClient";
import { useParams, useNavigate } from "react-router-dom";
import { UserContext } from "../../context/UserContext";
import "./GameBoard.css";

interface GameState {
  currentWord: string;
  players: { id: string; username: string; score: number }[];
  round: number;
  status: 'WAITING' | 'PLAYING' | 'FINISHED';
  timeLeft?: number;
  currentPlayer?: string;
  rounds_total: number;
}

const GameBoard: React.FC = () => {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [guess, setGuess] = useState<string>("");
  const { roomCode } = useParams<{ roomCode: string }>();
  const { user } = useContext(UserContext);
  const navigate = useNavigate();

  // Загрузка состояния игры
  useEffect(() => {
    const fetchGameState = async () => {
      if (!roomCode) return;
      
      try {
        setLoading(true);
        const data = await gameApi.getGameState(roomCode);
        setGameState(data);
        setError(null);
      } catch (error) {
        console.error("Error fetching game state:", error);
        setError("Не удалось загрузить состояние игры");
      } finally {
        setLoading(false);
      }
    };

    fetchGameState();
    const interval = setInterval(fetchGameState, 3000);

    return () => clearInterval(interval);
  }, [roomCode]);

  // Обработчик начала игры
  const handleStartGame = async () => {
    if (!roomCode) return;
    
    try {
      setLoading(true);
      await gameApi.startGame(roomCode);
    } catch (error) {
      console.error("Error starting the game:", error);
      setError("Не удалось начать игру");
    } finally {
      setLoading(false);
    }
  };

  // Обработчик завершения хода
  const handleEndTurn = async () => {
    if (!roomCode) return;
    
    try {
      setLoading(true);
      await gameApi.endTurn(roomCode);
    } catch (error) {
      console.error("Error ending turn:", error);
      setError("Не удалось завершить ход");
    } finally {
      setLoading(false);
    }
  };

  // Обработчик выхода из игры
  const handleLeaveGame = async () => {
    if (!roomCode) return;
    
    try {
      await gameApi.leaveGame(roomCode);
      navigate('/');
    } catch (error) {
      console.error("Error leaving game:", error);
      setError("Не удалось покинуть игру");
    }
  };

  // Проверка, является ли текущий пользователь активным игроком
  const isCurrentPlayer = () => {
    return gameState?.currentPlayer === user?.id;
  };

  // Обработчик отправки догадки
  const handleSubmitGuess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!roomCode || !guess.trim()) return;
    
    try {
      setLoading(true);
      const result = await gameApi.submitGuess(roomCode, guess);
      
      // Очищаем поле ввода после отправки
      setGuess("");
      
      if (result.correct) {
        alert("Правильно! Вы угадали слово.");
      }
    } catch (error) {
      console.error("Error submitting guess:", error);
      setError("Не удалось отправить догадку");
    } finally {
      setLoading(false);
    }
  };

  if (loading && !gameState) {
    return <div className="game-loading">Загрузка игры...</div>;
  }

  if (error) {
    return <div className="game-error">{error}</div>;
  }

  return (
    <div className="game-board">
      <h2>Игровая доска</h2>
      {gameState ? (
        <div className="game-content">
          {gameState.status === 'WAITING' ? (
            <div className="waiting-screen">
              <h3>Ожидание начала игры</h3>
              <button 
                className="start-game-btn" 
                onClick={handleStartGame}
              >
                Начать игру
              </button>
            </div>
          ) : (
            <>
              <div className="game-info">
                <p><strong>Текущее слово:</strong> {gameState.currentWord}</p>
                <p><strong>Раунд:</strong> {gameState.round} из {gameState.rounds_total || "?"}</p>
                {gameState.timeLeft !== undefined && (
                  <p><strong>Оставшееся время:</strong> {gameState.timeLeft} сек.</p>
                )}
              </div>
              
              {gameState.status === 'PLAYING' && (
                <div className="game-actions">
                  {isCurrentPlayer() ? (
                    <div className="player-controls">
                      <p>Ваш ход! Объясните слово другим игрокам.</p>
                      <button 
                        className="end-turn-btn" 
                        onClick={handleEndTurn}
                      >
                        Завершить ход
                      </button>
                    </div>
                  ) : (
                    <div className="guess-form">
                      <form onSubmit={handleSubmitGuess}>
                        <input
                          type="text"
                          value={guess}
                          onChange={(e) => setGuess(e.target.value)}
                          placeholder="Введите вашу догадку..."
                          disabled={loading}
                        />
                        <button 
                          type="submit" 
                          disabled={loading || !guess.trim()}
                        >
                          Отправить
                        </button>
                      </form>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          <div className="players-section">
            <h3>Игроки</h3>
            <ul className="players-list">
              {gameState.players.map((player) => (
                <li 
                  key={player.id} 
                  className={`player-item ${player.id === gameState.currentPlayer ? 'current-player' : ''}`}
                >
                  {player.username}: {player.score} очков
                  {player.id === user?.id && " (Вы)"}
                  {player.id === gameState.currentPlayer && " (Ходит)"}
                </li>
              ))}
            </ul>
          </div>

          <button 
            className="leave-game-btn" 
            onClick={handleLeaveGame}
          >
            Покинуть игру
          </button>
        </div>
      ) : (
        <p>Загрузка состояния игры...</p>
      )}
    </div>
  );
};

export default GameBoard;