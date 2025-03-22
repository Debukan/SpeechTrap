import React, { useState, useEffect } from "react";

interface TimerProps {
  initialTime: number;
  onTimeUp: () => void; // kogda timer dostignet 0
}

const GameTimer: React.FC<TimerProps> = ({ initialTime, onTimeUp }) => {
  const [timeLeft, setTimeLeft] = useState(initialTime);

  useEffect(() => {
    if (timeLeft <= 0) {
      onTimeUp();
      return;
    }

    const timerId = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
    return () => clearTimeout(timerId);
  }, [timeLeft, onTimeUp]);

  return <div>Time left: {timeLeft} seconds</div>;
};

export default GameTimer;