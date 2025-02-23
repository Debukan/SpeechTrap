from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    """Базовая схема пользователя"""

    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """Схема для создания пользователя"""

    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    """Схема для ответа"""

    id: int
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
