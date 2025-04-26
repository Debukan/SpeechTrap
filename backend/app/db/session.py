from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

"""
Модуль настройки сессии базы данных.
Создает подключение к PostgreSQL и предоставляет функцию для получения сессии.
"""

# Создаем движок SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL, connect_args={"options": "-c client_encoding=utf8"}
)

# Фабрика сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
