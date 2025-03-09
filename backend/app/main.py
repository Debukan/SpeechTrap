import json

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.api.endpoints import users
from app.api.endpoints import rooms
from app.models.word import WordWithAssociations
from app.routes.word import router as word_router
from app.db.session import engine

def load_data():
    with open("words.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    with Session(engine) as session:
        for category, words in data.items():
            for word, associations in words.items():
                word_entry = WordWithAssociations(
                    category=category,
                    word=word,
                    associations=associations
                )
                session.add(word_entry)
        session.commit()

# Вызываем загрузку данных при старте приложения
load_data()

# Инициализация FastAPI приложения
app = FastAPI()

# TODO: раскоммитить когда появиться база данных пользователя
app.include_router(users.router, prefix="/users", tags=['users'])
app.include_router(rooms.router, prefix="/rooms", tags=['rooms'])
app.include_router(word_router)

@app.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    """
    Проверяет работоспособность API и подключение к базе данных.

    Args:
        db: Сессия базы данных
    Returns:
        dict: Статус работоспособности сервиса
    """
    try:
        result = db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database connected successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
