import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.user import User
from app.models.room import Room, GameStatus
from app.models.player import Player, PlayerRole
from app.models.word import WordWithAssociations
from app.core.security import get_password_hash, create_access_token
import asyncio

client = TestClient(app)

@pytest.fixture
def start_game_setup(test_db: Session):
    """Настраивает игровую комнату для теста запуска игры."""
    user1 = User(name="Host", email="starthost@example.com", hashed_password=get_password_hash("hostpass"))
    user2 = User(name="Player", email="startplayer@example.com", hashed_password=get_password_hash("playerpass"))
    test_db.add_all([user1, user2])
    test_db.commit()
    
    room = Room(code="start1", status=GameStatus.WAITING, max_players=4)
    test_db.add(room)
    test_db.commit()
    
    player1 = Player(user_id=user1.id, room_id=room.id, role=PlayerRole.WAITING)
    player2 = Player(user_id=user2.id, room_id=room.id, role=PlayerRole.WAITING)
    test_db.add_all([player1, player2])
    
    word = WordWithAssociations(word="Тест", category="Тесты", associations=["проверка", "код", "функция"])
    test_db.add(word)
    test_db.commit()
    
    token = create_access_token(data={"sub": user1.email})
    
    return {
        "room": room,
        "user1": user1,
        "player1": player1,
        "token": token,
        "word": word
    }


@pytest.mark.usefixtures("test_db", "start_game_setup")
def test_start_game_isolated(test_db: Session, start_game_setup):
    """Изолированный тест начала игры с подменой всех асинхронных функций."""
    with patch('app.api.endpoints.game.start_periodic_game_state_updates', new=MagicMock()), \
         patch('app.api.endpoints.game.manager.broadcast', new_callable=AsyncMock) as mock_broadcast, \
         patch('app.api.endpoints.game.send_game_state_update', new_callable=AsyncMock) as mock_send_state, \
         patch('app.api.endpoints.game.start_round_timer', new_callable=AsyncMock) as mock_timer:
         
        headers = {"Authorization": f"Bearer {start_game_setup['token']}"}
        
        room_code = start_game_setup["room"].code
        
        response = client.post(f"/api/game/{room_code}/start", headers=headers)
        
        assert response.status_code == 200
        
        test_db.expire_all()
        
        room = test_db.query(Room).filter(Room.code == room_code).first()
        
        assert room.status == GameStatus.PLAYING
        assert room.current_round == 1
        assert room.current_word_id is not None
        
        players = test_db.query(Player).filter(Player.room_id == room.id).all()
        
        explaining_count = sum(1 for p in players if p.role == PlayerRole.EXPLAINING)
        guessing_count = sum(1 for p in players if p.role == PlayerRole.GUESSING)
        
        assert explaining_count == 1
        assert guessing_count == len(players) - 1
        
        mock_send_state.assert_called()
        mock_broadcast.assert_called()
        mock_timer.assert_called_once()
