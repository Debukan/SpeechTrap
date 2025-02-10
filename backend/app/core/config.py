from pydantic_settings import BaseSettings
from functools import lru_cache

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

    @property
    def DATABASE_URL(self) -> str:
        """
        Формирует URL для подключения к PostgreSQL.
        
        Returns:
            str: URL подключения к базе данных
        """
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = '../../.env'


@lru_cache()
def get_settings() -> Settings:
    """
    Создает и кеширует экземпляр настроек.
    
    Returns:
        Settings: Объект настроек приложения
    """
    return Settings()

settings = get_settings()