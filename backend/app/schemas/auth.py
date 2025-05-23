from pydantic import BaseModel


class LogoutResponse(BaseModel):
    """Схема ответа при выходе из системы"""

    message: str


class Token(BaseModel):
    """Схема для ответа с токеном"""

    access_token: str
    token_type: str = "bearer"
