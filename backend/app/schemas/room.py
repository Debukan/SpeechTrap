from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.models.room import GameStatus
from app.schemas.player import PlayerResponse


class RoomBase(BaseModel):
    name: str
    max_players: int = 8
    rounds_total: int = 10
    time_per_round = 60


class RoomCreate(RoomBase):
    pass

class RoomCreate(RoomBase):
    code: str  # Код комнаты, заданный пользователем
    status: GameStatus = GameStatus.WAITING  # Статус комнаты по умолчанию

class RoomResponse(RoomBase):
    id: int
    code: str
    status: GameStatus
    current_round: int
    created_at: datetime
    player_count: int
    current_word_id: Optional[int] = None  # Добавлено
    is_full: bool  # Добавлено
    players: List[PlayerResponse]  # Добавлено

    class Config:
        orm_mode = True
