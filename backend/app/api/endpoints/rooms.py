from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime
from typing import Optional
import asyncio
import time

from app.db.deps import get_db
from app.core.security import get_current_user
from app.models.room import Room, GameStatus
from app.schemas.room import RoomCreate, RoomResponse
from app.schemas.player import PlayerResponse
from app.models.player import Player
from app.models.user import User
from .ws import manager

router = APIRouter()

# Модель для чата
class ChatMessageRequest(BaseModel):
    message: str

@router.post("/create", response_model=RoomResponse)
async def create_room(
    room_data: RoomCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создание новой игровой комнаты с пользовательским кодом.

    Параметры:
    - room_data: Данные для создания комнаты, включая код.

    Возвращает:
    - Созданная комната.
    """
    # Проверка, находится ли пользователь уже в какой-либо активной комнате
    active_player = db.query(Player).join(Room).filter(
        Player.user_id == current_user.id,
        Room.status != GameStatus.FINISHED
    ).first()
    
    if active_player:
        room = db.query(Room).filter(Room.id == active_player.room_id).first()
        if room:
            raise HTTPException(
                status_code=400, 
                detail=f"Вы уже находитесь в активной комнате с кодом {room.code}. Покиньте существующую комнату перед созданием новой."
            )
    
    # Проверка, что код не пустой
    if not room_data.code:
        raise HTTPException(status_code=400, detail="Код комнаты не может быть пустым")

    # Проверка уникальности кода комнаты
    existing_room = db.query(Room).filter(Room.code == room_data.code).first()
    if existing_room:
        raise HTTPException(status_code=400, detail="Комната с таким кодом уже существует")

    # Создание новой комнаты
    new_room = Room(
        code=room_data.code,
        status=GameStatus.WAITING,
        max_players=room_data.max_players,
        current_round=0,
        rounds_total=room_data.rounds_total,
        time_per_round=room_data.time_per_round
    )

    # Добавление комнаты в базу данных
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    
    # Создаем нового игрока и делаем текущего пользователя первым игроком в комнате
    new_player = Player(user_id=current_user.id, room_id=new_room.id, role="waiting")
    db.add(new_player)
    db.commit()
    db.refresh(new_player)

    # Формируем список игроков для ответа
    players = [
        PlayerResponse(
            id=new_player.id,
            name=current_user.name
        )
    ]

    room_response = RoomResponse(
        id=new_room.id,
        code=new_room.code,
        status=new_room.status,
        max_players=new_room.max_players,
        rounds_total=new_room.rounds_total,
        time_per_round=new_room.time_per_round,
        current_round=new_room.current_round,
        created_at=new_room.created_at,
        player_count=1,
        current_word_id=new_room.current_word_id if hasattr(new_room, "current_word_id") else None,
        is_full=False,
        players=players
    )

    return room_response


@router.get("/active", response_model=List[RoomResponse])
async def get_active_rooms(db: Session = Depends(get_db)):
    """
    Получает список активных комнат
    """
    rooms = db.query(Room).filter(Room.status != GameStatus.FINISHED).all()

    return [
        RoomResponse(
            id=room.id,
            code=room.code,
            status=room.status,
            max_players=room.max_players,
            rounds_total=room.rounds_total,
            time_per_round=room.time_per_round,
            current_round=room.current_round,
            created_at=room.created_at,
            player_count=len(room.players) if hasattr(room, "players") else 0,
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
        for room in rooms
    ]


@router.get("/{room_code}", response_model=RoomResponse)
async def get_room_by_code(room_code: str, db: Session = Depends(get_db)):
    """
    Получение информации о комнате по коду.
    
    Параметры:
    - room_code: Код комнаты.
    
    Возвращает:
    - Информация о комнате и список игроков.
    """
    room = db.query(Room).filter(Room.code == room_code).first()
    
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    players_list = []
    if hasattr(room, "players") and room.players:
        for player in room.players:
            user = db.query(User).filter(User.id == player.user_id).first()
            if user:
                players_list.append(
                    PlayerResponse(
                        id=player.id,
                        name=user.name,
                        role=player.role,
                        score=player.score or 0,
                        score_total=player.score_total or 0
                    )
                )
    
    return RoomResponse(
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
        players=players_list
    )


@router.post("/join/{room_code}/{user_id}")
async def join_room_by_code(
    room_code: str, 
    user_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Присоединение пользователя к комнате по коду.

    Параметры:
    - room_code: Код комнаты, к которой нужно присоединиться.
    - user_id: ID пользователя, который присоединяется.

    Возвращает:
    - Сообщение об успешном присоединении или ошибку.
    """
    # Проверка, что текущий пользователь присоединяет себя или имеет права
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403, 
            detail="Нет прав для присоединения другого пользователя к комнате"
        )
    
    # Проверка существования комнаты
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    # Проверка существования пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Проверка, не присоединен ли пользователь уже к комнате
    existing_player = db.query(Player).filter(Player.user_id == user_id, Player.room_id == room.id).first()
    if existing_player:
        raise HTTPException(status_code=400, detail="Пользователь уже в комнате")

    # Создание нового игрока
    new_player = Player(user_id=user_id, room_id=room.id, role="waiting")
    db.add(new_player)
    db.commit()
    db.refresh(new_player)

    player_data = {"id": new_player.id, "name": user.name}
    
    async def broadcast_player_joined():
        await manager.broadcast(
            room_code, 
            {"type": "player_joined", "player": player_data}
        )
    
    background_tasks.add_task(broadcast_player_joined)

    return {"message": f"Пользователь {user.name} успешно присоединился к комнате {room.code}"}

