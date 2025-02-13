import React from 'react';
import Register from "./Components/Register";

function App() {
  const handleRegister = (userData: { name: string; email: string; password: string }) => {
    console.log('Данные регистрации:', userData);
  };

  return (
      <div className="App">
        <h1>SpeechTrap</h1> {}
        <Register onRegister={handleRegister} /> {}
      </div>
  );
}

export default App;