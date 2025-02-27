import React, { useState, useEffect } from 'react';
import Menu from './Components/Menu/Menu';
import Register from "./Components/Register/Register";

function App() {
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    const handleRegister = (userData: { name: string; email: string; password: string }) => {
        console.log('Данные регистрации:', userData);
    };

    useEffect(() => {
        setIsMenuOpen(true);
    }, []);

    return (
        <div className="App">
            <h1>SpeechTrap</h1>
            <Menu isOpen={isMenuOpen} /> {}
            <Register onRegister={handleRegister} />
        </div>
    );
}

export default App;