import pytest
from unittest.mock import patch, AsyncMock, MagicMock, call
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.main import app
from app.models.user import User
from app.models.room import Room, GameStatus
from app.models.player import Player, PlayerRole
from app.models.word import WordWithAssociations, DifficultyEnum
from app.core.security import get_password_hash, create_access_token
from app.api.endpoints.game import send_game_state_update, start_round_timer
from app.api.endpoints import game as game_module
import time
import asyncio

client = TestClient(app)

original_asyncio_sleep = asyncio.sleep


@pytest.fixture
def incorrect_guess_setup(test_db: Session):
    """Настраивает игровую комнату для теста неправильной догадки."""
    user1 = User(
        name="Host2",
        email="host2@example.com",
        hashed_password=get_password_hash("hostpass"),
    )
    user2 = User(
        name="Player2",
        email="player2@example.com",
        hashed_password=get_password_hash("playerpass"),
    )
    test_db.add_all([user1, user2])
    test_db.commit()

    room = Room(
        code="guess2",
        status=GameStatus.PLAYING,
        max_players=4,
        rounds_total=5,
        current_round=1,
        time_per_round=60,
    )
    test_db.add(room)
    test_db.commit()

    word = WordWithAssociations(
        word="Банан",
        category="Фрукты",
        associations=["желтый", "обезьяна", "тропики"],
        is_active=True,
        difficulty=DifficultyEnum.basic,
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
        score_total=0,
    )
    player2 = Player(
        user_id=user2.id,
        room_id=room.id,
        role=PlayerRole.GUESSING,
        score=0,
        wrong_answers=0,
        correct_answers=0,
        score_total=0,
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
        "word": word,
    }


@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
def test_submit_guess_incorrect(
    mock_manager_broadcast, test_db: Session, incorrect_guess_setup
):
    """Тест отправки неправильного ответа."""
    room = incorrect_guess_setup["room"]
    player2 = incorrect_guess_setup["player2"]

    headers = {"Authorization": f"Bearer {incorrect_guess_setup['token2']}"}

    guess_data = {"guess": "Груша"}

    response = client.post(
        f"/api/game/{room.code}/guess", json=guess_data, headers=headers
    )
    assert response.status_code == 200

    data = response.json()

    assert data["correct"] is False

    test_db.expire_all()
    player2 = test_db.get(Player, player2.id)
    assert player2.wrong_answers >= 1


@pytest.fixture
def setup_users_rooms(test_db: Session):
    """Фикстура для создания пользователей, комнаты и игроков."""
    user1 = User(
        name="GameUser1",
        email="gu1@example.com",
        hashed_password=get_password_hash("pass1"),
    )
    user2 = User(
        name="GameUser2",
        email="gu2@example.com",
        hashed_password=get_password_hash("pass2"),
    )
    test_db.add_all([user1, user2])
    test_db.commit()
    test_db.refresh(user1)
    test_db.refresh(user2)
    word = WordWithAssociations(
        word="TestWord",
        category="TestCat",
        difficulty=DifficultyEnum.basic,
        associations=["t1"],
    )
    test_db.add(word)
    test_db.commit()
    test_db.refresh(word)
    room = Room(
        code="GAME1",
        status=GameStatus.WAITING,
        max_players=4,
        rounds_total=3,
        time_per_round=60,
        difficulty=DifficultyEnum.basic,
        current_word_id=word.id,
    )
    test_db.add(room)
    test_db.commit()
    test_db.refresh(room)

    player1 = Player(user_id=user1.id, room_id=room.id, role=PlayerRole.WAITING)
    player2 = Player(user_id=user2.id, room_id=room.id, role=PlayerRole.WAITING)
    test_db.add_all([player1, player2])
    test_db.commit()
    test_db.refresh(player1)
    test_db.refresh(player2)

    token1 = create_access_token(data={"sub": user1.email})
    token2 = create_access_token(data={"sub": user2.email})

    return {
        "db": test_db,
        "users": [user1, user2],
        "tokens": [token1, token2],
        "room": room,
        "players": [player1, player2],
        "word": word,
    }


def test_get_game_state_room_not_found(client, setup_users_rooms):
    """Тест получения состояния игры для несуществующей комнаты."""
    token = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/game/NOROOM/state", headers=headers)
    assert response.status_code == 404
    assert "Комната не найдена" in response.json()["detail"]


def test_get_game_state_player_not_in_room(client, test_db: Session):
    """Тест получения состояния игры пользователем не из комнаты."""
    user_other = User(
        name="OtherUser",
        email="other@example.com",
        hashed_password=get_password_hash("pass"),
    )
    room_other = Room(code="OTHER", status=GameStatus.WAITING)
    test_db.add_all([user_other, room_other])
    test_db.commit()
    test_db.refresh(user_other)

    token_other = create_access_token(data={"sub": user_other.email})
    headers = {"Authorization": f"Bearer {token_other}"}

    response = client.get(f"/api/game/{room_other.code}/state", headers=headers)
    assert response.status_code == 403
    assert "Вы не являетесь участником этой комнаты" in response.json()["detail"]


def test_get_game_state_waiting(client, setup_users_rooms):
    """Тест получения состояния игры в статусе WAITING."""
    room = setup_users_rooms["room"]
    token = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/api/game/{room.code}/state", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == GameStatus.WAITING.upper()
    assert data["currentWord"] == ""
    assert data["round"] == 0
    assert data["timeLeft"] == room.time_per_round
    assert len(data["players"]) == len(setup_users_rooms["players"])
    assert data["currentPlayer"] is None


