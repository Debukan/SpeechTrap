import random
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, ORJSONResponse
from sqlalchemy.orm import Session
from app.db.deps import get_db  # Исправленный импорт
from app.models.word import WordWithAssociations  # Импорт модели

app = FastAPI()
router = APIRouter()

# Получение случайного слова по категории
@router.get("/word/{category}")
def get_word_by_category(category: str, db: Session = Depends(get_db)):
    words = db.query(WordWithAssociations).filter(
        WordWithAssociations.category == category,
        WordWithAssociations.is_active == True
    ).all()
    if not words:
        return JSONResponse(
            content=jsonable_encoder({"detail": "Категория не найдена или нет активных слов"}),
            status_code=404,
            media_type="application/json; charset=utf-8"
        )

    word = random.choice(words)
    print(f"DEBUG: {word.word} -> {word.associations}")
    return ORJSONResponse(
        content={"word": word.word, "associations": word.associations}
    )

# Получение случайного слова из случайной категории
@router.get("/random-word")
def get_random_word(db: Session = Depends(get_db)):  # Исправленный вызов Depends
    words = db.query(WordWithAssociations).filter(WordWithAssociations.is_active == True).all()
    if not words:
        return JSONResponse(
            content={"detail": "Слов нет в базе"},
            status_code=404,
            media_type="application/json; charset=utf-8"
        )

    word = random.choice(words)
    return ORJSONResponse(
        content={"word": word.word, "associations": word.associations}
    )

# Обновление статистики слова
@router.post("/word/{word_id}/update-stats")
def update_word_stats(word_id: int, success: bool, db: Session = Depends(get_db)):  # Исправленный вызов Depends
    word = db.query(WordWithAssociations).filter(WordWithAssociations.id == word_id).first()
    if not word:
        return JSONResponse(
            content={"detail": "Слово не найдено"},
            status_code=404,
            media_type="application/json; charset=utf-8"
        )

    word.update_stats(success)
    db.commit()
    return ORJSONResponse(
        content={"word": word.word, "associations": word.associations}
    )

# Добавление нового слова
@router.post("/word/")
def add_word(word: str, category: str, associations: list[str], db: Session = Depends(get_db)):  # Исправленный вызов Depends
    new_word = WordWithAssociations(word=word, category=category, associations=associations)
    db.add(new_word)
    db.commit()
    db.refresh(new_word)
    return JSONResponse(
        content={"message": "Слово добавлено", "id": new_word.id},
        media_type="application/json; charset=utf-8"
    )

# Подключение роутера к FastAPI
app.include_router(router)
