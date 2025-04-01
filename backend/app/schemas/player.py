from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models.player import PlayerRole
from typing import Optional

class PlayerBase(BaseModel):
    pass

class PlayerCreate(PlayerBase):
    user_id: int
    room_id: int
    role: PlayerRole = PlayerRole.WAITING

class PlayerResponse(BaseModel):
    id: int
    name: str
    
    user_id: Optional[int] = None
    room_id: Optional[int] = None
    role: Optional[str] = None
    score: int = 0
    joined_at: Optional[datetime] = None
    correct_answers: int = 0
    wrong_answers: int = 0
    success_rate: float = 0.0

    model_config = ConfigDict(
        from_attributes=True
    )

class PlayerDetailResponse(PlayerResponse):
    user_id: int
    room_id: int  
    role: str
    joined_at: datetime
    success_rate: float

    model_config = ConfigDict(
        from_attributes=True
    )
