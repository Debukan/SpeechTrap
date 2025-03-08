from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.db.session import get_db
from app.models.room import Room
from app.models.user import User
from app.models.player import Player

router = APIRouter()

@router.post("/join-room/{room_code}/{user_id}")
def join_room_by_code(room_code: str, user_id: int, db: Session = Depends(get_db)):
    """
    Присоединение пользователя к комнате по коду.

    Параметры:
    - room_code: Код комнаты, к которой нужно присоединиться.
    - user_id: ID пользователя, который присоединяется.

    Возвращает:
    - Сообщение об успешном присоединении или ошибку.
    """
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

    return {"message": f"Пользователь {user.name} успешно присоединился к комнате {room.code}"}