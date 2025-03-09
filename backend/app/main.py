import json
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db, engine
from app.models.word import WordWithAssociations

# Импортируем роутеры
from app.api.endpoints import users, rooms, join_room  # Добавили join_room
from app.routes.word import router as word_router

# Функция для загрузки начальных данных (слов) в базу данных
async def load_data():
    """
    Загружает слова и ассоциации из файла words.json в базу данных.
    """
    with open("words.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    db = next(get_db())
    try:
        # Проверяем, есть ли уже данные в таблице
        if not db.query(WordWithAssociations).first():
            for category, words in data.items():
                for word, associations in words.items():
                    word_entry = WordWithAssociations(
                        category=category,
                        word=word,
                        associations=associations
                    )
                    db.add(word_entry)
            db.commit()
            print("Initial data loaded successfully")
        else:
            print("Data already exists in the database")
    finally:
        db.close()

# Инициализация FastAPI приложения
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """
    Выполняется при запуске приложения
    """
    await load_data()


# Подключаем роутеры
app.include_router(users.router, prefix="/users", tags=['users'])  # Роутер для пользователей
app.include_router(rooms.router, prefix="/rooms", tags=['rooms'])  # Роутер для комнат
app.include_router(join_room.router, prefix="/join", tags=['join'])  # Роутер для присоединения к комнате
app.include_router(word_router)  # Роутер для работы со словами

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