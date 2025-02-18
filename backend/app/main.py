from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.api.endpoints import users
from app.api.endpoints import rooms

# Инициализация FastAPI приложения
app = FastAPI()

# TODO: раскоммитить когда появиться база данных пользователя
# app.include_router(users.router, prefix="/api/users", tags=['users'])
# app.include_router(rooms.router, prefix="/api/rooms", tags=['rooms'])

@app.get('/health')
def health_checlk(db: Session = Depends(get_db)) -> dict:
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
