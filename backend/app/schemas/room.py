from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.models.room import GameStatus

class RoomBase(BaseModel):
    name: str
    max_players: int = 8
    rounds_total: int = 10
    time_per_round = 60


class RoomCreate(RoomBase):
    pass


class RoomResponse(RoomBase):
    id: int
    code: str
    status: GameStatus
    current_round: int
    created_at: datetime
    player_count: int

    class Config:
        orm_mode = True