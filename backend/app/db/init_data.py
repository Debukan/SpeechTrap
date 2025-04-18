import json
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.models.word import WordWithAssociations

# Функция для загрузки начальных данных (слов) в базу данных
def init_data():
    """
    Загружает слова и ассоциации из файла words.json в базу данных.
    """
    with open("words.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    db = next(get_db())
    try:
        # Проверяем, есть ли уже данные в таблице
        if not db.query(WordWithAssociations).first():
            for category, difficulties in data.items():
                for difficulty, words in difficulties.items():
                    for word, associations in words.items():
                        word_entry = WordWithAssociations(
                            category=category,
                            word=word,
                            associations=associations,
                            difficulty=difficulty  # Устанавливаем сложность
                        )
                        db.add(word_entry)
            db.commit()
            print("Initial data loaded successfully")
        else:
            print("Data already exists in the database")
    finally:
        db.close()

if __name__ == "__main__":
    init_data()
