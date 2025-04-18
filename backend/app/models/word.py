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
            self.success_rate = ((self.success_rate * (self.times_used - 1)) + 1) / self.times_used
        else:
            self.success_rate = (self.success_rate * (self.times_used - 1)) / self.times_used


"""
# запись в бд

import json
from sqlmodel import Session, create_engine
from models import WordWithAssociations

engine = create_engine("sqlite:///words.db")
SQLModel.metadata.create_all(engine)

with open("../words.json", "r", encoding="utf-8") as file:
    data = json.load(file)

with Session(engine) as session:
    for category, words in data.items():
        for item in words:
            word_entry = WordWithAssociations(
                category=category, 
                word=item["word"],
                associations=item["associations"]
            )
            session.add(word_entry)
    session.commit()

"""

"""
# запрос на извлечение данных из модели

import json
from sqlmodel import Session, create_engine

engine = create_engine("sqlite:///words.db")
SQLModel.metadata.create_all(engine)

with open("../words.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    
with Session(engine) as session:
    results = session.exec(WordWithAssociations.select()).all()
    for entry in results:
        print(f"{entry.category}: {entry.word} -> {', '.join(entry.associations)}")
"""