def test_get_game_state_playing_guesser(client, setup_users_rooms):
    """Тест получения состояния игры для угадывающего."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    players = setup_users_rooms["players"]
    word = setup_users_rooms["word"]
    token_guesser = setup_users_rooms["tokens"][1]
    headers = {"Authorization": f"Bearer {token_guesser}"}

    room.status = GameStatus.PLAYING
    room.current_round = 1
    players[0].role = PlayerRole.EXPLAINING
    players[1].role = PlayerRole.GUESSING
    db.commit()

    response = client.get(f"/api/game/{room.code}/state", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == GameStatus.PLAYING.upper()
    assert data["currentWord"] == ""
    assert data["round"] == 1
    assert data["timeLeft"] is not None
    assert data["currentPlayer"] == str(players[0].id)


def test_get_game_state_playing_explainer(client, setup_users_rooms):
    """Тест получения состояния игры для объясняющего."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    players = setup_users_rooms["players"]
    word = setup_users_rooms["word"]
    token_explainer = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token_explainer}"}

    room.status = GameStatus.PLAYING
    room.current_round = 1
    players[0].role = PlayerRole.EXPLAINING
    players[1].role = PlayerRole.GUESSING
    db.commit()

    response = client.get(f"/api/game/{room.code}/state", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == GameStatus.PLAYING.upper()
    assert data["currentWord"] == word.word
    assert data["round"] == 1
    assert data["timeLeft"] is not None
    assert data["currentPlayer"] == str(players[0].id)


def test_start_game_room_not_found(client, setup_users_rooms):
    """Тест старта игры для несуществующей комнаты."""
    token = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/game/NOROOM/start", headers=headers)
    assert response.status_code == 404


def test_start_game_not_creator(client, setup_users_rooms):
    """Тест старта игры не создателем."""
    room = setup_users_rooms["room"]
    token_not_creator = setup_users_rooms["tokens"][1]
    headers = {"Authorization": f"Bearer {token_not_creator}"}
    response = client.post(f"/api/game/{room.code}/start", headers=headers)
    assert response.status_code == 403
    assert "Только создатель" in response.json()["detail"]


def test_start_game_already_playing(client, setup_users_rooms):
    """Тест старта игры, которая уже идет."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    room.status = GameStatus.PLAYING
    db.commit()
    token_creator = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token_creator}"}
    response = client.post(f"/api/game/{room.code}/start", headers=headers)
    assert response.status_code == 400
    assert "Игра уже началась" in response.json()["detail"]


def test_start_game_not_enough_players(client, setup_users_rooms):
    """Тест старта игры с одним игроком."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    player_to_remove = setup_users_rooms["players"][1]
    db.delete(player_to_remove)
    db.commit()
    token_creator = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token_creator}"}
    response = client.post(f"/api/game/{room.code}/start", headers=headers)
    assert response.status_code == 400
    assert "минимум 2 игрока" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.manager.send_personal_message", new_callable=AsyncMock)
async def test_send_game_state_update_room_not_found(
    mock_send_personal, mock_broadcast, test_db: Session
):
    """Тест отправки состояния для несуществующей комнаты."""
    await send_game_state_update("NONEXISTENT", test_db)
    mock_broadcast.assert_not_called()
    mock_send_personal.assert_not_called()


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.manager.send_personal_message", new_callable=AsyncMock)
async def test_send_game_state_update_not_playing(
    mock_send_personal, mock_broadcast, setup_users_rooms
):
    """Тест отправки состояния, когда игра не в статусе PLAYING."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    room.status = GameStatus.WAITING
    db.commit()

    await send_game_state_update(room.code, db)
    mock_broadcast.assert_not_called()
    mock_send_personal.assert_not_called()


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.manager.send_personal_message", new_callable=AsyncMock)
@patch("app.api.endpoints.game.time.time")
async def test_send_game_state_update_playing(
    mock_time, mock_send_personal, mock_broadcast, setup_users_rooms
):
    """Тест успешной отправки состояния во время игры."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    players = setup_users_rooms["players"]
    word = setup_users_rooms["word"]
    user1 = setup_users_rooms["users"][0]
    user2 = setup_users_rooms["users"][1]

    room.status = GameStatus.PLAYING
    room.current_round = 2
    players[0].role = PlayerRole.EXPLAINING
    players[0].score = 5
    players[1].role = PlayerRole.GUESSING
    players[1].score = 10
    db.commit()

    start_time = 1000.0
    current_time = 1015.5
    mock_time.return_value = current_time
    from app.api.endpoints.game import room_timers

    room_timers[room.code] = {"start_time": start_time, "duration": room.time_per_round}
    expected_time_left = max(0, int(room.time_per_round - (current_time - start_time)))

    await send_game_state_update(room.code, db)

    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room.code
    broadcast_data = broadcast_call_args[1]
    assert broadcast_data["type"] == "game_state_update"
    game_state = broadcast_data["game_state"]
    assert game_state["status"] == GameStatus.PLAYING.upper()
    assert game_state["round"] == 2
    assert game_state["currentWord"] == ""
    assert game_state["timeLeft"] == expected_time_left
    assert game_state["currentPlayer"] == str(players[0].id)
    assert len(game_state["players"]) == 2
    player_state_1 = next(
        p for p in game_state["players"] if p["id"] == str(players[0].id)
    )
    player_state_2 = next(
        p for p in game_state["players"] if p["id"] == str(players[1].id)
    )
    assert player_state_1["username"] == user1.name
    assert player_state_1["score"] == 5
    assert player_state_1["role"] == PlayerRole.EXPLAINING
    assert player_state_2["username"] == user2.name
    assert player_state_2["score"] == 10
    assert player_state_2["role"] == PlayerRole.GUESSING

    mock_send_personal.assert_called_once()
    personal_call_args = mock_send_personal.call_args[0]
    assert personal_call_args[0] == str(user1.id)
    personal_data = personal_call_args[1]
    assert personal_data["type"] == "game_state_update"
    personal_game_state = personal_data["game_state"]
    assert personal_game_state["currentWord"] == word.word
    assert "associations" in personal_game_state
    assert personal_game_state["status"] == game_state["status"]
    assert personal_game_state["round"] == game_state["round"]
    assert personal_game_state["timeLeft"] == game_state["timeLeft"]
    assert personal_game_state["currentPlayer"] == game_state["currentPlayer"]
    assert len(personal_game_state["players"]) == len(game_state["players"])

    if room.code in room_timers:
        del room_timers[room.code]


