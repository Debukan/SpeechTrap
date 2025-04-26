from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.models.player import Player
from app.schemas.player import PlayerCreate, PlayerResponse
from app.models.word import WordWithAssociations

router = APIRouter()


@router.post("/", response_model=PlayerResponse)
async def create_player(player: PlayerCreate, db: Session = Depends(get_db)):
    db_player = Player(**player.dict())
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player


@router.post("/players/{player_id}/answer")
def process_player_answer(
    player_id: int,
    word_id: int,
    guessed_association: str,
    db: Session = Depends(get_db),
):
    """
    Обработка ответа игрока. Сравнивает его ответ с ассоциациями слова.
    Обновляет статистику игрока и слова.
    """

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Игрок не найден")

    word = (
        db.query(WordWithAssociations)
        .filter(WordWithAssociations.id == word_id)
        .first()
    )
    if not word:
        raise HTTPException(status_code=404, detail="Слово не найдено")

    # Сравниваем слова
    is_correct = player.check_answer(word, guessed_association)

    # Обновляем статистику игрока
    if is_correct:
        player.correct_answers += 1
        player.update_score(1)
    else:
        player.wrong_answers += 1

    # Обновляем статистику слова
    word.update_stats(success=is_correct)

    db.commit()

    return {
        "correct": is_correct,
        "player_score": player.score,
        "player_success_rate": player.success_rate,
        "word_success_rate": word.success_rate,
    }
