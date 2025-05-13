import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/button';
import { useAuth } from '../../context/AuthContext';
import './Menu.css';

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

  const gameWords = [
    'Табу', 'Слово', 'Ассоциация', 'Описание', 'Загадка', 
    'Угадай', 'Синоним', 'Команда', 'Фраза', 'Общение',
    'Игра', 'Объяснение', 'Секрет', 'Запрет', 'Подсказка'
  ];

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-20 -right-20 w-64 h-64 bg-blue-200 rounded-full opacity-20 blur-3xl"></div>
        <div className="absolute top-1/3 -left-20 w-80 h-80 bg-purple-200 rounded-full opacity-20 blur-3xl"></div>
        <div className="absolute -bottom-20 right-1/3 w-72 h-72 bg-blue-200 rounded-full opacity-20 blur-3xl"></div>
        
        {gameWords.map((word, index) => (
          <div 
            key={index}
            className="floating-word absolute"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 20}s`,
              animationDuration: `${25 + Math.random() * 15}s`,
              transform: `rotate(${Math.random() * 30 - 15}deg)`,
              fontSize: `${1 + Math.random() * 0.8}rem`,
              opacity: 0.15
            }}
          >
            {word}
          </div>
        ))}
      </div>
      
      <div className="flex justify-center items-center">
        <div className="w-full max-w-5xl bg-white rounded-xl shadow-xl overflow-hidden relative z-10">
          <div className="absolute -top-10 -left-10 w-24 h-24 bg-purple-200 rounded-full opacity-50 speech-bubble-decoration"></div>
          <div className="absolute -bottom-10 -right-10 w-28 h-28 bg-blue-200 rounded-full opacity-50 speech-bubble-decoration"></div>
          
          <div className="flex flex-col md:flex-row">
            <div className="w-full md:w-3/5 p-8 bg-gradient-to-br from-white to-blue-50 relative">
              <div className="absolute inset-0 opacity-10 bg-repeat" style={{ 
                backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 63c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm57-13c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9-21c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM60 91c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM35 41c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM12 60c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z' fill='%232563eb' fill-opacity='0.2' fill-rule='evenodd'/%3E%3C/svg%3E\")"
              }}></div>
              
              <div className="text-center mb-6 relative">
                <div className="absolute -top-2 -left-2 text-5xl opacity-20">💬</div>
                <div className="absolute -bottom-2 -right-2 text-5xl opacity-20">🎮</div>
                <h2 className="text-4xl font-bold text-blue-800 mb-2">Главное меню</h2>
                <p className="text-blue-600 opacity-75 text-base">Словесная игра, где важно что говорить и чего не говорить</p>
              </div>
              
              {isAuthenticated ? (
                <div className="space-y-4">
                  <Button 
                    onClick={handleCreateRoom} 
                    className="menu-button w-full h-14 bg-gradient-to-r from-blue-600 to-blue-800 hover:from-blue-700 hover:to-blue-900 text-white text-lg font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
                  >
                    <div className="flex items-center justify-center">
                      <span className="mr-3 flex-shrink-0">🏠</span>
                      <span>Создать комнату</span>
                    </div>
                  </Button>
                  <Button 
                    onClick={handleJoinRoom} 
                    className="menu-button w-full h-14 bg-gradient-to-r from-purple-600 to-purple-800 hover:from-purple-700 hover:to-purple-900 text-white text-lg font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
                  >
                    <div className="flex items-center justify-center">
                      <span className="mr-3 flex-shrink-0">🚪</span>
                      <span>Присоединиться к комнате</span>
                    </div>
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <Button 
                    onClick={handleRegister} 
                    className="menu-button w-full h-14 bg-gradient-to-r from-blue-600 to-blue-800 hover:from-blue-700 hover:to-blue-900 text-white text-lg font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
                  >
                    <div className="flex items-center justify-center">
                      <span className="mr-3 flex-shrink-0">✍️</span>
                      <span>Зарегистрироваться</span>
                    </div>
                  </Button>
                  <Button 
                    onClick={handleLogin} 
                    className="menu-button w-full h-14 bg-gradient-to-r from-purple-600 to-purple-800 hover:from-purple-700 hover:to-purple-900 text-white text-lg font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
                  >
                    <div className="flex items-center justify-center">
                      <span className="mr-3 flex-shrink-0">🔑</span>
                      <span>Войти</span>
                    </div>
                  </Button>
                  
                  <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-100">
                    <p className="text-center text-blue-700 text-sm mb-2">
                      Войдите или зарегистрируйтесь, чтобы создать или присоединиться к комнате.
                    </p>
                  </div>
                </div>
              )}
            </div>
            
            <div className="w-full md:w-2/5 bg-gradient-to-br from-blue-50 to-purple-50 p-8 relative">
              <div className="absolute -top-6 -right-6 w-16 h-16 bg-blue-300 rounded-full opacity-30"></div>
              <div className="absolute top-1/4 right-1/4 w-12 h-12 bg-purple-300 rounded-full opacity-30"></div>
              <div className="absolute bottom-1/3 right-0 w-20 h-20 bg-blue-200 rounded-full opacity-20"></div>
              
              <div className="taboo-card mb-6 transform rotate-2 hover:rotate-0 transition-transform">
                <div className="taboo-card-header">
                  Пример карточки
                </div>
                <div className="taboo-card-word">
                  КОМПЬЮТЕР
                </div>
                <div className="taboo-card-forbidden">
                  <div className="taboo-card-forbidden-item">Клавиатура</div>
                  <div className="taboo-card-forbidden-item">Мышь</div>
                  <div className="taboo-card-forbidden-item">Экран</div>
                  <div className="taboo-card-forbidden-item">Интернет</div>
                  <div className="taboo-card-forbidden-item">Система</div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow-md p-4 mt-6">
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Как играть в SpeechTrap:</h3>
                <ul className="text-sm text-blue-700 space-y-2 list-disc pl-5">
                  <li>Объясните загаданное слово команде</li>
                  <li>Избегайте использования запрещенных слов</li>
                  <li>Зарабатывайте очки за каждое угаданное слово</li>
                  <li>Соревнуйтесь с друзьями в словесной ловкости</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Menu;