@pytest.mark.asyncio
@patch("app.api.endpoints.game.asyncio.sleep", new_callable=AsyncMock)
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.get_next_word")
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
@patch("app.api.endpoints.game.asyncio.create_task")
@patch("app.api.endpoints.game.asyncio.current_task")
@patch("app.api.endpoints.game.time.time")
async def test_start_round_timer_next_round(
    mock_time,
    mock_current_task,
    mock_create_task,
    mock_send_state,
    mock_get_next_word,
    mock_broadcast,
    mock_sleep,
    setup_users_rooms,
):
    """Тест перехода к следующему раунду по таймеру."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    players = setup_users_rooms["players"]
    word = setup_users_rooms["word"]
    user1 = setup_users_rooms["users"][0]
    user2 = setup_users_rooms["users"][1]

    room.status = GameStatus.PLAYING
    room.current_round = 1
    players[0].role = PlayerRole.EXPLAINING
    players[1].role = PlayerRole.GUESSING
    db.commit()

    duration = room.time_per_round
    start_time = 1000.0
    end_time = start_time + duration
    mock_time.return_value = end_time
    game_module.room_timers[room.code] = {
        "start_time": start_time,
        "duration": duration,
    }
    mock_timer_task = MagicMock()
    game_module.timer_tasks[room.code] = mock_timer_task
    mock_current_task.return_value = mock_timer_task

    mock_next_word_data = {"id": word.id + 1, "word": "NextWord", "associations": []}

    next_word_db = WordWithAssociations(
        id=mock_next_word_data["id"],
        word=mock_next_word_data["word"],
        category="TestCat2",
        difficulty=DifficultyEnum.basic,
    )
    db.add(next_word_db)
    db.commit()

    mock_get_next_word.return_value = mock_next_word_data
    mock_next_timer_task = MagicMock()
    mock_create_task.return_value = mock_next_timer_task

    await start_round_timer(room.code, duration, db)

    mock_sleep.assert_called_once_with(duration)

    db.refresh(room)
    db.refresh(players[0])
    db.refresh(players[1])
    assert room.current_round == 2
    assert room.current_word_id == mock_next_word_data["id"]
    assert players[0].role == PlayerRole.GUESSING
    assert players[1].role == PlayerRole.EXPLAINING

    assert room.code in game_module.room_timers
    assert game_module.room_timers[room.code]["start_time"] == end_time
    assert room.code in game_module.timer_tasks
    assert game_module.timer_tasks[room.code] == mock_next_timer_task
    mock_create_task.assert_called_once()

    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room.code
    broadcast_data = broadcast_call_args[1]
    assert broadcast_data["type"] == "turn_changed"
    assert broadcast_data["current_player"] == str(players[1].id)
    assert broadcast_data["message"].startswith("Ход переходит к игроку")

    mock_send_state.assert_called_once_with(room.code, db)

    if room.code in game_module.room_timers:
        del game_module.room_timers[room.code]
    if room.code in game_module.timer_tasks:
        del game_module.timer_tasks[room.code]


@pytest.mark.asyncio
@patch("app.api.endpoints.game.asyncio.sleep", new_callable=AsyncMock)
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
@patch("app.api.endpoints.game.asyncio.current_task")
@patch("app.api.endpoints.game.time.time")
async def test_start_round_timer_game_finish(
    mock_time,
    mock_current_task,
    mock_send_state,
    mock_broadcast,
    mock_sleep,
    setup_users_rooms
):
    """Тест завершения игры по таймеру в последнем раунде."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    players = setup_users_rooms["players"]

    room.status = GameStatus.PLAYING
    room.current_round = room.rounds_total
    players[0].role = PlayerRole.EXPLAINING
    players[0].score = 15
    players[0].score_total = 10
    players[1].role = PlayerRole.GUESSING
    players[1].score = 20
    players[1].score_total = 5
    db.commit()

    duration = room.time_per_round
    start_time = 1000.0
    end_time = start_time + duration
    mock_time.return_value = end_time
    game_module.room_timers[room.code] = {
        "start_time": start_time,
        "duration": duration,
    }
    mock_timer_task = MagicMock()
    game_module.timer_tasks[room.code] = mock_timer_task
    mock_current_task.return_value = mock_timer_task

    await start_round_timer(room.code, duration, db)

    mock_sleep.assert_called_once_with(duration)

    db.refresh(room)
    db.refresh(players[0])
    db.refresh(players[1])
    assert room.status == GameStatus.WAITING
    assert room.current_round == 0
    assert players[0].role == PlayerRole.WAITING
    assert players[1].role == PlayerRole.WAITING
    assert players[0].score == 0
    assert players[1].score == 0
    assert players[0].score_total == 25
    assert players[1].score_total == 25

    assert room.code not in game_module.room_timers
    assert room.code not in game_module.timer_tasks

    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room.code
    broadcast_data = broadcast_call_args[1]
    assert broadcast_data["type"] == "game_finished"
    assert broadcast_data["message"] == "Игра завершена!"
    assert (
        broadcast_data["winner"] == players[0].id
        or broadcast_data["winner"] == players[1].id
    )
    mock_send_state.assert_not_called()

    if room.code in game_module.room_timers:
        del game_module.room_timers[room.code]
    if room.code in game_module.timer_tasks:
        del game_module.timer_tasks[room.code]


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.get_next_word")
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
@patch("app.api.endpoints.game.time.time")
@patch("app.api.endpoints.game.asyncio.create_task")
@patch("app.api.endpoints.game.start_round_timer", new_callable=AsyncMock)
async def test_end_turn_success(
    mock_start_timer,
    mock_create_task,
    mock_time,
    mock_send_state,
    mock_get_next_word,
    mock_broadcast,
    client,
    setup_users_rooms,
):
    """Тест успешного завершения хода объясняющим игроком."""
    db = setup_users_rooms["db"]
    room_code = setup_users_rooms["room"].code
    player1_id = setup_users_rooms["players"][0].id
    player2_id = setup_users_rooms["players"][1].id
    word = setup_users_rooms["word"]
    token_explainer = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token_explainer}"}

    room_setup = db.scalar(select(Room).where(Room.code == room_code))
    player1_setup = db.get(Player, player1_id)
    player2_setup = db.get(Player, player2_id)
    room_setup.status = GameStatus.PLAYING
    room_setup.current_round = 1
    player1_setup.role = PlayerRole.EXPLAINING
    player2_setup.role = PlayerRole.GUESSING
    db.commit()

    start_time = 1000.0
    mock_time.return_value = start_time
    mock_next_word_data = {
        "id": word.id + 1,
        "word": "NextWordEndTurn",
        "associations": [],
    }
    next_word_db = WordWithAssociations(
        id=mock_next_word_data["id"],
        word=mock_next_word_data["word"],
        category="TestCat3",
        difficulty=DifficultyEnum.basic,
    )
    db.add(next_word_db)
    db.commit()
    mock_get_next_word.return_value = mock_next_word_data
    mock_timer_task = MagicMock()
    mock_create_task.return_value = mock_timer_task

    response = client.post(f"/api/game/{room_code}/end-turn", headers=headers)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["message"] == "Ход успешно завершен"

    room_after = db.scalar(select(Room).where(Room.code == room_code))
    player1_after = db.get(Player, player1_id)
    player2_after = db.get(Player, player2_id)
    assert room_after.current_round == 2
    assert room_after.current_word_id == mock_next_word_data["id"]
    assert player1_after.role == PlayerRole.GUESSING
    assert player2_after.role == PlayerRole.EXPLAINING

    assert room_code in game_module.room_timers
    assert game_module.room_timers[room_code]["start_time"] == start_time
    mock_create_task.assert_called_once()
    assert game_module.timer_tasks[room_code] == mock_timer_task

    mock_send_state.assert_called_once()
    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room_code
    assert broadcast_call_args[1]["type"] == "turn_changed"
    assert broadcast_call_args[1]["current_player"] == str(player2_id)

    if room_code in game_module.room_timers:
        del game_module.room_timers[room_code]
    if room_code in game_module.timer_tasks:
        del game_module.timer_tasks[room_code]


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.asyncio.create_task")
@patch("app.api.endpoints.game.start_round_timer", new_callable=AsyncMock)
async def test_end_turn_game_finish(
    mock_start_timer, mock_create_task, mock_broadcast, client, setup_users_rooms
):
    """Тест завершения хода, приводящего к завершению игры."""
    db = setup_users_rooms["db"]
    room_code = setup_users_rooms["room"].code
    player1_id = setup_users_rooms["players"][0].id
    player2_id = setup_users_rooms["players"][1].id
    token_explainer = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token_explainer}"}

    room_setup = db.scalar(select(Room).where(Room.code == room_code))
    player1_setup = db.get(Player, player1_id)
    player2_setup = db.get(Player, player2_id)
    room_setup.status = GameStatus.PLAYING
    room_setup.current_round = room_setup.rounds_total
    player1_setup.role = PlayerRole.EXPLAINING
    player1_setup.score = 10
    player1_setup.score_total = 5
    player2_setup.role = PlayerRole.GUESSING
    player2_setup.score = 5
    player2_setup.score_total = 15
    db.commit()

    response = client.post(f"/api/game/{room_setup.code}/end-turn", headers=headers)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["message"] == "Игра завершена!"

    room_after = db.scalar(select(Room).where(Room.code == room_code))
    player1_after = db.get(Player, player1_id)
    player2_after = db.get(Player, player2_id)
    assert room_after.status == GameStatus.WAITING
    assert room_after.current_round == 0
    assert player1_after.role == PlayerRole.WAITING
    assert player2_after.role == PlayerRole.WAITING
    assert player1_after.score == 0
    assert player2_after.score == 0
    assert player1_after.score_total == 15
    assert player2_after.score_total == 20

    assert room_code not in game_module.room_timers
    assert room_code not in game_module.timer_tasks

    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room_after.code
    assert broadcast_call_args[1]["type"] == "game_finished"
    assert broadcast_call_args[1]["winner"] == player2_id
    mock_create_task.assert_not_called()


