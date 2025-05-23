from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from app.core.security import verify_password, get_password_hash
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

    def check_password(self, password: str) -> bool:
        """Метод для проверки пароля"""
        return verify_password(password, self.hashed_password)

    def set_password(self, password: str):
        """Метод для хеширования пароля"""
        self.hashed_password = get_password_hash(password)

    players: List[Player] = Relationship(back_populates="user")
