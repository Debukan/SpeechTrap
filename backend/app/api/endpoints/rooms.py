from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from datetime import datetime

from app.db.session import get_db
from app.models.room import Room, GameStatus

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