def test_end_turn_not_explainer(client, setup_users_rooms):
    """Тест попытки завершить ход не объясняющим игроком."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    players = setup_users_rooms["players"]
    token_guesser = setup_users_rooms["tokens"][1]
    headers = {"Authorization": f"Bearer {token_guesser}"}

    room.status = GameStatus.PLAYING
    players[0].role = PlayerRole.EXPLAINING
    players[1].role = PlayerRole.GUESSING
    db.commit()

    response = client.post(f"/api/game/{room.code}/end-turn", headers=headers)

    assert response.status_code == 403
    assert "Только текущий объясняющий игрок" in response.json()["detail"]


def test_end_turn_game_not_playing(client, setup_users_rooms):
    """Тест попытки завершить ход, когда игра не идет."""
    room = setup_users_rooms["room"]
    token_explainer = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token_explainer}"}

    response = client.post(f"/api/game/{room.code}/end-turn", headers=headers)

    assert response.status_code == 400
    assert "Игра не запущена" in response.json()["detail"]


def test_end_turn_room_not_found(client, setup_users_rooms):
    """Тест завершения хода для несуществующей комнаты."""
    token = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/game/NOROOM/end-turn", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
async def test_leave_game_guesser_success(
    mock_send_state, mock_broadcast, client, setup_users_rooms
):
    """Тест выхода угадывающего игрока, когда остается один (игра завершается)."""
    db = setup_users_rooms["db"]
    room_code = setup_users_rooms["room"].code
    player1_id = setup_users_rooms["players"][0].id
    player2_id = setup_users_rooms["players"][1].id
    user2_name = setup_users_rooms["users"][1].name
    token_guesser = setup_users_rooms["tokens"][1]
    headers = {"Authorization": f"Bearer {token_guesser}"}

    room_setup = db.scalar(select(Room).where(Room.code == room_code))
    player1_setup = db.get(Player, player1_id)
    player2_setup = db.get(Player, player2_id)
    room_setup.status = GameStatus.PLAYING
    player1_setup.role = PlayerRole.EXPLAINING
    player2_setup.role = PlayerRole.GUESSING
    db.commit()

    response = client.post(f"/api/game/{room_code}/leave", headers=headers)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["message"] == "Вы успешно покинули игру"

    room_after = db.scalar(select(Room).where(Room.code == room_code))
    player1_after = db.get(Player, player1_id)
    player2_after = db.get(Player, player2_id)

    assert player2_after is None
    assert player1_after is None
    assert room_after is None

    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room_code
    assert broadcast_call_args[1]["type"] == "player_left"
    assert broadcast_call_args[1]["player_id"] == player2_id
    assert broadcast_call_args[1]["message"] == f"Игрок {user2_name} покинул игру"

    mock_send_state.assert_called_once_with(room_code, db)


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
async def test_leave_game_explainer_success(
    mock_send_state, mock_broadcast, client, setup_users_rooms
):
    """Тест успешного выхода объясняющего игрока из игры (игра продолжается)."""
    db = setup_users_rooms["db"]
    room_code = setup_users_rooms["room"].code
    player1_id = setup_users_rooms["players"][0].id
    player2_id = setup_users_rooms["players"][1].id
    user1_name = setup_users_rooms["users"][0].name
    token_explainer = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token_explainer}"}

    user3 = User(
        name="GameUser3",
        email="gu3@example.com",
        hashed_password=get_password_hash("pass3"),
    )
    db.add(user3)
    db.commit()
    db.refresh(user3)
    player3 = Player(
        user_id=user3.id, room_id=setup_users_rooms["room"].id, role=PlayerRole.GUESSING
    )
    db.add(player3)
    db.commit()
    db.refresh(player3)
    player3_id = player3.id

    room_setup = db.scalar(select(Room).where(Room.code == room_code))
    player1_setup = db.get(Player, player1_id)
    player2_setup = db.get(Player, player2_id)
    room_setup.status = GameStatus.PLAYING
    player1_setup.role = PlayerRole.EXPLAINING
    player2_setup.role = PlayerRole.GUESSING
    db.commit()

    response = client.post(f"/api/game/{room_code}/leave", headers=headers)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["message"] == "Вы успешно покинули игру"

    room_after = db.scalar(select(Room).where(Room.code == room_code))
    player1_after = db.get(Player, player1_id)
    player2_after = db.get(Player, player2_id)
    player3_after = db.get(Player, player3_id)

    assert player1_after is None
    assert player2_after is not None
    assert player3_after is not None
    assert room_after is not None
    assert room_after.status == GameStatus.PLAYING
    assert player2_after.role == PlayerRole.EXPLAINING
    assert player3_after.role == PlayerRole.GUESSING

    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room_code
    assert broadcast_call_args[1]["type"] == "player_left"
    assert broadcast_call_args[1]["player_id"] == player1_id
    assert broadcast_call_args[1]["message"] == f"Игрок {user1_name} покинул игру"

    mock_send_state.assert_called_once_with(room_code, db)


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
async def test_leave_game_last_player_ends_game(
    mock_send_state, mock_broadcast, client, setup_users_rooms
):
    """Тест выхода игрока, когда остается один, что приводит к удалению комнаты."""
    db = setup_users_rooms["db"]
    room_code = setup_users_rooms["room"].code
    player1_id = setup_users_rooms["players"][0].id
    player2_id = setup_users_rooms["players"][1].id
    user2_name = setup_users_rooms["users"][1].name
    token_guesser = setup_users_rooms["tokens"][1]
    headers = {"Authorization": f"Bearer {token_guesser}"}

    room_setup = db.scalar(select(Room).where(Room.code == room_code))
    player1_setup = db.get(Player, player1_id)
    player2_setup = db.get(Player, player2_id)
    room_setup.status = GameStatus.PLAYING
    player1_setup.role = PlayerRole.EXPLAINING
    player1_setup.score = 5
    player2_setup.role = PlayerRole.GUESSING
    player2_setup.score = 10
    db.commit()

    response = client.post(f"/api/game/{room_code}/leave", headers=headers)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["message"] == "Вы успешно покинули игру"

    room_after = db.scalar(select(Room).where(Room.code == room_code))
    player1_after = db.get(Player, player1_id)
    player2_after = db.get(Player, player2_id)

    assert player2_after is None
    assert player1_after is None
    assert room_after is None

    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room_code
    assert broadcast_call_args[1]["type"] == "player_left"
    assert broadcast_call_args[1]["player_id"] == player2_id
    assert broadcast_call_args[1]["message"] == f"Игрок {user2_name} покинул игру"

    mock_send_state.assert_called_once_with(room_code, db)


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
async def test_leave_game_creator_waiting_room(
    mock_send_state, mock_broadcast, client, setup_users_rooms
):
    """Тест выхода создателя из комнаты ожидания (комната удаляется)."""
    db = setup_users_rooms["db"]
    room_code = setup_users_rooms["room"].code
    player1_id = setup_users_rooms["players"][0].id
    player2_id = setup_users_rooms["players"][1].id
    user1_name = setup_users_rooms["users"][0].name
    token_creator = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token_creator}"}

    room_setup = db.scalar(select(Room).where(Room.code == room_code))
    room_setup.status = GameStatus.WAITING
    db.commit()

    response = client.post(f"/api/game/{room_code}/leave", headers=headers)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["message"] == "Вы успешно покинули игру"

    room_after= db.scalar(select(Room).where(Room.code == room_code))
    player1_after = db.get(Player, player1_id)
    player2_after = db.get(Player, player2_id)

    assert player1_after is None
    assert player2_after is None
    assert room_after is None

    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room_code
    assert broadcast_call_args[1]["type"] == "player_left"
    assert broadcast_call_args[1]["player_id"] == player1_id
    assert broadcast_call_args[1]["message"] == f"Игрок {user1_name} покинул игру"

    mock_send_state.assert_not_called()


@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
def test_leave_game_player_not_in_room(
    mock_send_state, mock_broadcast, client, test_db: Session, setup_users_rooms
):
    """Тест выхода пользователя, который не в комнате."""
    room_code = setup_users_rooms["room"].code
    user_other = User(
        name="OtherUserLeave",
        email="otherleave@example.com",
        hashed_password=get_password_hash("pass"),
    )
    test_db.add(user_other)
    test_db.commit()
    test_db.refresh(user_other)
    token_other = create_access_token(data={"sub": user_other.email})
    headers = {"Authorization": f"Bearer {token_other}"}

    response = client.post(f"/api/game/{room_code}/leave", headers=headers)
    assert response.status_code == 404
    assert "Вы не являетесь участником этой комнаты" in response.json()["detail"]
    mock_broadcast.assert_not_called()
    mock_send_state.assert_not_called()


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
@patch("app.api.endpoints.game.get_next_word")
@patch("app.api.endpoints.game.start_round_timer", new_callable=AsyncMock)
@patch("app.api.endpoints.game.asyncio.create_task")
@patch("app.api.endpoints.game.time.time")
async def test_submit_guess_correct_next_round(
    mock_time,
    mock_create_task,
    mock_start_timer,
    mock_get_next_word,
    mock_send_state,
    mock_broadcast,
    client,
    setup_users_rooms,
):
    """Тест правильной догадки, переход к следующему раунду."""
    db = setup_users_rooms["db"]
    room_code = setup_users_rooms["room"].code
    player1_id = setup_users_rooms["players"][0].id
    player2_id = setup_users_rooms["players"][1].id
    user2_name = setup_users_rooms["users"][1].name
    word_id = setup_users_rooms["word"].id
    word_text = setup_users_rooms["word"].word
    token_guesser = setup_users_rooms["tokens"][1]
    headers = {"Authorization": f"Bearer {token_guesser}"}

    room_setup = db.scalar(select(Room).where(Room.code == room_code))
    player1_setup = db.get(Player, player1_id)
    player2_setup = db.get(Player, player2_id)
    room_setup.status = GameStatus.PLAYING
    room_setup.current_round = 1
    room_setup.current_word_id = word_id
    player1_setup.role = PlayerRole.EXPLAINING
    player1_setup.score = 0
    player2_setup.role = PlayerRole.GUESSING
    player2_setup.score = 0
    db.commit()

    start_time = 1000.0
    mock_time.return_value = start_time
    mock_next_word_data = {
        "id": word_id + 1,
        "word": "NextGuessWord",
        "associations": [],
    }
    next_word_db = WordWithAssociations(
        id=mock_next_word_data["id"],
        word=mock_next_word_data["word"],
        category="TestCatGuess",
        difficulty=DifficultyEnum.basic,
    )
    db.add(next_word_db)
    db.commit()
    mock_get_next_word.return_value = mock_next_word_data
    mock_timer_task = MagicMock()
    mock_create_task.return_value = mock_timer_task

    guess_payload = {"guess": f" {word_text.upper()} "}

    response = client.post(
        f"/api/game/{room_code}/guess", headers=headers, json=guess_payload
    )

    assert response.status_code == 200
    resp_json = response.json()
    assert resp_json["correct"] is True
    assert "Поздравляем! Вы угадали слово." in resp_json["message"]

    room_after = db.scalar(select(Room).where(Room.code == room_code))
    player1_after = db.get(Player, player1_id)
    player2_after = db.get(Player, player2_id)

    assert room_after.current_round == 2
    assert room_after.current_word_id == mock_next_word_data["id"]
    assert player1_after.role == PlayerRole.GUESSING
    assert player2_after.role == PlayerRole.EXPLAINING
    assert player1_after.score == 5
    assert player2_after.score == 10
    assert player2_after.correct_answers == 1

    assert room_code in game_module.room_timers
    assert game_module.room_timers[room_code]["start_time"] == start_time
    mock_create_task.assert_called_once()
    assert game_module.timer_tasks[room_code] == mock_timer_task

    mock_send_state.assert_called_once_with(room_code, db)
    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room_code
    broadcast_data = broadcast_call_args[1]
    assert broadcast_data["type"] == "correct_guess"
    assert broadcast_data["player_id"] == player2_id
    assert broadcast_data["word"] == word_text
    assert (
        broadcast_data["message"]
        == f"Игрок {user2_name} правильно угадал слово: {word_text}"
    )


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
async def test_submit_guess_correct_last_round_finish(
    mock_send_state, mock_broadcast, client, setup_users_rooms
):
    """Тест правильной догадки в последнем раунде, завершение игры."""
    db = setup_users_rooms["db"]
    room_code = setup_users_rooms["room"].code
    player1_id = setup_users_rooms["players"][0].id
    player2_id = setup_users_rooms["players"][1].id
    word_id = setup_users_rooms["word"].id
    word_text = setup_users_rooms["word"].word
    token_guesser = setup_users_rooms["tokens"][1]
    headers = {"Authorization": f"Bearer {token_guesser}"}

    room_setup = db.scalar(select(Room).where(Room.code == room_code))
    player1_setup = db.get(Player, player1_id)
    player2_setup = db.get(Player, player2_id)
    room_setup.status = GameStatus.PLAYING
    room_setup.current_round = room_setup.rounds_total
    room_setup.current_word_id = word_id
    player1_setup.role = PlayerRole.EXPLAINING
    player1_setup.score = 5
    player1_setup.score_total = 10
    player2_setup.role = PlayerRole.GUESSING
    player2_setup.score = 10
    player2_setup.score_total = 5
    db.commit()

    guess_payload = {"guess": word_text}

    response = client.post(
        f"/api/game/{room_code}/guess", headers=headers, json=guess_payload
    )

    assert response.status_code == 200
    resp_json = response.json()
    assert resp_json["correct"] is True
    assert "Игра завершена!" in resp_json["message"]

    room_after = db.scalar(select(Room).where(Room.code == room_code))
    player1_after = db.get(Player, player1_id)
    player2_after = db.get(Player, player2_id)

    assert room_after.status == GameStatus.WAITING
    assert room_after.current_round == 0
    assert player1_after.role == PlayerRole.WAITING
    assert player2_after.role == PlayerRole.WAITING
    assert player1_after.score == 0
    assert player2_after.score == 0
    assert player1_after.score_total == 20
    assert player2_after.score_total == 25

    assert room_code not in game_module.room_timers
    assert room_code not in game_module.timer_tasks

    mock_send_state.assert_not_called()
    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room_code
    broadcast_data = broadcast_call_args[1]
    assert broadcast_data["type"] == "game_finished"
    assert broadcast_data["winner"] == player2_id


def test_submit_guess_not_guesser(client, setup_users_rooms):
    """Тест попытки угадать объясняющим игроком."""
    db = setup_users_rooms["db"]
    room_code = setup_users_rooms["room"].code
    player1_id = setup_users_rooms["players"][0].id
    word_id = setup_users_rooms["word"].id
    token_explainer = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token_explainer}"}

    room_setup = db.scalar(select(Room).where(Room.code == room_code))
    player1_setup = db.get(Player, player1_id)
    room_setup.status = GameStatus.PLAYING
    room_setup.current_word_id = word_id
    player1_setup.role = PlayerRole.EXPLAINING
    db.commit()

    guess_payload = {"guess": "any_guess"}
    response = client.post(
        f"/api/game/{room_code}/guess", headers=headers, json=guess_payload
    )

    assert response.status_code == 400
    assert "Только угадывающие игроки" in response.json()["detail"]


def test_submit_guess_game_not_playing(client, setup_users_rooms):
    """Тест попытки угадать, когда игра не идет."""
    db = setup_users_rooms["db"]
    room_code = setup_users_rooms["room"].code
    token_guesser = setup_users_rooms["tokens"][1]
    headers = {"Authorization": f"Bearer {token_guesser}"}

    guess_payload = {"guess": "any_guess"}
    response = client.post(
        f"/api/game/{room_code}/guess", headers=headers, json=guess_payload
    )

    assert response.status_code == 400
    assert "Игра не запущена" in response.json()["detail"]


def test_submit_guess_room_not_found(client, setup_users_rooms):
    """Тест попытки угадать в несуществующей комнате."""
    token = setup_users_rooms["tokens"][0]
    headers = {"Authorization": f"Bearer {token}"}
    guess_payload = {"guess": "any_guess"}
    response = client.post(
        "/api/game/NOROOM/guess", headers=headers, json=guess_payload
    )
    assert response.status_code == 404


def test_submit_guess_player_not_in_room(client, test_db: Session, setup_users_rooms):
    """Тест попытки угадать пользователем не из комнаты."""
    room_code = setup_users_rooms["room"].code
    user_other = User(
        name="OtherUserGuess",
        email="otherguess@example.com",
        hashed_password=get_password_hash("pass"),
    )
    test_db.add(user_other)
    test_db.commit()
    test_db.refresh(user_other)
    token_other = create_access_token(data={"sub": user_other.email})
    headers = {"Authorization": f"Bearer {token_other}"}

    db = setup_users_rooms["db"]
    room_setup = db.scalar(select(Room).where(Room.code == room_code))
    room_setup.status = GameStatus.PLAYING
    db.commit()

    guess_payload = {"guess": "any_guess"}
    response = client.post(
        f"/api/game/{room_code}/guess", headers=headers, json=guess_payload
    )
    assert response.status_code == 404
    assert "Вы не являетесь участником этой комнаты" in response.json()["detail"]


def test_submit_guess_no_current_word(client, setup_users_rooms):
    """Тест попытки угадать, когда нет текущего слова."""
    db = setup_users_rooms["db"]
    room_code = setup_users_rooms["room"].code
    player1_id = setup_users_rooms["players"][0].id
    player2_id = setup_users_rooms["players"][1].id
    token_guesser = setup_users_rooms["tokens"][1]
    headers = {"Authorization": f"Bearer {token_guesser}"}

    room_setup = db.scalar(select(Room).where(Room.code == room_code))
    player1_setup = db.get(Player, player1_id)
    player2_setup = db.get(Player, player2_id)
    room_setup.status = GameStatus.PLAYING
    room_setup.current_word_id = None
    player1_setup.role = PlayerRole.EXPLAINING
    player2_setup.role = PlayerRole.GUESSING
    db.commit()

    guess_payload = {"guess": "any_guess"}
    response = client.post(
        f"/api/game/{room_code}/guess", headers=headers, json=guess_payload
    )

    assert response.status_code == 400
    assert "В игре нет активного слова" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.manager.send_personal_message", new_callable=AsyncMock)
@patch("app.api.endpoints.game.get_word_by_id_internal")
async def test_send_game_state_update_word_not_found(
    mock_get_word, mock_send_personal, mock_broadcast, setup_users_rooms
):
    """Тест отправки состояния, когда get_word_by_id_internal не находит слово."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    players = setup_users_rooms["players"]

    room.status = GameStatus.PLAYING
    room.current_round = 1
    players[0].role = PlayerRole.EXPLAINING
    players[1].role = PlayerRole.GUESSING
    db.commit()

    mock_get_word.side_effect = HTTPException(
        status_code=404, detail="Слово не найдено"
    )

    start_time = time.time()
    game_module.room_timers[room.code] = {
        "start_time": start_time,
        "duration": room.time_per_round,
    }

    await send_game_state_update(room.code, db)

    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room.code
    broadcast_data = broadcast_call_args[1]
    assert broadcast_data["type"] == "game_state_update"
    assert broadcast_data["game_state"]["currentWord"] == ""

    mock_send_personal.assert_not_called()

    if room.code in game_module.room_timers:
        del game_module.room_timers[room.code]


