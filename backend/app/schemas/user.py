from pydantic import BaseModel, EmailStr, Field, model_validator
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


class UserLogin(BaseModel):
    """Схема для авторизации пользователя."""

    email: EmailStr
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Схема для обновления профиля пользователя"""

    name: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    new_password: Optional[str] = Field(None, min_length=8, max_length=30)
    confirm_password: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def check_fields_not_empty(cls, values):
        """Проверяем, что хотя бы одно поле передано для обновления"""

        if not values or not any(v is not None for v in values.values()):
            raise ValueError("Должно быть передано хотя бы одно поле для обновления")
        return values

    @model_validator(mode="before")
    @classmethod
    def passwords_match(cls, values):
        """Проверяем, что новый пароль совпадает с подтверждением"""

        new_password = values.get("new_password")
        confirm_password = values.get("confirm_password")

        if new_password or confirm_password:
            if not new_password or not confirm_password:
                raise ValueError("Оба поля new_password и confirm_password должны быть заполнены")

            if new_password.strip() == "" or confirm_password.strip() == "":
                raise ValueError("Пароли не могут быть пустыми строками")

            if new_password != confirm_password:
                raise ValueError("Пароли не совпадают")

        return values