from pydantic import BaseModel
from typing import List


class WordBase(BaseModel):
    word: str
    category: str
    associations: List[str]


class WordCreate(WordBase):
    room_id: int


class WordResponse(WordBase):
    id: int
    is_active: bool
    times_used: int
    success_rate: float

    class Config:
        orm_mode = True
