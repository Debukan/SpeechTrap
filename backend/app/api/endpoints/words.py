import random
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel  # Импортируем BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError
from sqlalchemy import select
from app.db.deps import get_db
from app.models.word import WordWithAssociations, DifficultyEnum
from typing import Literal

router = APIRouter()


# Получение случайного слова из случайной категории
@router.get("/random-word")
def get_random_word(difficulty: DifficultyEnum, db: Session = Depends(get_db)):
    try:
        words = db.scalars(
            select(WordWithAssociations).where(
                WordWithAssociations.is_active == True,
                WordWithAssociations.difficulty == difficulty,
            )
        ).all()
    except ProgrammingError:
        raise HTTPException(status_code=404, detail="Нет слов подходящей сложности")

    if not words:
        raise HTTPException(status_code=404, detail="Нет слов подходящей сложности")

    word = random.choice(words)

    return {
        "id": word.id,
        "category": word.category,
        "word": word.word,
        "associations": word.associations,
        "difficulty": difficulty,
    }
    # TODO: non-repeating words


# Обновление статистики слова
@router.post("/{word_id}/update-stats")
def update_word_stats(word_id: int, success: bool, db: Session = Depends(get_db)):
    try:
        word = db.scalar(
            select(WordWithAssociations).where(WordWithAssociations.id == word_id)
        )
    except ProgrammingError:
        raise HTTPException(status_code=404, detail="Слово не найдено")
    if not word:
        raise HTTPException(status_code=404, detail="Слово не найдено")

    word.update_stats(success)
    db.commit()
    return {
        "message": "Статистика обновлена",
        "word_id": word.id,
        "success_rate": word.success_rate,
    }


# Модель для данных при создании слова
class WordCreate(BaseModel):
    word: str
    category: str
    difficulty: DifficultyEnum
    associations: list[str]


# Добавление нового слова
@router.post("/")
def add_word(
    word_data: WordCreate,
    db: Session = Depends(get_db),
):
    new_word = WordWithAssociations(
        word=word_data.word,
        category=word_data.category,
        difficulty=word_data.difficulty,
        associations=word_data.associations,
    )
    try:
        db.add(new_word)
        db.commit()
        db.refresh(new_word)
    except ProgrammingError:
        raise HTTPException(
            status_code=500, detail="Ошибка базы данных: таблица 'words' не найдена."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=422, detail=f"Не удалось добавить слово: {str(e)}"
        )

    return {"message": "Слово добавлено", "id": new_word.id}


# Получение случайного слова, исключая слово с указанным ID
@router.get("/next-word/{exclude_id}")
def get_next_word(
    exclude_id: int, difficulty: DifficultyEnum, db: Session = Depends(get_db)
):
    try:
        words = db.scalars(
            select(WordWithAssociations).where(
                WordWithAssociations.id != exclude_id,
                WordWithAssociations.is_active == True,
                WordWithAssociations.difficulty == difficulty,
            )
        ).all()
    except ProgrammingError:
        raise HTTPException(status_code=404, detail="Нет активных слов для выбора")

    if not words:
        raise HTTPException(status_code=404, detail="Нет активных слов для выбора")

    word = random.choice(words)
    return {
        "id": word.id,
        "category": word.category,
        "word": word.word,
        "associations": word.associations,
        "difficulty": word.difficulty,
    }


def get_word_by_id_internal(word_id: int, db: Session):
    try:
        word = db.scalar(
            select(WordWithAssociations).where(WordWithAssociations.id == word_id)
        )
    except ProgrammingError:
        raise HTTPException(status_code=404, detail="Слово не найдено")
    if not word:
        raise HTTPException(status_code=404, detail="Слово не найдено")
    return {
        "id": word.id,
        "category": word.category,
        "word": word.word,
        "associations": word.associations,
        "difficulty": word.difficulty,
    }


# Получение слова по ID
@router.get("/word-by-id/{word_id}")
def get_word_by_id(word_id: int, db: Session = Depends(get_db)):
    return get_word_by_id_internal(word_id, db)


# Получение случайного слова по категории
@router.get("/{category}")
def get_word_by_category(category: str, db: Session = Depends(get_db)):
    try:
        words = db.scalars(
            select(WordWithAssociations).where(
                WordWithAssociations.category == category,
                WordWithAssociations.is_active == True,
            )
        ).all()
    except ProgrammingError:
        raise HTTPException(
            status_code=404, detail="Категория не найдена или нет активных слов"
        )
    if not words:
        raise HTTPException(
            status_code=404, detail="Категория не найдена или нет активных слов"
        )

    word = random.choice(words)
    return {
        "word": word.word,
        "associations": word.associations,
        "difficulty": word.difficulty,
    }
