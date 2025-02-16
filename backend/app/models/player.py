from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
from enum import Enum

class PlayerRole(str, Enum):
    """Роли игрока в игре"""
    EXPLAINING = "explaining"
    GUESSING = "guessing"
    WAITING = "waiting"

class Player(SQLModel, table=True):
    """
    Модель игрока в комнате.
    Связывает пользователя с игровой комнатой и хранит игровую статистику.
    """
    __tablename__ = "players"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    room_id: int = Field(foreign_key="rooms.id")

    # Игровая статистика
    score: int = Field(default=0)
    role: PlayerRole = Field(default=PlayerRole.WAITING)
    correct_answers: int = Field(default=0)
    wrong_answers: int = Field(default=0)
    joined_at: datetime = Field(default_factory=datetime.now)

    # Связи с другими моделями
    user: "User" = Relationship(back_populates="players")
    room: "Room" = Relationship(back_populates="players")


    def update_score(self, points: int) -> None:
        """Обновление очков игрока"""
        self.score += points

    def change_role(self, new_role: PlayerRole) -> None:
        """Изменение роли игрока"""
        self.role = new_role
    
    @property
    def success_rate(self) -> float:
        """Процент успешных ответов"""
        total = self.correct_answers + self.wrong_answers
        if total == 0:
            return 0.0
        return (self.correct_answers / total) * 100
