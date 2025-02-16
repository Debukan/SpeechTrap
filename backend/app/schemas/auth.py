from pydantic import BaseModel


class LogoutResponse(BaseModel):
    """Схема ответа при выходе из системы"""

    message: str
