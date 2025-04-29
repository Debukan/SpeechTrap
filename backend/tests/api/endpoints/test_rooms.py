import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.user import User
from app.models.room import Room, GameStatus
from app.core.security import get_password_hash, create_access_token
import uuid
from unittest.mock import AsyncMock, patch
from app.models.player import Player, PlayerRole

client = TestClient(app)

@pytest.fixture
def auth_user(test_db: Session):
    """Создает тестового пользователя и возвращает его JWT токен."""
    user = User(
        name="Room Test User",
        email="roomtest@example.com",
        hashed_password=get_password_hash("roompass123")
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    token = create_access_token(data={"sub": user.email})
    return {"user": user, "token": token}

def test_create_room(test_db: Session, auth_user):
    """Тест создания игровой комнаты."""
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    
    room_code = str(uuid.uuid4())[:6]
    
    room_data = {
        "code": room_code,
        "max_players": 6,
        "rounds_total": 5,
        "time_per_round": 60
    }
    
    response = client.post("/api/rooms/create", json=room_data, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "id" in data
    assert "code" in data
    assert data["code"] == room_code
    assert data["max_players"] == room_data["max_players"]
    assert data["rounds_total"] == room_data["rounds_total"]
    assert data["time_per_round"] == room_data["time_per_round"]
    assert data["status"] == GameStatus.WAITING
    
    room = test_db.query(Room).filter(Room.id == data["id"]).first()
    assert room is not None
    assert room.code == data["code"]
    assert room.status == GameStatus.WAITING

def test_join_room(test_db: Session, auth_user):
    """Тест присоединения к игровой комнате."""
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    
    room = Room(code="test12", max_players=6)
    test_db.add(room)
    test_db.commit()
    test_db.refresh(room)
    
    user_id = auth_user['user'].id
    response = client.post(f"/api/rooms/join/{room.code}/{user_id}", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "message" in data
    
    room_response = client.get(f"/api/rooms/{room.code}", headers=headers)
    assert room_response.status_code == 200
    room_data = room_response.json()
    
    assert len(room_data["players"]) > 0
    
    player_found = False
    for player in room_data["players"]:
        if player.get("name") == auth_user["user"].name:
            player_found = True
            break
    
    assert player_found, "Пользователь не найден в списке игроков комнаты"

def test_join_nonexistent_room(auth_user):
    """Тест присоединения к несуществующей комнате."""
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    
    user_id = auth_user['user'].id
    nonexistent_code = "nonexistent"
    response = client.post(f"/api/rooms/join/{nonexistent_code}/{user_id}", headers=headers)
    
    assert response.status_code == 404
    assert "не найдена" in response.json()["detail"]

def test_leave_room(test_db: Session, auth_user):
    """Тест выхода из игровой комнаты."""
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    
    room = Room(code="leave1", max_players=6)
    test_db.add(room)
    test_db.commit()
    test_db.refresh(room)
    
    user_id = auth_user['user'].id
    player = Player(user_id=user_id, room_id=room.id, role=PlayerRole.WAITING)
    test_db.add(player)
    test_db.commit()
    test_db.refresh(player)
    
    with patch('app.api.endpoints.rooms.manager.broadcast', new_callable=AsyncMock):
        response = client.post(f"/api/rooms/{room.code}/leave", headers=headers)
    
    assert response.status_code == 200
    
    test_db.expire_all()
    player_check = test_db.query(Player).filter(Player.user_id == user_id).first()
    assert player_check is None
