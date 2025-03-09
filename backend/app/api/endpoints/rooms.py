from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from datetime import datetime
from typing import Optional

from app.db.session import get_db
from app.models.room import Room, GameStatus
from app.schemas.room import RoomCreate, RoomResponse

router = APIRouter()

@router.post("/rooms/", response_model=RoomResponse)
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
        max_players=room_data.max_players if room_data.max_players else 4  # Максимум игроков
    )

    # Добавление комнаты в базу данных
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    return new_room