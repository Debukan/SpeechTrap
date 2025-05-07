
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/button';
import { useAuth } from '../../context/AuthContext';

const Menu: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const handleCreateRoom = () => {
    if (isAuthenticated) {
      navigate('/createroom');
    } else {
      navigate('/login', { state: { from: '/createroom' } });
    }
  };

  const handleJoinRoom = () => {
    if (isAuthenticated) {
      navigate('/join-room');
    } else {
      navigate('/login', { state: { from: '/join-room' } });
    }
  };

  const handleLogin = () => {
    navigate('/login');
  };

  const handleRegister = () => {
    navigate('/register');
  };

  return (
    <div className="max-w-md mx-auto p-6 rounded-lg shadow-lg bg-gradient-to-br from-cyan-100 to-cyan-300">
      <h2 className="text-center text-2xl font-semibold mb-6 text-gray-800">Главное меню</h2>

      {isAuthenticated ? (
        <>
          <Button onClick={handleCreateRoom} className="w-full mb-4">
                        Создать комнату
          </Button>
          <Button onClick={handleJoinRoom} className="w-full">
                        Присоединиться к комнате
          </Button>
        </>
      ) : (
        <>
          <Button onClick={handleRegister} className="w-full mb-4">
                        Зарегистрироваться
          </Button>
          <Button onClick={handleLogin} className="w-full">
                        Войти
          </Button>

          <p className="mt-4 text-center text-gray-700">
                        Войдите или зарегистрируйтесь, чтобы создать или присоединиться к комнате.
          </p>
        </>
      )}
    </div>
  );
};

export default Menu;