@pytest.mark.asyncio
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.manager.send_personal_message", new_callable=AsyncMock)
@patch("app.api.endpoints.game.time.time")
async def test_send_game_state_update_timer_missing(
    mock_time, mock_send_personal, mock_broadcast, setup_users_rooms
):
    """Тест отправки состояния, когда таймер отсутствует в room_timers при статусе PLAYING."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    players = setup_users_rooms["players"]
    word = setup_users_rooms["word"]
    user1 = setup_users_rooms["users"][0]

    room.status = GameStatus.PLAYING
    room.current_round = 1
    players[0].role = PlayerRole.EXPLAINING
    players[1].role = PlayerRole.GUESSING
    db.commit()

    if room.code in game_module.room_timers:
        del game_module.room_timers[room.code]

    current_time = 1000.0
    mock_time.return_value = current_time

    await send_game_state_update(room.code, db)

    mock_broadcast.assert_called_once()
    broadcast_call_args = mock_broadcast.call_args[0]
    assert broadcast_call_args[0] == room.code
    broadcast_data = broadcast_call_args[1]
    assert broadcast_data["type"] == "game_state_update"
    assert broadcast_data["game_state"]["timeLeft"] == room.time_per_round

    mock_send_personal.assert_called_once()
    personal_call_args = mock_send_personal.call_args[0]
    assert personal_call_args[0] == str(user1.id)
    personal_data = personal_call_args[1]
    assert personal_data["type"] == "game_state_update"
    assert personal_data["game_state"]["timeLeft"] == room.time_per_round
    assert personal_data["game_state"]["currentWord"] == word.word

    if room.code in game_module.room_timers:
        del game_module.room_timers[room.code]


@pytest.mark.asyncio
@patch("app.api.endpoints.game.asyncio.sleep", new_callable=AsyncMock)
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
@patch("app.api.endpoints.game.asyncio.create_task", new_callable=AsyncMock)
async def test_start_round_timer_cancelled_room_deleted(
    mock_create_task, mock_send_state, mock_broadcast, mock_sleep, setup_users_rooms
):
    """Тест отмены таймера, если комната удалена во время ожидания."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    room_code = room.code
    players = setup_users_rooms["players"]

    room.status = GameStatus.PLAYING
    room.current_round = 1
    players[0].role = PlayerRole.EXPLAINING
    players[1].role = PlayerRole.GUESSING
    db.commit()

    duration = room.time_per_round
    start_time = time.time()
    game_module.room_timers[room_code] = {
        "start_time": start_time,
        "duration": duration,
    }
    game_module.timer_tasks[room_code] = MagicMock()

    async def sleep_side_effect(delay):
        await original_asyncio_sleep(0.01)
        room_to_delete = db.scalar(select(Room).where(Room.code == room_code))
        if room_to_delete:
            players_to_delete = db.scalars(select(Player).where(Player.room_id == room_to_delete.id)).all()
            for p in players_to_delete:
                db.delete(p)
            db.delete(room_to_delete)
            db.commit()

    mock_sleep.side_effect = sleep_side_effect

    await start_round_timer(room_code, duration, db)

    mock_sleep.assert_called_once_with(duration)

    mock_broadcast.assert_not_called()
    mock_send_state.assert_not_called()
    mock_create_task.assert_not_called()

    assert room_code not in game_module.room_timers
    assert room_code not in game_module.timer_tasks


