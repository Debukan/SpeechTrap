import random
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import text, func
from app.db.deps import get_db
from app.models.word import WordWithAssociations, DifficultyEnum
from typing import Literal

router = APIRouter()

# Получение случайного слова из случайной категории
@router.get("/random-word")
def get_random_word(
    difficulty: DifficultyEnum = Query(...),
    db: Session = Depends(get_db)
):
    words = db.query(WordWithAssociations).filter(
        WordWithAssociations.is_active == True,
        WordWithAssociations.difficulty == difficulty
    ).all()

    if not words:
        raise HTTPException(status_code=404, detail="Нет слов подходящей сложности")

    word = random.choice(words)

    return {
        "id": word.id,
        "category": word.category,
        "word": word.word,
        "associations": word.associations,
        "difficulty": difficulty
    }
    # TODO: non-repeating words

# Обновление статистики слова
@router.post("/{word_id}/update-stats")
def update_word_stats(word_id: int, success: bool, db: Session = Depends(get_db)):
    word = db.query(WordWithAssociations).filter(WordWithAssociations.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Слово не найдено")

    word.update_stats(success)
    db.commit()
    return {"message": "Статистика обновлена", "word_id": word.id, "success_rate": word.success_rate}

# Добавление нового слова
@router.post("/")
def add_word(
    word: str,
    category: str,
    difficulty: DifficultyEnum,
    associations: list[str],
    db: Session = Depends(get_db)
):
    new_word = WordWithAssociations(
        word=word,
        category=category,
        difficulty=difficulty,
        associations=associations
    )
    db.add(new_word)
    db.commit()
    db.refresh(new_word)
    return {"message": "Слово добавлено", "id": new_word.id}

# Получение случайного слова, исключая слово с указанным ID
@router.get("/next-word/{exclude_id}")
def get_next_word(exclude_id: int, db: Session = Depends(get_db)):
    words = db.query(WordWithAssociations).filter(
        WordWithAssociations.id != exclude_id,
        WordWithAssociations.is_active == True
    ).all()

    if not words:
        raise HTTPException(status_code=404, detail="Нет активных слов для выбора")

    word = random.choice(words)
    return {
        "id": word.id,
        "category": word.category,
        "word": word.word,
        "associations": word.associations
    }

# Получение слова по ID
@router.get("/word-by-id/{word_id}")
def get_word_by_id(word_id: int, db: Session = Depends(get_db)):
    word = db.query(WordWithAssociations).filter(
        WordWithAssociations.id == word_id
    ).first()

    if not word:
        raise HTTPException(status_code=404, detail="Слово не найдено")

    return {
        "id": word.id,
        "category": word.category,
        "word": word.word,
        "associations": word.associations
    }

# Получение случайного слова по категории
@router.get("/{category}")
def get_word_by_category(category: str, db: Session = Depends(get_db)):
    words = db.query(WordWithAssociations).filter(
        WordWithAssociations.category == category,
        WordWithAssociations.is_active == True
    ).all()
    if not words:
        raise HTTPException(status_code=404, detail="Категория не найдена или нет активных слов")

    word = random.choice(words)
    return {"word": word.word, "associations": word.associations, "difficulty": word.difficulty}
