import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Menu from './Components/Menu/Menu';
import Register from './Components/RegisterandProfile/Register';
import Login from './Components/RegisterandProfile/Login';
import Profile from './Components/RegisterandProfile/Profile';
import CreateRoom from './Components/CreateRoom/CreateRoom';
import JoinRoom from './Components/JoinRoom/JoinRoom';
import ProfileIcon from './Components/RegisterandProfile/ProfileIcon';
import Room from './Components/Room/Room';
import ROV from './Components/RoomOwnerVision/RoomOwnerVision';
import RPV from './Components/Room player vision/Room player vision';
import { AuthProvider } from './context/AuthContext';

function App() {
    const [userData, setUserData] = useState<{ name: string; email: string; password: string } | null>(null);

    const handleRegister = (userData: { name: string; email: string; password: string }) => {
        setUserData(userData);
    };

    const handleLogin = (token: string, userData: any) => {
        // Обработка успешного входа пользователя
        setUserData(userData);
    };

    return (
        <AuthProvider>
            <Router>
                <div className="App">
                    <h1>
                        <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>SpeechTrap</Link>
                    </h1>
                    <ProfileIcon />
                    <Routes>
                        <Route path="/" element={<Menu />} />
                        <Route path="/register" element={<Register onRegister={handleRegister} />} />
                        <Route path="/login" element={<Login onLogin={handleLogin} />} />
                        <Route path="/profile" element={<Profile userData={userData} />} />
                        <Route path="/createroom" element={<CreateRoom />} />
                        <Route path="/join-room" element={<JoinRoom />} />
                        <Route path="/room/:roomId" element={<Room />} />
                        <Route path="/rov/:roomId" element={<ROV />} />
                        <Route path="/rpv/:roomId" element={<RPV />} />
                        <Route path="*" element={<div className="not-found">404 - Страница не найдена</div>} />
                    </Routes>
                </div>
            </Router>
        </AuthProvider>
    );
}

export default App;