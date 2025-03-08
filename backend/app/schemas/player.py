from pydantic import BaseModel
from datetime import datetime
from app.models.player import PlayerRole
from typing import Optional

class PlayerBase(BaseModel):
    role: PlayerRole
    score: int = 0


class PlayerCreate(PlayerBase):
    user_id: int
    room_id: int


class PlayerResponse(PlayerBase):
    id: int
    user_id: int  # Добавлено
    room_id: int  # Добавлено
    joined_at: datetime
    correct_answers: int
    wrong_answers: int  # Добавлено
    success_rate: float

    class Config:
        orm_mode = True
