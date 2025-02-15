from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
"""
Модуль конфигурации приложения.
Содержит настройки подключения к базе данных и другие параметры.
"""

class Settings(BaseSettings):
    """
    Класс настроек приложения.
    Загружает конфигурацию из переменных окружения.
    """
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def DATABASE_URL(self) -> str:
        """
        Формирует URL для подключения к PostgreSQL.
        
        Returns:
            str: URL подключения к базе данных
        """
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = str(Path(__file__).resolve().parents[2] / ".env")



@lru_cache()
def get_settings() -> Settings:
    """
    Создает и кеширует экземпляр настроек.
    
    Returns:
        Settings: Объект настроек приложения
    """
    return Settings()

settings = get_settings()