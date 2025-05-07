import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Register from './components/RegisterandProfile/Register';
import Login from './components/RegisterandProfile/Login';
import Profile from './components/RegisterandProfile/Profile';
import Menu from './components/Menu/Menu';
import CreateRoom from './components/CreateRoom/CreateRoom';
import JoinRoom from './components/JoinRoom/JoinRoom';
import Room from './components/Room/Room';
import GameBoard from './components/Game/GameBoard';
import ProfileIcon from './components/RegisterandProfile/ProfileIcon';
import { AuthProvider } from './context/AuthContext';
import { UserProvider } from './context/UserContext';

function App() {
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
              <Route path="/register" element={<Register />} />
              <Route path="/login" element={<Login />} />
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