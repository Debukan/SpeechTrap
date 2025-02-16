from pydantic import BaseModel
from datetime import datetime
from app.models.player import PlayerRole

class PlayerBase(BaseModel):
    role: PlayerRole
    score: int = 0

class PlayerCreate(PlayerBase):
    user_id: int
    room_id: int

class PlayerResponse(PlayerBase):
    id: int
    joined_at: datetime
    correct_answers: int
    success_rate: float

    class Config:
        orm_mode = True