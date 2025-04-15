from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import datetime
from typing import List, Optional
from app.models.room import GameStatus
from app.schemas.player import PlayerResponse


class RoomBase(BaseModel):
    max_players: int = 8
    rounds_total: int = 10
    time_per_round: int = 60


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
    max_players: int
    created_at: datetime
    player_count: int
    current_word_id: Optional[int] = None
    is_full: bool
    players: List[PlayerResponse]
    
    # Cериализатор для datetime
    @field_serializer('created_at', when_used="json")
    def serialize_dt(self, dt: datetime):
        return dt.isoformat()

    model_config = ConfigDict(
        from_attributes=True,
    )
