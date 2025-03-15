import json
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.word import WordWithAssociations
from app.db.deps import get_db
from app.core.config import settings
from contextlib import asynccontextmanager

# Импортируем роутеры
from app.api.endpoints import users, rooms, join_room  # Добавили join_room
from app.routes.word import router as word_router

# Инициализация FastAPI приложения
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    #allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(users.router, prefix="/users", tags=['users'])  # Роутер для пользователей
app.include_router(rooms.router, prefix="/rooms", tags=['rooms'])  # Роутер для комнат
app.include_router(join_room.router, prefix="/join", tags=['join'])  # Роутер для присоединения к комнате
app.include_router(word_router)  # Роутер для работы со словами

@app.get("/")
async def root():
    return {"message": "SpeechTrap API"}

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


@app.get("/check-data", tags=["debug"])
async def check_data():
    db = next(get_db())
    try:
        count = db.query(WordWithAssociations).count()
        return {"status": "успех", "количество_слов": count}
    finally:
        db.close()
