import json
from fastapi import FastAPI, Depends, WebSocket
from fastapi.websockets import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.word import WordWithAssociations
from app.db.deps import get_db
from app.core.config import settings
from contextlib import asynccontextmanager

# Импортируем роутеры
from app.api.endpoints import users, rooms, join_room, words # Добавили join_room
from app.api.endpoints.websocket_chat import WebSocketChatManager  # Добавляем импорт менеджера чата
# Инициализация FastAPI приложения
app = FastAPI()

chat_manager = WebSocketChatManager()

app.add_middleware(
    CORSMiddleware,
    #allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(users.router, prefix="/api/users", tags=['users'])  # Роутер для пользователей
app.include_router(rooms.router, prefix="/api/rooms", tags=['rooms'])  # Роутер для комнат
app.include_router(join_room.router, prefix="/api/join", tags=['join'])  # Роутер для присоединения к комнате
app.include_router(words.router, prefix="/api/words", tags=['words'])  # Роутер для работы со словами
#префикс пусть будет апи чтобы они в одном месте все были, более изолировано все равно внутри роутов будут свои пути

@app.websocket("/ws/{room_id}/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    room_id: str,
    session_id: str
):
    await chat_manager.connect(websocket, room_id, session_id)
    try:
        while True:
            await chat_manager.receive_message(websocket, room_id)
    except WebSocketDisconnect:
        await chat_manager.disconnect(websocket, room_id)


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
