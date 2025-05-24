import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../../types/chat';
import './ChatBox.css';

interface ChatBoxProps {
  roomCode: string;
  isExplaining: boolean;
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
}

const ChatBox: React.FC<ChatBoxProps> = ({ isExplaining, messages, onSendMessage }) => {
  const [newMessage, setNewMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // // Прокрутка чата при новых сообщениях`
  // useEffect(() => {
  //   messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  // }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newMessage.trim() || isSending) return;
    
    setIsSending(true);
    onSendMessage(newMessage);
    setNewMessage('');
    setIsSending(false);
  };

  // Форматирование времени
  const formatTime = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="chat-box">
      <div className="chat-header">
        <div className="flex items-center">
          <span className="mr-2">💬</span>
          <h3>Чат</h3>
        </div>
        {isExplaining && (
          <div className="explaining-indicator">
            <span className="mr-1">✨</span>
            Вы объясняете слово
          </div>
        )}
      </div>
      
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-chat">Сообщений пока нет. Начните общение!</div>
        ) : (
          messages.map((msg, index) => (
            <div 
              key={index} 
              className={`chat-message ${msg.is_explaining ? 'explaining-message' : ''}`}
            >
              <div className="message-header">
                <div className="message-info">
                  <span className="player-name">{msg.player_name}</span>
                  {msg.player_role === 'EXPLAINING' && (
                    <span className="role-badge">ОБЪЯСНЯЕТ</span>
                  )}
                </div>
                <span className="timestamp">{formatTime(msg.timestamp)}</span>
              </div>
              <div className="message-content">{msg.message}</div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <form className="chat-input" onSubmit={handleSubmit}>
        <div className="relative w-full flex items-center">
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder={isExplaining ? 'Объясните слово другим игрокам...' : 'Введите сообщение...'}
            disabled={isSending}
            className="w-full"
          />
          <button 
            type="submit" 
            title="Отправить"
            disabled={isSending || !newMessage.trim()}
            className={`send-button ${isExplaining ? 'explaining-button' : ''}`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
              <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatBox;