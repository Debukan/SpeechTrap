from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime
from enum import Enum


class GameStatus(str, Enum):
    """Статусы игровой комнаты"""
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"
    PAUSED = "paused"


class Room(SQLModel, table=True):
    """
    Модель игровой комнаты.
    Хранит информацию о текущей игре и её участниках.
    """
    __tablename__ = "rooms"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    code: str = Field(unique=True, index=True)
    status: GameStatus = Field(default=GameStatus.WAITING)
    max_players: int = Field(default=8)
    current_round: int = Field(default=0)
    rounds_total: int = Field(default=10)
    created_at: datetime = Field(default_factory=datetime.now)

    # Настройки игры
    time_per_round: int = Field(default=60)

    players: List['PLayer'] = Relationship(back_populates='room')
    words: List["Word"] = Relationship(back_populates="room")
    current_word_id: Optional[int] = Field(default=None, foreign_key="words.id")


    def is_full(self) -> bool:
        """Проверка, заполнена ли комната"""
        return len(self.players) >= self.max_players if hasattr(self, 'players') else False

    def can_start(self) -> bool:
        """Проверка, можно ли начать игру"""
        return (
            self.status == GameStatus.WAITING and
            hasattr(self, 'players') and 
            len(self.players) >= 2
        )