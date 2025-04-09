from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends
from sqlalchemy.orm import Session
import json
import logging
from datetime import datetime
from app.db.deps import get_db
from app.models.room import Room
from app.models.user import User

logger = logging.getLogger(__name__)

# Создаем роутер для WebSocket
router = APIRouter()

# Менеджер подключений WebSocket
class ConnectionManager:
    def __init__(self):
        # Словарь для хранения активных подключений
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, room_code: str, user_id: int = None):
        # Принимаем подключение
        logger.info(f"Attempting to accept WebSocket connection for room {room_code}, user_id: {user_id}")
        await websocket.accept()
        logger.info(f"Connection accepted for room {room_code}")

        # Добавляем подключение в словарь
        if room_code not in self.active_connections:
            self.active_connections[room_code] = {}
        
        if user_id:
            self.active_connections[room_code][user_id] = websocket
            logger.info(f"User {user_id} connected to room {room_code}")
        else:
            self.active_connections[room_code][websocket] = websocket
            logger.info(f"Anonymous client connected to room {room_code}")

    def disconnect(self, room_code: str, user_id: int = None, websocket: WebSocket = None):
        # Удаляем подключение из словаря
        if room_code in self.active_connections:
            if user_id is not None and user_id in self.active_connections[room_code]:
                del self.active_connections[room_code][user_id]
                logger.info(f"User {user_id} disconnected from room {room_code}")
            elif websocket and websocket in self.active_connections[room_code]:
                del self.active_connections[room_code][websocket]
                logger.info(f"Anonymous client disconnected from room {room_code}")
            
            # Если комната пуста, удаляем её
            if not self.active_connections[room_code]:
                del self.active_connections[room_code]

    def serialize_datetime(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    async def broadcast(self, room_code: str, message: dict, exclude_user_id: int = None, exclude_websocket: WebSocket = None):
        # Рассылка сообщений всем участникам комнаты, кроме указанного пользователя
        if room_code in self.active_connections:
            clients_count = len(self.active_connections[room_code])
            logger.info(f"Broadcasting message to {clients_count} clients in room {room_code}: {message.get('type', 'unknown')}")
            
            success_count = 0
            for client_id, websocket in self.active_connections[room_code].items():
                if client_id != exclude_user_id and websocket != exclude_websocket:
                    try:
                        if isinstance(message, dict):
                            json_str = json.dumps(message, default=self.serialize_datetime)
                            await websocket.send_text(json_str)
                            success_count += 1
                        else:
                            await websocket.send_text(message)
                            success_count += 1
                    except Exception as e:
                        logger.error(f"Error sending message to client {client_id}: {e}")
            
            logger.info(f"Successfully sent message to {success_count} out of {clients_count} clients")

    async def send_personal_message(self, user_id: str, message: dict):
        """
        Отправляет личное сообщение конкретному пользователю
        
        Параметры:
        - user_id: ID пользователя, которому нужно отправить сообщение
        - message: Сообщение для отправки
        """
        # Найти все соединения данного пользователя
        user_id_int = int(user_id) if user_id.isdigit() else user_id
        
        for room_code in self.active_connections:
            for connection_id, websocket in self.active_connections[room_code].items():
                if connection_id == user_id_int:
                    try:
                        json_str = json.dumps(message, default=self.serialize_datetime)
                        await websocket.send_text(json_str)
                        logger.info(f"Personal message sent to user {user_id}")
                    except Exception as e:
                        logger.error(f"Error sending personal message to user {user_id}: {e}")

# Инициализация менеджера подключений
manager = ConnectionManager()

# WebSocket endpoint для подключения к комнате
@router.websocket("/ws/{room_code}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, user_id: int, db: Session = Depends(get_db)):
    """
    WebSocket-подключение для взаимодействия с игровой комнатой для авторизованного пользователя.

    Параметры:
    - room_code: Код комнаты, к которой подключается пользователь.
    - user_id: ID пользователя, который подключается.
    """
    logger.info(f"WebSocket request received for room {room_code}, user_id: {user_id}")
    logger.info(f"Request headers: {websocket.headers}")

    # Проверка существования комнаты
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        logger.warning(f"Room {room_code} not found")
        await websocket.close(code=1008)
        return

    # Проверка существования пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User {user_id} not found")
        await websocket.close(code=1008)
        return

    # Подключение пользователя к комнате
    await manager.connect(websocket, room_code, user_id)

    try:
        from app.schemas.room import RoomResponse
        from app.schemas.player import PlayerResponse
        
        room_data = RoomResponse(
            id=room.id,
            code=room.code,
            status=room.status,
            max_players=room.max_players,
            rounds_total=room.rounds_total,
            time_per_round=room.time_per_round,
            current_round=room.current_round,
            created_at=room.created_at,
            player_count=len(room.players) if hasattr(room, "players") and room.players else 0,
            current_word_id=room.current_word_id if hasattr(room, "current_word_id") else None,
            is_full=room.is_full(),
            players=[
                PlayerResponse(
                    id=player.id,
                    name=player.user.name if hasattr(player, "user") and player.user else f"Player {player.id}"
                )
                for player in room.players
            ] if hasattr(room, "players") and room.players else []
        )
        
        room_dict = room_data.dict()
        json_data = json.dumps({
            "type": "room_update",
            "room": room_dict
        }, default=manager.serialize_datetime)
        
        await websocket.send_text(json_data)
        
        # Отправляем запрос на обновление состояния игры для этого игрока
        from app.api.endpoints.game import send_game_state_update
        await send_game_state_update(room_code, db)
        
        # Ожидание сообщений от клиента
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received message from user {user_id} in room {room_code}: {data}")
            message = json.loads(data)

            # Обработка сообщения
            if message["type"] == "chat":
                # Рассылка сообщениея всем участникам комнаты
                await manager.broadcast(
                    room_code,
                    {"type": "chat", "user_id": user_id, "message": message["message"]},
                    exclude_user_id=user_id
                )
            elif message["type"] == "game_action":
                # Рассылка игрового действие всем участникам комнаты
                await manager.broadcast(
                    room_code,
                    {"type": "game_action", "user_id": user_id, "action": message["action"]},
                    exclude_user_id=user_id
                )

    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected from room {room_code}")
        # Обработка отключения пользователя
        manager.disconnect(room_code, user_id)
    except Exception as e:
        logger.exception(f"Error in websocket_endpoint for room {room_code}, user_id {user_id}: {str(e)}")
        try:
            await websocket.close(code=1011, reason=f"Internal error: {str(e)}")
        except:
            logger.exception("Failed to close WebSocket connection")