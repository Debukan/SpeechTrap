from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from datetime import datetime

from app.db.session import get_db
from app.models.room import Room, GameStatus
from app.schemas.room import RoomResponse

router = APIRouter()


@router.post("/rooms/", response_model=Room)
def create_room(room: Room, db: Session = Depends(get_db)):
    """Создание новой игровой комнаты.
    Args:
        room: Данные для создания комнаты.
        db: Сессия базы данных.
    Returns: Room: Созданная комната.
    """
    # Проверка уникальности кода комнаты
    existing_room = db.query(Room).filter(Room.code == room.code).first()
    if existing_room:
        raise HTTPException(status_code=400, detail="Комната с таким кодом уже существует")

    # Установка времени создания
    room.created_at = datetime.now()

    # Добавление комнаты в базу данных
    db.add(room)
    db.commit()
    db.refresh(room)

    return room


@router.get("/rooms/active", response_model=List[RoomResponse])
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
        )
        for room in rooms
    ]