@router.delete("/{room_code}")
async def delete_room(
    room_code: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удаление комнаты и всех связанных игроков"""
    # Проверка существования комнаты
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    # Проверка, что пользователь является создателем комнаты (первым игроком)
    if not room.players or len(room.players) == 0:
        raise HTTPException(status_code=400, detail="Невозможно определить создателя комнаты")
    
    first_player = room.players[0]
    if first_player.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Только создатель комнаты может её удалить")
    
    # Отправка уведомления всем клиентам о закрытии комнаты
    async def broadcast_room_closed():
        await manager.broadcast(
            room_code, 
            {"type": "room_closed", "message": "Комната была закрыта создателем"}
        )
    
    background_tasks.add_task(broadcast_room_closed)
    
    for player in room.players:
        db.delete(player)
    
    db.delete(room)
    db.commit()
    
    return {"message": "Комната успешно удалена"}


@router.post("/{room_code}/leave")
async def leave_room(
    room_code: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Позволяет пользователю выйти из лобби.
    """
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    # Находим игрока в комнате
    player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    
    if not player:
        raise HTTPException(
            status_code=404,
            detail="Вы не являетесь участником этой комнаты"
        )
    
    # Удаляем игрока из комнаты
    db.delete(player)
    db.commit()
    db.refresh(room)
    
    # Отправляем сообщение о выходе игрока
    async def broadcast_player_left():
        try:
            await manager.broadcast(
                room_code,
                {
                    "type": "player_left",
                    "player_id": player.id,
                    "message": f"Игрок {current_user.name} покинул лобби"
                }
            )
        except Exception as e:
            print(f"Error broadcasting player left: {e}")
    
    background_tasks.add_task(broadcast_player_left)

    if room_code in manager.active_connections and current_user.id in manager.active_connections[room_code]:
        ws = manager.active_connections[room_code][current_user.id]
        await ws.close(code=1000, reason="User left")
        manager.disconnect(room_code, user_id=current_user.id)

    # Если это был последний игрок, удаляем комнату
    if len(room.players) == 0:
        db.delete(room)
        db.commit()
    
    return {"success": True, "message": "Вы успешно покинули лобби"}


@router.post("/{room_code}/chat")
async def send_lobby_chat_message(
    room_code: str,
    message_data: ChatMessageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отправка сообщения в чат лобби.
    
    Параметры:
    - room_code: Код комнаты
    - message_data: Данные сообщения (текст)
    
    Возвращает:
    - Подтверждение отправки сообщения
    """
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    # Проверяем, что пользователь находится в комнате
    player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    
    if not player:
        raise HTTPException(
            status_code=403,
            detail="Вы не являетесь участником этой комнаты"
        )
    
    chat_message = {
        "type": "chat_message",
        "player_id": str(player.id),
        "player_name": current_user.name,
        "player_role": player.role,
        "message": message_data.message,
        "timestamp": time.time()
    }
    
    # Отправляем сообщение всем игрокам в комнате
    async def broadcast_chat_message():
        await manager.broadcast(room_code, chat_message)
    
    background_tasks.add_task(broadcast_chat_message)
    
    return {"success": True, "message": "Сообщение отправлено"}