@pytest.mark.asyncio
@patch("app.api.endpoints.game.asyncio.sleep", new_callable=AsyncMock)
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
@patch("app.api.endpoints.game.asyncio.create_task", new_callable=AsyncMock)
async def test_start_round_timer_cancelled_status_changed(
    mock_create_task, mock_send_state, mock_broadcast, mock_sleep, setup_users_rooms
):
    """Тест отмены таймера, если статус комнаты изменился во время ожидания."""
    db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    players = setup_users_rooms["players"]

    room.status = GameStatus.PLAYING
    room.current_round = 1
    players[0].role = PlayerRole.EXPLAINING
    players[1].role = PlayerRole.GUESSING
    db.commit()

    duration = room.time_per_round
    start_time = time.time()
    game_module.room_timers[room.code] = {
        "start_time": start_time,
        "duration": duration,
    }
    game_module.timer_tasks[room.code] = MagicMock()

    async def sleep_side_effect(delay):
        await original_asyncio_sleep(0.01)
        room_to_update = db.scalar(select(Room).where(Room.code == room.code))
        if room_to_update:
            room_to_update.status = GameStatus.WAITING
            db.commit()

    mock_sleep.side_effect = sleep_side_effect

    await start_round_timer(room.code, duration, db)

    mock_sleep.assert_called_once_with(duration)

    db.refresh(room)
    assert room.status == GameStatus.WAITING

    mock_broadcast.assert_not_called()
    mock_send_state.assert_not_called()
    mock_create_task.assert_not_called()

    assert room.code not in game_module.room_timers
    assert room.code not in game_module.timer_tasks


