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
          <div className="App min-h-screen flex flex-col bg-gradient-to-br from-indigo-50 via-blue-50 to-white">
            <header className="flex items-center justify-between px-6 py-2 shadow-lg bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white relative overflow-hidden">
              <div className="absolute inset-0 opacity-10">
                <div className="absolute inset-0 bg-repeat" style={{ 
                  backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'20\' height=\'20\' viewBox=\'0 0 20 20\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'0.2\' fill-rule=\'evenodd\'%3E%3Ccircle cx=\'3\' cy=\'3\' r=\'3\'/%3E%3Ccircle cx=\'13\' cy=\'13\' r=\'3\'/%3E%3C/g%3E%3C/svg%3E")', 
                }}></div>
              </div>
              
              <div className="w-1/5"></div>
              
              <div className="flex-grow text-center z-10">
                <h1 className="text-2xl font-bold tracking-tight hover:text-blue-100 transition-colors duration-300">
                  <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }} className="flex items-center justify-center">
                    <span className="font-extrabold">Speech</span>
                    <span className="font-light">Trap</span>
                  </Link>
                </h1>
              </div>
              
              <div className="w-1/5 flex justify-end z-10">
                <ProfileIcon />
              </div>
              
              <div className="absolute -bottom-1 left-1/4 w-32 h-1 bg-blue-400 opacity-30 rounded-full blur-sm"></div>
              <div className="absolute -bottom-1 right-1/3 w-24 h-1 bg-purple-400 opacity-30 rounded-full blur-sm"></div>
            </header>
            
            <main className="flex-grow relative flex items-center justify-center">
              <div className="absolute inset-0 bg-repeat opacity-5" style={{ 
                backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%239C92AC\' fill-opacity=\'0.3\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")', 
              }}></div>
              
              <div className="relative z-10 w-full">
                <Routes>
                  <Route path="/" element={<Menu />} />
                  <Route path="/register" element={<Register />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/profile" element={<Profile />} />
                  <Route path="/createroom" element={<CreateRoom />} />
                  <Route path="/join-room" element={<JoinRoom />} />
                  <Route path="/room/:roomId" element={<Room />} />
                  <Route path="/game/:roomCode" element={<GameBoard />} />
                  <Route path="*" element={<div className="not-found p-4 text-center">404 - Страница не найдена</div>} />
                </Routes>
              </div>
            </main>
          </div>
        </Router>
      </UserProvider>
    </AuthProvider>
  );
}

export default App;