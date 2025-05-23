import pytest
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.room import Room, GameStatus
from app.models.player import Player, PlayerRole
from app.models.word import WordWithAssociations, DifficultyEnum
from app.core.security import get_password_hash
import uuid


def test_create_user(test_db: Session):
    """Тест создания пользователя в БД."""
    user_data = {
        "name": "Test User Model",
        "email": "testmodel@example.com",
        "hashed_password": get_password_hash("testpassword123"),
        "is_active": True,
    }
    db_user = User(**user_data)
    test_db.add(db_user)
    test_db.commit()
    test_db.refresh(db_user)

    assert db_user.id is not None
    assert db_user.email == user_data["email"]
    assert db_user.name == user_data["name"]
    assert db_user.hashed_password == user_data["hashed_password"]
    assert db_user.is_active == user_data["is_active"]


def test_create_room(test_db: Session):
    """Тест создания комнаты в БД."""
    room_data = {
        "code": str(uuid.uuid4())[:6],
        "max_players": 8,
        "rounds_total": 5,
        "time_per_round": 90,
        "status": GameStatus.WAITING,
    }
    db_room = Room(**room_data)
    test_db.add(db_room)
    test_db.commit()
    test_db.refresh(db_room)

    assert db_room.id is not None
    assert db_room.code == room_data["code"]
    assert db_room.max_players == room_data["max_players"]
    assert db_room.rounds_total == room_data["rounds_total"]
    assert db_room.time_per_round == room_data["time_per_round"]
    assert db_room.status == GameStatus.WAITING
    assert db_room.current_round == 0
    assert not db_room.is_full()
    assert not db_room.can_start()
    assert db_room.get_player_count() == 0


def test_create_word(test_db: Session):
    """Тест создания слова в БД."""
    word_data = {
        "word": "Тестовое слово",
        "category": "Тест",
        "associations": ["ассоциация1", "тест2"],
        "is_active": True,
        "difficulty": DifficultyEnum.basic,
    }
    db_word = WordWithAssociations(**word_data)
    test_db.add(db_word)
    test_db.commit()
    test_db.refresh(db_word)

    assert db_word.id is not None
    assert db_word.word == word_data["word"]
    assert db_word.category == word_data["category"]
    assert db_word.associations == word_data["associations"]
    assert db_word.is_active == word_data["is_active"]
    assert db_word.times_used == 0
    assert db_word.success_rate == 0.0
    assert db_word.difficulty == word_data["difficulty"]


def test_create_player(test_db: Session):
    """Тест создания игрока в БД и связи с пользователем и комнатой."""
    user = User(
        name="Player User",
        email="player@example.com",
        hashed_password=get_password_hash("playerpass"),
    )
    room = Room(code=str(uuid.uuid4())[:6])
    test_db.add(user)
    test_db.add(room)
    test_db.commit()
    test_db.refresh(user)
    test_db.refresh(room)

    player_data = {
        "user_id": user.id,
        "room_id": room.id,
        "role": PlayerRole.WAITING,
    }
    db_player = Player(**player_data)
    test_db.add(db_player)
    test_db.commit()
    test_db.refresh(db_player)

    assert db_player.id is not None
    assert db_player.user_id == user.id
    assert db_player.room_id == room.id
    assert db_player.score == 0
    assert db_player.score_total == 0
    assert db_player.role == PlayerRole.WAITING
    assert db_player.correct_answers == 0
    assert db_player.wrong_answers == 0
    assert db_player.success_rate == 0.0

    test_db.refresh(user)
    test_db.refresh(room)
    assert db_player in user.players
    assert db_player in room.players


def test_player_update_score(test_db: Session):
    """Тест обновления очков игрока."""
    user = User(name="Score User", email="score@example.com", hashed_password="pw")
    room = Room(code=str(uuid.uuid4())[:6])
    test_db.add_all([user, room])
    test_db.commit()
    player = Player(user_id=user.id, room_id=room.id)
    test_db.add(player)
    test_db.commit()
    test_db.refresh(player)

    player.update_score(10)
    assert player.score == 10
    player.update_score(-5)
    assert player.score == 5
    test_db.commit()


def test_player_check_answer(test_db: Session):
    """Тест проверки ответа игрока."""
    word = WordWithAssociations(
        word="Яблоко",
        category="Фрукты",
        associations=["красное", "фрукт", "круглое"],
        is_active=True,
        difficulty=DifficultyEnum.basic,
    )
    test_db.add(word)
    test_db.commit()
    test_db.refresh(word)

    player = Player(user_id=1, room_id=1)

    assert player.check_answer(word, "красное") is True
    assert player.check_answer(word, "Красное") is True
    assert player.check_answer(word, "зеленое") is False
    assert player.check_answer(word, "фрукт") is True


def test_room_add_remove_player(test_db: Session):
    """Тест добавления и удаления игрока из комнаты."""
    user1 = User(name="User1", email="user1@example.com", hashed_password="pw")
    user2 = User(name="User2", email="user2@example.com", hashed_password="pw")
    room = Room(code=str(uuid.uuid4())[:6], max_players=2)
    test_db.add_all([user1, user2, room])
    test_db.commit()
    test_db.refresh(room)

    player1 = Player(user_id=user1.id, room_id=room.id)
    test_db.add(player1)
    test_db.commit()
    test_db.refresh(room)
    test_db.refresh(player1)

    assert room.get_player_count() == 1
    assert player1 in room.players
    assert not room.is_full()
    assert not room.can_start()

    player2 = Player(user_id=user2.id, room_id=room.id)
    test_db.add(player2)
    test_db.commit()
    test_db.refresh(room)
    test_db.refresh(player2)

    assert room.get_player_count() == 2
    assert player2 in room.players
    assert room.is_full()
    assert room.can_start()

    test_db.delete(player1)
    test_db.commit()
    test_db.refresh(room)

    assert room.get_player_count() == 1
    assert not room.is_full()
    assert not room.can_start()