@pytest.mark.asyncio
@patch("app.api.endpoints.game.asyncio.sleep", new_callable=AsyncMock)
@patch("app.api.endpoints.game.manager.broadcast", new_callable=AsyncMock)
@patch("app.api.endpoints.game.send_game_state_update", new_callable=AsyncMock)
@patch("app.api.endpoints.game.asyncio.create_task", new_callable=AsyncMock)
async def test_start_round_timer_current_player_not_found(
    mock_create_task, mock_send_state, mock_broadcast, mock_sleep, setup_users_rooms
):
    """Тест случая, когда текущий объясняющий игрок не найден после sleep."""
    real_db = setup_users_rooms["db"]
    room = setup_users_rooms["room"]
    players = setup_users_rooms["players"]

    room.status = GameStatus.PLAYING
    room.current_round = 1
    players[0].role = PlayerRole.EXPLAINING
    players[1].role = PlayerRole.GUESSING
    real_db.commit()

    duration = room.time_per_round
    start_time = time.time()
    game_module.room_timers[room.code] = {
        "start_time": start_time,
        "duration": duration,
    }
    game_module.timer_tasks[room.code] = MagicMock()

    mock_db = MagicMock(spec=Session)

    def scalar_side_effect(stmt):
        if hasattr(stmt, "columns_clause") and hasattr(stmt, "whereclause"):
            from sqlalchemy import inspect
            entities = [c for c in stmt.columns_clause]
            if any(getattr(e, "class_", None) == Room for e in entities):
                return room
            if any(getattr(e, "class_", None) == Player for e in entities):
                return None
        try:
            from sqlalchemy.sql.selectable import Select
            if isinstance(stmt, Select):
                entities = stmt._raw_columns
                if any(getattr(e, "class_", None) == Room for e in entities):
                    return room
                if any(getattr(e, "class_", None) == Player for e in entities):
                    return None
        except ImportError:
            pass
        return None

    mock_db.scalar.side_effect = scalar_side_effect
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()
    mock_db.expire_all = MagicMock()
    mock_db.get = real_db.get

    await start_round_timer(room.code, duration, mock_db)

    mock_sleep.assert_called_once_with(duration)

    mock_broadcast.assert_not_called()
    mock_send_state.assert_not_called()
    mock_create_task.assert_not_called()

    assert room.code not in game_module.room_timers
    assert room.code not in game_module.timer_tasks