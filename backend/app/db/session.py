from sqlalchemy import create_engine
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

# Создание таблиц
max_attempts = 10
for attempt in range(max_attempts):
    try:
        Base.metadata.create_all(bind=engine)
        break
    except OperationalError as e:
        if attempt == max_attempts - 1:
            raise
        print(f"Waiting for db... Attempt {attempt + 1}/{max_attempts}: {e}")
        time.sleep(2)

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
