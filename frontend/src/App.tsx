import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import Menu from './Components/Menu/Menu';
import Register from "./Components/Register/Register";
import CreateRoom from "./Components/CreateRoom/CreateRoom";
import Room from "./Components/Room/Room";

function App() {
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    const handleRegister = (userData: { name: string; email: string; password: string }) => {
        console.log('Данные регистрации:', userData);
    };

    useEffect(() => {
        setIsMenuOpen(true);
    }, []);

    return (
        <Router>
            <div className="App">
                <h1>SpeechTrap</h1>
                <Menu isOpen={isMenuOpen} />
                <Register onRegister={handleRegister} />
                <Routes>
                    <Route path="/createroom" element={<CreateRoom />} /> {/* Маршрут для создания комнаты */}
                    <Route path="/room/:roomId" element={<Room />} /> {/* Маршрут для комнаты с динамическим roomId */}
                </Routes>
            </div>
        </Router>
    );
}

export default App;