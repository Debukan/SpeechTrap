from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.base import Base
import time
from sqlalchemy.exc import OperationalError

"""
Модуль настройки сессии базы данных.
Создает подключение к PostgreSQL и предоставляет функцию для получения сессии.
"""

# Создаем движок SQLAlchemy
engine = create_engine(settings.DATABASE_URL, connect_args={"options": "-c client_encoding=utf8"})

# Фабрика сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Генератор сессий базы данных.
    Обеспечивает корректное закрытие сессии после использования.

    Yields:
        Session: Сессия SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
