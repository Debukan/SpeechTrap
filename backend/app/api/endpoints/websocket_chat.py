# websocket_chat.py
import json
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import WebSocket, status
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, ForeignKey, DateTime
from app.db.deps import get_db
from app.db.base import Base
from app.models.room import Room
from app.models.player import Player
from app.models.user import User


# Модель для хранения сообщений (создается только в этом файле)
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True)  # UUID или timestamp
    room_id = Column(String, ForeignKey("rooms.id"))  # Связь с комнатой
    user_id = Column(String, ForeignKey("users.id"))  # Связь с пользователем
    text = Column(String)  # Текст сообщения
    created_at = Column(DateTime, default=datetime.utcnow)  # Время отправки


class WebSocketChatManager:
    def __init__(self):
        # Словарь активных подключений: {room_id: set(websocket1, websocket2)}
        self.active_connections: Dict[str, Set[WebSocket]] = {}

        # Сессия БД из вашего существующего get_db()
        self.db: Session = next(get_db())

    async def connect(self, websocket: WebSocket, room_id: str, session_id: str):
        """Основной метод подключения к чату комнаты"""
        await websocket.accept()

        # 1. Аутентификация через session_id
        user = await self._authenticate_user(websocket, session_id)
        if not user:
            return  # Ошибка уже обработана в _authenticate_user

        # 2. Проверка существования комнаты
        room = self.db.query(Room).filter(Room.id == room_id).first()
        if not room:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Room not found"
            )
            return

        # 3. Добавление в активные подключения комнаты
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()

        self.active_connections[room_id].add(websocket)

        # Сохраняем пользователя в объекте websocket для быстрого доступа
        websocket.scope["user"] = user

        # 4. Отправляем новому пользователю историю чата
        await self._send_chat_history(websocket, room_id)

        # 5. Уведомляем других участников о новом подключении
        await self._broadcast(room_id, {
            "type": "system",
            "message": f"{user.username} присоединился к чату",
            "timestamp": datetime.utcnow().isoformat()
        }, exclude=websocket)

    async def disconnect(self, websocket: WebSocket, room_id: str):
        """Обработка отключения пользователя"""
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            user = self._get_user_by_websocket(websocket)

            if user:
                await self._broadcast(room_id, {
                    "type": "system",
                    "message": f"{user.username} покинул чат",
                    "timestamp": datetime.utcnow().isoformat()
                })

    async def receive_message(self, websocket: WebSocket, room_id: str):
        """Прием и обработка сообщений от клиента"""
        user = self._get_user_by_websocket(websocket)
        if not user:
            return

        while True:
            # Ожидаем новое сообщение
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # 1. Сохраняем сообщение в БД
            message = ChatMessage(
                id=str(datetime.utcnow().timestamp()),  # Простой ID на основе времени
                room_id=room_id,
                user_id=user.id,
                text=message_data["text"]
            )
            self.db.add(message)
            self.db.commit()

            # 2. Рассылаем сообщение всем в комнате
            await self._broadcast(room_id, {
                "type": "chat",
                "user_id": user.id,
                "username": user.username,
                "text": message_data["text"],
                "timestamp": datetime.utcnow().isoformat()
            })

    async def _send_chat_history(self, websocket: WebSocket, room_id: str):
        """Отправка последних 50 сообщений из истории чата"""
        messages = self.db.query(ChatMessage, User.username) \
            .join(User, ChatMessage.user_id == User.id) \
            .filter(ChatMessage.room_id == room_id) \
            .order_by(ChatMessage.created_at.desc()) \
            .limit(50) \
            .all()

        # Отправляем в обратном порядке (от старых к новым)
        for msg, username in reversed(messages):
            await websocket.send_text(json.dumps({
                "type": "chat",
                "user_id": msg.user_id,
                "username": username,
                "text": msg.text,
                "timestamp": msg.created_at.isoformat(),
                "is_history": True  # Флаг для клиента
            }))

    async def _broadcast(self, room_id: str, message: dict, exclude: Optional[WebSocket] = None):
        """Рассылка сообщения всем участникам комнаты"""
        if room_id not in self.active_connections:
            return

        for connection in self.active_connections[room_id]:
            if connection != exclude and connection.client_state == "connected":
                await connection.send_text(json.dumps(message))

    async def _authenticate_user(self, websocket: WebSocket, session_id: str) -> Optional[User]:
        """Аутентификация через вашу систему сессий"""
        try:
            # 1. Ищем игрока по session_id (из вашей модели Player)
            player = self.db.query(Player).filter(Player.session_id == session_id).first()
            if not player:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Сессия не найдена"
                )
                return None

            # 2. Получаем связанного пользователя
            user = self.db.query(User).filter(User.id == player.user_id).first()
            if not user:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Пользователь не найден"
                )
                return None

            return user

        except Exception as e:
            await websocket.close(
                code=status.WS_1011_INTERNAL_ERROR,
                reason=f"Ошибка аутентификации: {str(e)}"
            )
            return None

    def _get_user_by_websocket(self, websocket: WebSocket) -> Optional[User]:
        return websocket.scope.get("user")
