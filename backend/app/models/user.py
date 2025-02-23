from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import List, Optional
from app.models.player import Player

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    players: List[Player] = Relationship(back_populates="user")