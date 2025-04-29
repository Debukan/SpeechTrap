import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Register from './Components/RegisterandProfile/Register';
import Login from './Components/RegisterandProfile/Login';
import Profile from './Components/RegisterandProfile/Profile';
import Menu from './Components/Menu/Menu';
import CreateRoom from './Components/CreateRoom/CreateRoom';
import JoinRoom from './Components/JoinRoom/JoinRoom';
import Room from './Components/Room/Room';
import GameBoard from './Components/Game/GameBoard';
import ProfileIcon from './Components/RegisterandProfile/ProfileIcon';
import { AuthProvider } from './context/AuthContext';
import { UserProvider } from './context/UserContext';

function App() {
    const handleRegister = (userData: { name: string; email: string; password: string }) => {
        console.log('Пользователь зарегистрирован:', userData);
    };

    const handleLogin = (token: string, userData: any) => {
        console.log('Пользователь вошел:', userData);
    };

    return (
        <AuthProvider>
            <UserProvider>
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
                            <Route path="/profile" element={<Profile />} />
                            <Route path="/createroom" element={<CreateRoom />} />
                            <Route path="/join-room" element={<JoinRoom />} />
                            <Route path="/room/:roomId" element={<Room />} />
                            <Route path="/game/:roomCode" element={<GameBoard />} />
                            <Route path="*" element={<div className="not-found">404 - Страница не найдена</div>} />
                        </Routes>
                    </div>
                </Router>
            </UserProvider>
        </AuthProvider>
    );
}

export default App;