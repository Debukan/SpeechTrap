from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from datetime import datetime
from typing import Optional

from app.db.deps import get_db
from app.models.room import Room, GameStatus
from app.schemas.room import RoomCreate, RoomResponse
from app.schemas.player import PlayerResponse

router = APIRouter()


@router.post("/create", response_model=RoomResponse)
def create_room(room_data: RoomCreate, db: Session = Depends(get_db)):
    """
    Создание новой игровой комнаты с пользовательским кодом.

    Параметры:
    - room_data: Данные для создания комнаты, включая код.

    Возвращает:
    - Созданная комната.
    """
    # Проверка, что код не пустой
    if not room_data.code:
        raise HTTPException(status_code=400, detail="Код комнаты не может быть пустым")

    # Проверка уникальности кода комнаты
    existing_room = db.query(Room).filter(Room.code == room_data.code).first()
    if existing_room:
        raise HTTPException(status_code=400, detail="Комната с таким кодом уже существует")

    # Создание новой комнаты
    new_room = Room(
        code=room_data.code,  # Используем код, заданный пользователем
        status=GameStatus.WAITING,  # Статус по умолчанию
        max_players=room_data.max_players if room_data.max_players else 4,  # Максимум игроков
        current_round=0,
        rounds_total=room_data.rounds_total if hasattr(room_data, "rounds_total") else 10,
        time_per_round=room_data.time_per_round if hasattr(room_data, "time_per_round") else 60
    )

    # Добавление комнаты в базу данных
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    room_response = RoomResponse(
        id=new_room.id,
        code=new_room.code,
        status=new_room.status,
        max_players=new_room.max_players,
        current_round=new_room.current_round,
        created_at=new_room.created_at,
        player_count=0,
        current_word_id=new_room.current_word_id if hasattr(new_room, "current_word_id") else None,
        is_full=False,
        players=[]
    )

    return room_response


@router.get("/active", response_model=List[RoomResponse])
def get_active_rooms(db: Session = Depends(get_db)):
    """
    Получает список активных комнат

    """
    rooms = db.query(Room).filter(Room.status != GameStatus.FINISHED).all()

    return [
        RoomResponse(
            id=room.id,
            code=room.code,
            status=room.status,
            current_round=room.current_round,
            created_at=room.created_at,
            player_count=len(room.players) if hasattr(room, "players") else 0,
            current_word_id=room.current_word_id,
            is_full=room.is_full(),
            players=[PlayerResponse(id=player.id, name=player.name) for player in room.players]
        )
        for room in rooms
    ]
