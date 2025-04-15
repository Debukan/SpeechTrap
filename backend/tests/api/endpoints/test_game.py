import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.user import User
from app.models.room import Room, GameStatus
from app.models.player import Player, PlayerRole
from app.models.word import WordWithAssociations
from app.core.security import get_password_hash, create_access_token

client = TestClient(app)

@pytest.fixture
def incorrect_guess_setup(test_db: Session):
    """Настраивает игровую комнату для теста неправильной догадки."""
    user1 = User(name="Host2", email="host2@example.com", hashed_password=get_password_hash("hostpass"))
    user2 = User(name="Player2", email="player2@example.com", hashed_password=get_password_hash("playerpass"))
    test_db.add_all([user1, user2])
    test_db.commit()
    
    room = Room(
        code="guess2", 
        status=GameStatus.PLAYING, 
        max_players=4, 
        rounds_total=5, 
        current_round=1,
        time_per_round=60
    )
    test_db.add(room)
    test_db.commit()
    
    word = WordWithAssociations(
        word="Банан",
        category="Фрукты",
        associations=["желтый", "обезьяна", "тропики"],
        is_active=True
    )
    test_db.add(word)
    test_db.commit()
    
    room.current_word_id = word.id
    test_db.commit()
    
    player1 = Player(
        user_id=user1.id, 
        room_id=room.id, 
        role=PlayerRole.EXPLAINING, 
        score=0, 
        wrong_answers=0,
        correct_answers=0,
        score_total=0
    )
    player2 = Player(
        user_id=user2.id, 
        room_id=room.id, 
        role=PlayerRole.GUESSING, 
        score=0, 
        wrong_answers=0,
        correct_answers=0,
        score_total=0
    )
    test_db.add_all([player1, player2])
    test_db.commit()
    
    token1 = create_access_token(data={"sub": user1.email})
    token2 = create_access_token(data={"sub": user2.email})
    
    return {
        "room": room,
        "user1": user1,
        "user2": user2,
        "player1": player1,
        "player2": player2,
        "token1": token1,
        "token2": token2,
        "word": word
    }


@patch('app.api.endpoints.game.manager.broadcast', new_callable=AsyncMock)
def test_submit_guess_incorrect(mock_manager_broadcast, test_db: Session, incorrect_guess_setup):
    """Тест отправки неправильного ответа."""
    room = incorrect_guess_setup["room"]
    player2 = incorrect_guess_setup["player2"]

    headers = {"Authorization": f"Bearer {incorrect_guess_setup['token2']}"}

    guess_data = {"guess": "Груша"}

    response = client.post(f"/api/game/{room.code}/guess", json=guess_data, headers=headers)
    assert response.status_code == 200

    data = response.json()

    assert data["correct"] is False
    
    test_db.expire_all()
    player2 = test_db.get(Player, player2.id)
    assert player2.wrong_answers >= 1
