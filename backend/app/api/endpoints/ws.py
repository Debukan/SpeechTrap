from fastapi import WebSocket, WebSocketDisconnect
from fastapi import APIRouter
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.room import Room
from app.models.user import User

# Создаем роутер для WebSocket
router = APIRouter()

# Менеджер подключений WebSocket
class ConnectionManager:
    def __init__(self):
        # Словарь для хранения активных подключений
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, room_code: str, user_id: int):
        # Принимаем подключение
        await websocket.accept()

        # Добавляем подключение в словарь
        if room_code not in self.active_connections:
            self.active_connections[room_code] = {}
        self.active_connections[room_code][user_id] = websocket
        print(f"User {user_id} connected to room {room_code}")

    def disconnect(self, room_code: str, user_id: int):
        # Удаляем подключение из словаря
        if room_code in self.active_connections and user_id in self.active_connections[room_code]:
            del self.active_connections[room_code][user_id]
            print(f"User {user_id} disconnected from room {room_code}")
            if not self.active_connections[room_code]:
                del self.active_connections[room_code]

    async def broadcast(self, room_code: str, message: dict, exclude_user_id: int = None):
        # Рассылаем сообщение всем участникам комнаты, кроме указанного пользователя
        if room_code in self.active_connections:
            for user_id, websocket in self.active_connections[room_code].items():
                if user_id != exclude_user_id:
                    await websocket.send_json(message)

# Инициализация менеджера подключений
manager = ConnectionManager()

# WebSocket endpoint для подключения к комнате
@router.websocket("/ws/{room_code}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, user_id: int, db: Session = Depends(get_db)):
    """
    WebSocket-подключение для взаимодействия с игровой комнатой.

    Параметры:
    - room_code: Код комнаты, к которой подключается пользователь.
    - user_id: ID пользователя, который подключается.
    """
    # Проверка существования комнаты
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        await websocket.close(code=1008)  # Закрываем соединение, если комнаты нет
        return

    # Проверка существования пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        await websocket.close(code=1008)  # Закрываем соединение, если пользователя нет
        return

    # Подключение пользователя к комнате
    await manager.connect(websocket, room_code, user_id)

    try:
        while True:
            # Ожидание сообщений от клиента
            data = await websocket.receive_text()
            message = json.loads(data)

            # Обработка сообщения
            if message["type"] == "chat":
                # Рассылаем сообщение всем участникам комнаты
                await manager.broadcast(
                    room_code,
                    {"type": "chat", "user_id": user_id, "message": message["message"]},
                    exclude_user_id=user_id
                )
            elif message["type"] == "game_action":
                # Рассылаем игровое действие всем участникам комнаты
                await manager.broadcast(
                    room_code,
                    {"type": "game_action", "user_id": user_id, "action": message["action"]},
                    exclude_user_id=user_id
                )

    except WebSocketDisconnect:
        # Обработка отключения пользователя
        manager.disconnect(room_code, user_id)
        await manager.broadcast(
            room_code,
            {"type": "user_left", "user_id": user_id}
        )