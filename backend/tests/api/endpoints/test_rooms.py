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
        hashed_password=get_password_hash("roompass123"),
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
        "time_per_round": 60,
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

    user_id = auth_user["user"].id
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

    user_id = auth_user["user"].id
    nonexistent_code = "nonexistent"
    response = client.post(
        f"/api/rooms/join/{nonexistent_code}/{user_id}", headers=headers
    )

    assert response.status_code == 404
    assert "не найдена" in response.json()["detail"]


def test_leave_room(test_db: Session, auth_user):
    """Тест выхода из игровой комнаты."""
    headers = {"Authorization": f"Bearer {auth_user['token']}"}

    room = Room(code="leave1", max_players=6)
    test_db.add(room)
    test_db.commit()
    test_db.refresh(room)

    user_id = auth_user["user"].id
    player = Player(user_id=user_id, room_id=room.id, role=PlayerRole.WAITING)
    test_db.add(player)
    test_db.commit()
    test_db.refresh(player)

    with patch("app.api.endpoints.rooms.manager.broadcast", new_callable=AsyncMock):
        response = client.post(f"/api/rooms/{room.code}/leave", headers=headers)

    assert response.status_code == 200

    test_db.expire_all()
    player_check = test_db.query(Player).filter(Player.user_id == user_id).first()
    assert player_check is None


def test_create_room_empty_code(auth_user, client):
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    data = {
        "code": "",
        "max_players": 4,
        "rounds_total": 3,
        "time_per_round": 30,
        "difficulty": "basic",
    }
    res = client.post("/api/rooms/create", json=data, headers=headers)
    assert res.status_code == 400
    assert "Код комнаты не может быть пустым" in res.json()["detail"]


def test_create_room_duplicate_code(auth_user, test_db, client):
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    code = str(uuid.uuid4())[:6]
    res1 = client.post(
        "/api/rooms/create",
        json={
            "code": code,
            "max_players": 2,
            "rounds_total": 2,
            "time_per_round": 20,
            "difficulty": "basic",
        },
        headers=headers,
    )
    assert res1.status_code == 200, f"Первое создание комнаты не удалось: {res1.text}"
    res2 = client.post(
        "/api/rooms/create",
        json={
            "code": code,
            "max_players": 2,
            "rounds_total": 2,
            "time_per_round": 20,
            "difficulty": "basic",
        },
        headers=headers,
    )
    assert res2.status_code == 400
    assert "уже существует" in res2.json()["detail"]


def test_get_active_rooms(test_db, auth_user, client):
    test_db.query(Player).delete()
    test_db.query(Room).delete()
    test_db.commit()
    r1 = Room(
        code="A1",
        status=GameStatus.WAITING,
        max_players=2,
        rounds_total=1,
        time_per_round=10,
    )
    r2 = Room(
        code="A2",
        status=GameStatus.WAITING,
        max_players=2,
        rounds_total=1,
        time_per_round=10,
    )
    test_db.add_all([r1, r2])
    test_db.commit()
    res = client.get("/api/rooms/active")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    codes = [r["code"] for r in data]
    assert set(codes) >= {"A1", "A2"}


def test_get_room_not_found(client):
    res = client.get("/api/rooms/NOCODE")
    assert res.status_code == 404
    assert "Комната не найдена" in res.json()["detail"]


def test_get_room_success(test_db, auth_user, client):
    room = Room(
        code="BC",
        status=GameStatus.WAITING,
        max_players=3,
        rounds_total=1,
        time_per_round=10,
    )
    test_db.add(room)
    test_db.commit()
    test_db.refresh(room)
    player = Player(
        user_id=auth_user["user"].id, room_id=room.id, role=PlayerRole.WAITING
    )
    test_db.add(player)
    test_db.commit()
    test_db.refresh(player)
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    res = client.get(f"/api/rooms/{room.code}", headers=headers)
    assert res.status_code == 200
    d = res.json()
    assert d["code"] == "BC"
    assert any(p["id"] == player.id for p in d["players"])


def test_join_forbidden(auth_user, test_db, client):
    room = Room(
        code="J1",
        status=GameStatus.WAITING,
        max_players=2,
        rounds_total=1,
        time_per_round=5,
    )
    test_db.add(room)
    test_db.commit()
    test_db.refresh(room)
    other = User(
        name="UU", email="uu@example.com", hashed_password=get_password_hash("x")
    )
    test_db.add(other)
    test_db.commit()
    test_db.refresh(other)
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    res = client.post(f"/api/rooms/join/{room.code}/{other.id}", headers=headers)
    assert res.status_code == 403
    assert "Нет прав" in res.json()["detail"]


