import React, { useState, useRef, useEffect } from 'react';
import axios from '../../utils/axios-config';
import { ChatMessage } from '../../types/chat';
import './ChatBox.css';

interface ChatBoxProps {
  roomCode: string;
  isExplaining: boolean;
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
}

const ChatBox: React.FC<ChatBoxProps> = ({ roomCode, isExplaining, messages, onSendMessage }) => {
  const [newMessage, setNewMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Прокрутка чата при новых сообщениях
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
        <h3>Чат игры</h3>
        {isExplaining && (
          <div className="explaining-indicator">Вы объясняете слово</div>
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
        <input
          type="text"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          placeholder={isExplaining ? "Объясните слово другим игрокам..." : "Введите сообщение..."}
          disabled={isSending}
        />
        <button 
          type="submit" 
          disabled={isSending || !newMessage.trim()}
          className={isExplaining ? "explaining-button" : ""}
        >
          Отправить
        </button>
      </form>
    </div>
  );
};

export default ChatBox;