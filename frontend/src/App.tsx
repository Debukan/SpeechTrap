import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Menu from './Components/Menu/Menu';
import Register from "./Components/RegisterandProfile/Register";
import CreateRoom from "./Components/CreateRoom/CreateRoom";
import Room from "./Components/Room/Room";
import Profile from "./Components/RegisterandProfile/Profile";
import ProfileIcon from "./Components/RegisterandProfile/ProfileIcon";

function App() {
    const [userData, setUserData] = useState<{ name: string; email: string; password: string } | null>(null);

    const handleRegister = (userData: { name: string; email: string; password: string }) => {
        setUserData(userData);
    };

    return (
        <Router>
            <div className="App">
                <h1>
                    <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>SpeechTrap</Link>
                </h1>
                <ProfileIcon />
                <Routes>
                    <Route path="/" element={<Menu />} />
                    <Route path="/register" element={<Register onRegister={handleRegister} />} />
                    <Route path="/profile" element={<Profile userData={userData} />} />
                    <Route path="/createroom" element={<CreateRoom />} />
                    <Route path="/room/:roomId" element={<Room />} />
                </Routes>
            </div>
        </Router>
    );
}

export default App;