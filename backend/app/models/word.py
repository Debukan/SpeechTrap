from enum import Enum

from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, JSON
from app.models.base import Base

from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional, Literal
from datetime import datetime
from sqlalchemy import Column, JSON
from app.models.base import Base


class DifficultyEnum(str, Enum):
    basic = "basic"
    medium = "medium"
    hard = "hard"


class WordWithAssociations(SQLModel, table=True):
    __tablename__ = "words"

    id: Optional[int] = Field(default=None, primary_key=True)
    word: str = Field(index=True)
    category: str = Field(index=True)
    associations: List[str] = Field(sa_column=Column(JSON), default=[])

    difficulty: DifficultyEnum = Field(index=True)

    # Статистика
    is_active: bool = Field(default=True)
    times_used: int = Field(default=0)
    success_rate: float = Field(default=0.0)

    def update_stats(self, success: bool) -> None:
        """Обновление статистики использования слова"""
        self.times_used += 1
        if success:
            self.success_rate = (
                (self.success_rate * (self.times_used - 1)) + 1
            ) / self.times_used
        else:
            self.success_rate = (self.success_rate * (self.times_used - 1)) / self.times_used
