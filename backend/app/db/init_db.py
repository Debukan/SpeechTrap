import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import text
from app.db.base import Base
from app.db.session import engine
import time
from sqlalchemy.exc import OperationalError


def init_db():
    """
    Инициализация базы данных.
    Создает таблицы, если они еще не существуют.
    """
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            # Проверяем, существуют ли уже таблицы
            with engine.connect() as connection:
                result_users = connection.execute(
                    text(
                        """
                    SELECT EXISTS (
                        SELECT 1 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                    )
                """
                    )
                )
                result_words = connection.execute(
                    text(
                        """
                    SELECT EXISTS (
                        SELECT 1 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'words'
                    )
                """
                    )
                )
                users_exist = result_users.scalar()
                words_exist = result_words.scalar()
                if not (users_exist and words_exist):
                    Base.metadata.create_all(bind=engine)
                    print("Tables created successfully")
                else:
                    print("All required tables already exist")
                connection.commit()
            break
        except OperationalError as e:
            if attempt == max_attempts - 1:
                raise
            print(f"Waiting for db... Attempt {attempt + 1}/{max_attempts}: {e}")
            time.sleep(2)


if __name__ == "__main__":
    print("Starting database initialization...")
    init_db()