def test_join_user_not_found(auth_user, test_db, client):
    room = Room(
        code="J2",
        status=GameStatus.WAITING,
        max_players=2,
        rounds_total=1,
        time_per_round=5,
    )
    test_db.add(room)
    test_db.commit()
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    res = client.post(f"/api/rooms/join/{room.code}/9999", headers=headers)
    assert res.status_code == 403
    assert "Нет прав" in res.json()["detail"]


def test_join_already_in_room(auth_user, test_db, client):
    room = Room(
        code="J3",
        status=GameStatus.WAITING,
        max_players=2,
        rounds_total=1,
        time_per_round=5,
    )
    test_db.add(room)
    test_db.commit()
    test_db.refresh(room)
    player = Player(
        user_id=auth_user["user"].id, room_id=room.id, role=PlayerRole.WAITING
    )
    test_db.add(player)
    test_db.commit()
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    res = client.post(
        f"/api/rooms/join/{room.code}/{auth_user['user'].id}", headers=headers
    )
    assert res.status_code == 400
    assert "уже в комнате" in res.json()["detail"]


def test_delete_room_not_found(auth_user, client):
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    res = client.delete("/api/rooms/NOROOM", headers=headers)
    assert res.status_code == 404


def test_delete_room_not_creator(test_db, auth_user, client):
    u1 = auth_user["user"]
    u2 = User(
        name="other", email="o@example.com", hashed_password=get_password_hash("p")
    )
    test_db.add(u2)
    test_db.commit()
    test_db.refresh(u2)
    room = Room(
        code="D1",
        status=GameStatus.WAITING,
        max_players=2,
        rounds_total=1,
        time_per_round=5,
    )
    test_db.add(room)
    test_db.commit()
    test_db.refresh(room)
    p1 = Player(user_id=u1.id, room_id=room.id, role=PlayerRole.WAITING)
    p2 = Player(user_id=u2.id, room_id=room.id, role=PlayerRole.WAITING)
    test_db.add_all([p1, p2])
    test_db.commit()
    token2 = create_access_token(data={"sub": u2.email})
    headers2 = {"Authorization": f"Bearer {token2}"}
    res = client.delete(f"/api/rooms/{room.code}", headers=headers2)
    assert res.status_code == 403
    assert "Только создатель" in res.json()["detail"]


def test_delete_room_success(test_db, auth_user, client):
    u = auth_user["user"]
    room = Room(
        code="D2",
        status=GameStatus.WAITING,
        max_players=2,
        rounds_total=1,
        time_per_round=5,
    )
    test_db.add(room)
    test_db.commit()
    test_db.refresh(room)
    p = Player(user_id=u.id, room_id=room.id, role=PlayerRole.WAITING)
    test_db.add(p)
    test_db.commit()
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    with patch("app.api.endpoints.rooms.manager.broadcast", new_callable=AsyncMock):
        res = client.delete(f"/api/rooms/{room.code}", headers=headers)
    assert res.status_code == 200
    deleted = test_db.query(Room).filter(Room.code == "D2").first()
    assert deleted is None


def test_lobby_chat_no_room(auth_user, client):
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    res = client.post("/api/rooms/NOCH/chat", json={"message": "hi"}, headers=headers)
    assert res.status_code == 404


def test_lobby_chat_not_player(test_db, auth_user, client):
    room = Room(
        code="C1",
        status=GameStatus.WAITING,
        max_players=2,
        rounds_total=1,
        time_per_round=5,
    )
    test_db.add(room)
    test_db.commit()
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    res = client.post(
        f"/api/rooms/{room.code}/chat", json={"message": "hi"}, headers=headers
    )
    assert res.status_code == 403


def test_lobby_chat_success(test_db, auth_user, client):
    room = Room(
        code="C2",
        status=GameStatus.WAITING,
        max_players=2,
        rounds_total=1,
        time_per_round=5,
    )
    test_db.add(room)
    test_db.commit()
    test_db.refresh(room)
    p = Player(user_id=auth_user["user"].id, room_id=room.id, role=PlayerRole.WAITING)
    test_db.add(p)
    test_db.commit()
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    with patch("app.api.endpoints.rooms.manager.broadcast", new_callable=AsyncMock):
        res = client.post(
            f"/api/rooms/{room.code}/chat", json={"message": "hello"}, headers=headers
        )
    assert res.status_code == 200
    assert res.json()["success"] is True
