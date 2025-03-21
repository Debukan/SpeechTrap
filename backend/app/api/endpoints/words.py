import random
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from app.db.deps import get_db
from app.models.word import WordWithAssociations  # Импорт модели

router = APIRouter()

# Проверка подключения к базе данных
@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database connected successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Получение случайного слова по категории
@router.get("/word/{category}")
def get_word_by_category(category: str, db: Session = Depends(get_db)):
    words = db.query(WordWithAssociations).filter(
        WordWithAssociations.category == category,
        WordWithAssociations.is_active == True
    ).all()
    if not words:
        raise HTTPException(status_code=404, detail="Категория не найдена или нет активных слов")

    word = random.choice(words)
    return {"word": word.word, "associations": word.associations}

# Получение случайного слова из случайной категории
@router.get("/random-word")
def get_random_word(db: Session = Depends(get_db)):
    words = db.query(WordWithAssociations).filter(WordWithAssociations.is_active == True).all()
    if not words:
        raise HTTPException(status_code=404, detail="Слов нет в базе")

    word = random.choice(words)
    return {"category": word.category, "word": word.word, "associations": word.associations}

# Обновление статистики слова
@router.post("/word/{word_id}/update-stats")
def update_word_stats(word_id: int, success: bool, db: Session = Depends(get_db)):
    word = db.query(WordWithAssociations).filter(WordWithAssociations.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Слово не найдено")

    word.update_stats(success)
    db.commit()
    return {"message": "Статистика обновлена", "word_id": word.id, "success_rate": word.success_rate}

# Добавление нового слова
@router.post("/word/")
def add_word(word: str, category: str, associations: list[str], db: Session = Depends(get_db)):
    new_word = WordWithAssociations(word=word, category=category, associations=associations)
    db.add(new_word)
    db.commit()
    db.refresh(new_word)
    return {"message": "Слово добавлено", "id": new_word.id}
