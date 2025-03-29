import json
import logging
from fastapi import FastAPI, Depends, WebSocket, Request
from fastapi.websockets import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.word import WordWithAssociations
from app.db.deps import get_db
from app.core.config import settings
from contextlib import asynccontextmanager
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# Импортируем роутеры
from app.api.endpoints import users, rooms, join_room, words
from app.api.endpoints.websocket_chat import WebSocketChatManager
from app.api.debug import router as debug_router

# Инициализация FastAPI приложения
app = FastAPI()

chat_manager = WebSocketChatManager()

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    try:
        body = await request.body()
        if body:
            logger.debug(f"Request body: {body.decode()}")
    except Exception as e:
        logger.error(f"Error reading request body: {e}")
    
    response = await call_next(request)
    
    return response

# Обработка исключений
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Точный список разрешенных источников
ALLOWED_ORIGINS = ["http://localhost:3000", "http://frontend:3000"]

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Authorization"],
    max_age=86400,
)

# Подключаем роутеры
app.include_router(users.router, prefix="/api/users", tags=['users'])  # Роутер для пользователей
app.include_router(rooms.router, prefix="/api/rooms", tags=['rooms'])  # Роутер для комнат
app.include_router(join_room.router, prefix="/api/join", tags=['join'])  # Роутер для присоединения к комнате
app.include_router(words.router, prefix="/api/words", tags=['words'])  # Роутер для работы со словами
app.include_router(debug_router, prefix="/api/debug", tags=['debug'])  # Роутер для отладки

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
        return {
            "status": "ok", 
            "message": "Service is running",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/check-data", tags=["debug"])
async def check_data():
    db = next(get_db())
    try:
        count = db.query(WordWithAssociations).count()
        return {"status": "успех", "количество_слов": count}
    finally:
        db.close()