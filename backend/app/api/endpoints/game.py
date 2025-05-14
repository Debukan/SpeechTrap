import random
import asyncio
import time
import threading
from fastapi import FastAPI, APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, ORJSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.sql import func
from typing import Dict, Any, List
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.db.deps import get_db
from app.models.word import WordWithAssociations, DifficultyEnum
from app.models.room import Room, GameStatus
from app.models.player import Player, PlayerRole
from app.models.user import User
from app.core.security import get_current_user
from app.api.endpoints.ws import manager
from app.api.endpoints.words import (
    get_random_word,
    get_next_word,
    get_word_by_id_internal,
)

router = APIRouter()

# Словарь для хранения таймеров комнат
room_timers = {}
timer_tasks = {}
# Глобальный замок для доступа к room_timers
timer_lock = threading.RLock()

# Флаги для отслеживания работающих обновлений состояния игры
active_periodic_updates = set()
# Замок для доступа к списку обновлений
updates_lock = threading.RLock()

# Модели для API
class GuessRequest(BaseModel):
    guess: str


class GameStateResponse(BaseModel):
    currentWord: str
    players: List[Dict[str, Any]]
    round: int
    status: str
    timeLeft: int = None
    currentPlayer: str = None
    rounds_total: int


class ChatMessageRequest(BaseModel):
    message: str


# Функция для отправки текущего состояния игры через WebSocket
async def send_game_state_update(room_code: str, db: Session):
    """
    Отправляет актуальное состояние игры всем игрокам через WebSocket.

    Параметры:
    - room_code: Код комнаты
    - db: Сессия базы данных
    """
    room = db.scalar(select(Room).where(Room.code == room_code))
    if not room:
        return

    if room.status != GameStatus.PLAYING:
        return

    db.expire_all()

    current_player = None
    explaining_player = db.scalar(
        select(Player)
        .where(Player.room_id == room.id, Player.role == PlayerRole.EXPLAINING)
    )

    if explaining_player:
        current_player = str(explaining_player.id)

    players = []
    for p in room.players:
        user = db.scalar(select(User).where(User.id == p.user_id))
        if user:
            players.append(
                {
                    "id": str(p.id),
                    "username": user.name,
                    "score": p.score,
                    "role": p.role,
                }
            )

    # Вычисляем оставшееся время под защитой замка
    time_left = None
    current_time = time.time()
    if room.status == GameStatus.PLAYING:
        with timer_lock:
            if room_code in room_timers:
                timer_info = room_timers[room_code]
                elapsed = current_time - timer_info["start_time"]
                total_time = timer_info["duration"]
                time_left = max(0, int(total_time - elapsed))
                if time_left < 1:
                    time_left = 0
            else:
                time_left = room.time_per_round
                room_timers[room_code] = {
                    "start_time": current_time,
                    "duration": room.time_per_round,
                    "end_time": current_time + room.time_per_round,
                }

                if room_code not in timer_tasks or timer_tasks[room_code] is None:
                    timer_task = asyncio.create_task(
                        start_round_timer(room_code, room.time_per_round, db)
                    )
                    timer_tasks[room_code] = timer_task
    elif room.status == GameStatus.WAITING:
        time_left = room.time_per_round

    # Базовое состояние игры без секретного слова
    base_state = {
        "currentWord": "",
        "players": players,
        "round": room.current_round,
        "status": room.status.upper(),
        "timeLeft": time_left,
        "currentPlayer": current_player,
        "rounds_total": room.rounds_total,
        "time_per_round": room.time_per_round,
    }

    # Отправляем сообщение всем игрокам
    await manager.broadcast(
        room_code, {"type": "game_state_update", "game_state": base_state}
    )

    # Отправляем отдельное сообщение объясняющему игроку с секретным словом
    if explaining_player and room.current_word_id and room.status == GameStatus.PLAYING:
        current_word = None
        associations = []

        if room.current_word_id:
            try:
                word_data = get_word_by_id_internal(room.current_word_id, db)
                if word_data:
                    current_word = word_data["word"]
                    associations = word_data["associations"]
            except HTTPException:
                pass
            except Exception as e:
                pass

        personal_state = base_state.copy()
        personal_state["currentWord"] = current_word
        personal_state["associations"] = associations

        if current_word:
            await manager.send_personal_message(
                str(explaining_player.user_id),
                {"type": "game_state_update", "game_state": personal_state},
            )


# Запуск периодического обновления состояния игры
async def start_periodic_game_state_updates(room_code: str, db: Session):
    """
    Запускает периодическую отправку состояния игры через WebSocket.
    """
    from app.db.deps import get_db
    
    try:
        # Проверяем, что комната существует и игра идет
        db.expire_all()
        room = db.scalar(select(Room).where(Room.code == room_code))
        if not room or room.status != GameStatus.PLAYING:
            with updates_lock:
                if room_code in active_periodic_updates:
                    active_periodic_updates.remove(room_code)
            return
            
        with updates_lock:
            if room_code not in active_periodic_updates:
                active_periodic_updates.add(room_code)
        
        try:
            while True:
                with updates_lock:
                    if room_code not in active_periodic_updates:
                        break
                
                # Получаем новую сессию для каждой итерации
                session_generator = get_db()
                try:
                    session = next(session_generator)
                    
                    # Проверяем статус комнаты
                    room = session.scalar(select(Room).where(Room.code == room_code))
                    if not room or room.status != GameStatus.PLAYING:
                        break
                    
                    # Проверяем, есть ли игроки в комнате
                    players_count = session.scalar(
                        select(func.count(Player.id)).where(Player.room_id == room.id)
                    )
                    if not players_count or players_count < 1:
                        break
                    
                    sleep_time = min(3, max(1, 2 + (players_count - 2) * 0.5))

                    await send_game_state_update(room_code, session)

                finally:
                    session.close()
                    next(session_generator, None)

                # Пауза между обновлениями
                await asyncio.sleep(sleep_time)
        finally:
            with updates_lock:
                if room_code in active_periodic_updates:
                    active_periodic_updates.remove(room_code)
    except Exception as e:
        with updates_lock:
            if room_code in active_periodic_updates:
                active_periodic_updates.remove(room_code)


# Получение состояния игры
@router.get("/{room_code}/state")
async def get_game_state(
    room_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получение текущего состояния игры по коду комнаты.

    Параметры:
    - room_code: Код комнаты.

    Возвращает:
    - Состояние игры: текущее слово, игроки, текущий раунд и т.д.
    """
    room = db.scalar(select(Room).where(Room.code == room_code))
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    player = db.scalar(
        select(Player)
        .where(Player.room_id == room.id, Player.user_id == current_user.id)
    )

    if not player:
        raise HTTPException(
            status_code=403, detail="Вы не являетесь участником этой комнаты"
        )

    # Находим текущее слово, если оно есть
    current_word = ""
    if room.status == GameStatus.PLAYING and room.current_word_id:
        try:
            word_data = get_word_by_id_internal(room.current_word_id, db)
            if word_data and player.role == PlayerRole.EXPLAINING:
                current_word = word_data["word"]
        except HTTPException:
            pass

    current_player = None
    explaining_player = db.scalar(
        select(Player)
        .where(Player.room_id == room.id, Player.role == PlayerRole.EXPLAINING)
    )

    if explaining_player:
        current_player = str(explaining_player.id)

    # Формируем список игроков
    players = []
    for p in room.players:
        user = db.scalar(select(User).where(User.id == p.user_id))
        if user:
            players.append(
                {
                    "id": str(p.id),
                    "username": user.name,
                    "score": p.score,
                    "score_total": p.score_total,
                }
            )

    # Получаем время с блокировкой
    time_left = None
    current_time = time.time()
    if room.status == GameStatus.PLAYING:
        with timer_lock:
            if room_code in room_timers:
                timer_info = room_timers[room_code]
                elapsed = current_time - timer_info["start_time"]
                total_time = timer_info["duration"]
                time_left = max(0, int(total_time - elapsed))
                if time_left < 1:
                    time_left = 0
            else:
                time_left = room.time_per_round
    elif room.status == GameStatus.WAITING:
        time_left = room.time_per_round

    response = {
        "currentWord": current_word,
        "players": players,
        "round": room.current_round,
        "status": room.status.upper(),
        "timeLeft": time_left,
        "currentPlayer": current_player,
        "rounds_total": room.rounds_total,
        "time_per_round": room.time_per_round,
    }

    return response


# Начало игры
@router.post("/{room_code}/start")
async def start_game(
    room_code: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Начинает игру в комнате.

    Параметры:
    - room_code: Код комнаты.

    Возвращает:
    - Сообщение об успешном начале игры или ошибку.
    """
    room = db.scalar(select(Room).where(Room.code == room_code))
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    # Проверяем, что пользователь находится в комнате и является создателем
    if not room.players or len(room.players) == 0:
        raise HTTPException(status_code=400, detail="В комнате нет игроков")

    first_player = room.players[0]
    if first_player.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Только создатель комнаты может начать игру"
        )

    # Проверяем, можно ли начать игру
    if room.status != GameStatus.WAITING:
        raise HTTPException(status_code=400, detail="Игра уже началась или завершена")

    if len(room.players) < 2:
        raise HTTPException(
            status_code=400, detail="Для начала игры нужно минимум 2 игрока"
        )

    # Очищаем все таймеры для этой комнаты перед началом новой игры
    with timer_lock:
        if room_code in room_timers:
            del room_timers[room_code]
        
        if room_code in timer_tasks:
            try:
                timer_tasks[room_code].cancel()
            except Exception:
                pass
            del timer_tasks[room_code]

    # Сбрасываем очки текущей игры
    for player in room.players:
        player.score = 0

    # Выбираем случайное слово из базы
    word_data = get_random_word(difficulty=room.difficulty, db=db)

    if not word_data or "id" not in word_data:
        raise HTTPException(status_code=500, detail="Не удалось выбрать слово для игры")

    # Обновляем состояние комнаты
    room.status = GameStatus.PLAYING
    room.current_round = 1
    room.current_word_id = word_data["id"]

    # Назначаем первого игрока объясняющим
    first_player.role = PlayerRole.EXPLAINING

    # Остальные игроки получают роль угадывающих
    for player in room.players[1:]:
        player.role = PlayerRole.GUESSING

    db.commit()

    # Инициализация таймера для комнаты под защитой блокировки
    with timer_lock:
        current_time = time.time()
        room_timers[room_code] = {
            "start_time": current_time,
            "duration": room.time_per_round,
            "end_time": current_time + room.time_per_round,
        }
        timer_task = asyncio.create_task(
            start_round_timer(room_code, room.time_per_round, db)
        )
        timer_tasks[room_code] = timer_task

    # Запускаем периодические обновления состояния игры через WebSocket
    with updates_lock:
        if room_code not in active_periodic_updates:
            active_periodic_updates.add(room_code)
            try:
                background_tasks.add_task(start_periodic_game_state_updates, room_code, db)
            except Exception as e:
                active_periodic_updates.remove(room_code)

    try:
        await manager.broadcast(
            room_code,
            {
                "type": "game_started",
                "message": "Игра началась!",
                "redirect_to": f"/game/{room_code}",
                "time_per_round": room.time_per_round,
                "timer_start": time.time(),
            },
        )
    except Exception as e:
        pass

    try:
        await send_game_state_update(room_code, db)
    except Exception as e:
        pass

    return {"success": True, "message": "Игра успешно начата"}


# Функция для отсчета времени раунда
async def start_round_timer(room_code: str, duration: int, db: Session):
    """
    Запускает таймер для раунда и обрабатывает его завершение.

    Параметры:
    - room_code: Код комнаты.
    - duration: Продолжительность раунда в секундах.
    - db: Сессия базы данных (используется только для первоначальной проверки).
    """
    from app.db.deps import get_db
    
    try:
        # Ждем необходимое время
        await asyncio.sleep(duration)

        # Проверяем, остался ли этот таймер активным
        with timer_lock:
            if room_code not in timer_tasks or timer_tasks[room_code] != asyncio.current_task():
                return
                
            # Очищаем информацию о таймере перед созданием нового
            if room_code in room_timers:
                del room_timers[room_code]
            if room_code in timer_tasks:
                del timer_tasks[room_code]

        use_existing_db = False
        session = None
        try:
            if db and db.is_active:
                room = db.scalar(select(Room).where(Room.code == room_code))
                if room:
                    use_existing_db = True
                    session = db
        except Exception as e:
            with timer_lock:
                if room_code in room_timers:
                    del room_timers[room_code]
                if room_code in timer_tasks:
                    del timer_tasks[room_code]
            return
            
        if not use_existing_db:
            session_generator = get_db()
            try:
                session = next(session_generator)
            except Exception as e:
                with timer_lock:
                    if room_code in room_timers:
                        del room_timers[room_code]
                    if room_code in timer_tasks:
                        del timer_tasks[room_code]
                return
            
        try:
            room = session.scalar(select(Room).where(Room.code == room_code))
            if not room:
                with timer_lock:
                    if room_code in room_timers:
                        del room_timers[room_code]
                    if room_code in timer_tasks:
                        del timer_tasks[room_code]
                return
            
            if room.status != GameStatus.PLAYING:
                with timer_lock:
                    if room_code in room_timers:
                        del room_timers[room_code]
                    if room_code in timer_tasks:
                        del timer_tasks[room_code]
                return

            # Находим текущего объясняющего игрока
            current_player = session.scalar(
                select(Player)
                .where(Player.room_id == room.id, Player.role == PlayerRole.EXPLAINING)
            )

            if not current_player:
                with timer_lock:
                    if room_code in room_timers:
                        del room_timers[room_code]
                    if room_code in timer_tasks:
                        del timer_tasks[room_code]
                return

            # Меняем роль текущего игрока на угадывающего
            current_player.role = PlayerRole.GUESSING

            # Находим всех игроков в комнате и сортируем их по ID
            players = session.scalars(
                select(Player).where(Player.room_id == room.id).order_by(Player.id)
            ).all()
            
            if not players or len(players) < 2:
                with timer_lock:
                    if room_code in room_timers:
                        del room_timers[room_code]
                    if room_code in timer_tasks:
                        del timer_tasks[room_code]
                return

            # Находим индекс текущего игрока
            try:
                current_index = players.index(current_player)
            except ValueError:
                current_index = 0

            # Определяем следующего игрока
            next_index = (current_index + 1) % len(players)
            next_player = players[next_index]

            # Назначаем следующего игрока объясняющим
            next_player.role = PlayerRole.EXPLAINING

            # Увеличиваем номер раунда
            room.current_round += 1

            # Если достигли максимального числа раундов, завершаем игру
            if room.current_round > room.rounds_total:
                room.status = GameStatus.WAITING
                room.current_round = 0

                for player in players:
                    if player.score_total is None:
                        player.score_total = 0
                    player.score_total += player.score
                    player.score = 0
                    player.role = PlayerRole.WAITING

                winner_id = max(players, key=lambda p: p.score_total).id
                session.commit()

                # Отправляем сообщение о завершении игры
                await manager.broadcast(
                    room_code,
                    {
                        "type": "game_finished",
                        "message": "Игра завершена!",
                        "winner": winner_id,
                    },
                )

                # Останавливаем периодические обновления
                with updates_lock:
                    if room_code in active_periodic_updates:
                        active_periodic_updates.remove(room_code)

                return

            # Выбираем новое слово для следующего раунда
            if room.current_word_id:
                word_data = get_next_word(
                    exclude_id=room.current_word_id, difficulty=room.difficulty, db=session
                )
                if word_data and "id" in word_data:
                    room.current_word_id = word_data["id"]

            session.commit()

            # Обновляем таймер комнаты под защитой блокировки
            with timer_lock:
                current_time = time.time()
                room_timers[room_code] = {
                    "start_time": current_time,
                    "duration": room.time_per_round,
                    "end_time": current_time + room.time_per_round,
                }

                # Отправляем всем сообщение о смене игрока и обновлении таймера
                user = session.scalar(select(User).where(User.id == next_player.user_id))
                user_name = user.name if user else "Неизвестный"
                await manager.broadcast(
                    room_code,
                    {
                        "type": "turn_changed",
                        "message": f"Ход переходит к игроку {user_name}",
                        "current_player": str(next_player.id),
                        "new_timer": True,
                        "timer_start": current_time,
                        "time_per_round": room.time_per_round,
                        "current_round": room.current_round,
                    },
                )

                # Запускаем новый таймер для следующего раунда
                if room_code in timer_tasks:
                    try:
                        if timer_tasks[room_code] != asyncio.current_task():
                            timer_tasks[room_code].cancel()
                    except Exception as e:
                        pass
                
                timer_task = asyncio.create_task(
                    start_round_timer(room_code, room.time_per_round, session)
                )
                timer_tasks[room_code] = timer_task

            await send_game_state_update(room_code, session)
        finally:
            if not use_existing_db and session:
                try:
                    session.close()
                    next(session_generator, None)
                except Exception as e:
                    pass
    except asyncio.CancelledError:
        with timer_lock:
            if room_code in room_timers:
                del room_timers[room_code]
            if room_code in timer_tasks:
                if timer_tasks[room_code] == asyncio.current_task():
                    del timer_tasks[room_code]
    except Exception as e:
        with timer_lock:
            if room_code in room_timers:
                del room_timers[room_code]
            if room_code in timer_tasks:
                if timer_tasks[room_code] == asyncio.current_task():
                    del timer_tasks[room_code]


# Завершение хода
@router.post("/{room_code}/end-turn")
async def end_turn(
    room_code: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Завершает текущий ход и передает право хода следующему игроку.

    Параметры:
    - room_code: Код комнаты.

    Возвращает:
    - Сообщение об успешном завершении хода или ошибку.
    """
    # Находим комнату по коду
    room = db.scalar(select(Room).where(Room.code == room_code))
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    # Проверяем, что игра идет
    if room.status != GameStatus.PLAYING:
        raise HTTPException(status_code=400, detail="Игра не запущена")

    # Находим текущего объясняющего игрока
    current_player = db.scalar(
        select(Player)
        .where(Player.room_id == room.id, Player.role == PlayerRole.EXPLAINING)
    )

    if not current_player:
        raise HTTPException(status_code=400, detail="Не удалось найти текущего игрока")

    # Проверяем, что запрос отправлен от текущего объясняющего игрока
    if current_player.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Только текущий объясняющий игрок может завершить ход",
        )

    # Меняем роль текущего игрока на угадывающего
    current_player.role = PlayerRole.GUESSING

    # Находим всех игроков в комнате и сортируем их по ID
    players = db.scalars(
        select(Player).where(Player.room_id == room.id).order_by(Player.id)
    ).all()

    # Находим индекс текущего игрока
    current_index = players.index(current_player)

    # Определяем следующего игрока
    next_index = (current_index + 1) % len(players)
    next_player = players[next_index]

    # Назначаем следующего игрока объясняющим
    next_player.role = PlayerRole.EXPLAINING

    next_player_id = next_player.id
    next_user = db.scalar(select(User).where(User.id == next_player.user_id))
    next_player_name = next_user.name if next_user else "Неизвестный"
    room.current_round += 1

    # Если достигли максимального числа раундов, завершаем игру
    if room.current_round > room.rounds_total:
        room.status = GameStatus.WAITING
        room.current_round = 0

        for player in players:
            player.score_total += player.score
            player.score = 0
            player.role = PlayerRole.WAITING

        winner_id = max(players, key=lambda p: p.score_total).id
        db.commit()

        # Отправляем всем сообщение о завершении игры
        async def broadcast_game_finished():
            await manager.broadcast(
                room_code,
                {
                    "type": "game_finished",
                    "message": "Игра завершена!",
                    "winner": winner_id,
                },
            )

        # Очищаем таймеры под защитой блокировки
        with timer_lock:
            if room_code in room_timers:
                del room_timers[room_code]
            if room_code in timer_tasks:
                try:
                    timer_tasks[room_code].cancel()
                except Exception:
                    pass
                del timer_tasks[room_code]

        # Останавливаем периодические обновления
        with updates_lock:
            if room_code in active_periodic_updates:
                active_periodic_updates.remove(room_code)

        background_tasks.add_task(broadcast_game_finished)

        return {"success": True, "message": "Игра завершена!"}

    # Выбираем новое слово для следующего раунда
    if room.current_word_id:
        word_data = get_next_word(
            exclude_id=room.current_word_id, difficulty=room.difficulty, db=db
        )
        if word_data and "id" in word_data:
            room.current_word_id = word_data["id"]

    db.commit()

    # Обновляем таймер комнаты под защитой блокировки
    current_time = time.time()
    with timer_lock:
        # Отменяем предыдущий таймер, если он существует
        if room_code in timer_tasks:
            try:
                timer_tasks[room_code].cancel()
            except Exception:
                pass
                
        # Создаем новый таймер
        room_timers[room_code] = {
            "start_time": current_time,
            "duration": room.time_per_round,
            "end_time": current_time + room.time_per_round,
        }
        
        timer_task = asyncio.create_task(
            start_round_timer(room_code, room.time_per_round, db)
        )
        timer_tasks[room_code] = timer_task

    await send_game_state_update(room_code, db)

    # Отправляем всем сообщение о смене игрока
    async def broadcast_turn_changed(player_id: int, player_name: str):
        await manager.broadcast(
            room_code,
            {
                "type": "turn_changed",
                "message": f"Ход переходит к игроку {player_name}",
                "current_player": str(player_id),
                "new_timer": True,
                "timer_start": current_time,
                "time_per_round": room.time_per_round,
            },
        )

    background_tasks.add_task(broadcast_turn_changed, next_player_id, next_player_name)
    return {"success": True, "message": "Ход успешно завершен"}


# Выход из игры
@router.post("/{room_code}/leave")
async def leave_game(
    room_code: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Позволяет игроку выйти из игры.

    Параметры:
    - room_code: Код комнаты.

    Возвращает:
    - Сообщение об успешном выходе из игры или ошибку.
    """
    # Находим комнату по коду
    room = db.scalar(select(Room).where(Room.code == room_code))
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    # Находим игрока в комнате
    player = db.scalar(
        select(Player)
        .where(Player.room_id == room.id, Player.user_id == current_user.id)
    )

    if not player:
        raise HTTPException(
            status_code=404, detail="Вы не являетесь участником этой комнаты"
        )

    player_id_leaving = player.id
    username = current_user.name
    is_explainer_leaving = (
        player.role == PlayerRole.EXPLAINING and room.status == GameStatus.PLAYING
    )
    is_creator = (
        room.players
        and len(room.players) > 0
        and room.players[0].id == player_id_leaving
    )
    is_waiting_room = room.status == GameStatus.WAITING
    is_creator_leaving_waiting_room = is_creator and is_waiting_room
    room_id = room.id
    initial_player_count = len(room.players)
    next_explainer_id = None

    # Если игрок является объясняющим, нужно передать ход следующему
    if is_explainer_leaving and initial_player_count > 1:
        players = db.scalars(
            select(Player).where(Player.room_id == room.id).order_by(Player.id)
        ).all()
        current_index = -1
        for i, p in enumerate(players):
            if p.id == player_id_leaving:
                current_index = i
                break

        if current_index != -1:
            for i in range(1, len(players)):
                next_idx_candidate = (current_index + i) % len(players)
                if players[next_idx_candidate].id != player_id_leaving:
                    next_explainer_id = players[next_idx_candidate].id
                    break

    # Удаляем игрока из комнаты
    db.delete(player)
    db.commit()

    room_deleted = False
    state_update_sent_sync = False
    remaining_players_count = db.scalars(
        select(Player).where(Player.room_id == room_id)
    ).all()
    remaining_players_count = len(remaining_players_count)
    room_after_leave = db.get(Room, room_id)

    if is_creator_leaving_waiting_room:
        remaining_players_to_delete = db.scalars(
            select(Player).where(Player.room_id == room_id)
        ).all()
        for p in remaining_players_to_delete:
            db.delete(p)
        room_to_delete = db.get(Room, room_id)
        if room_to_delete:
            db.delete(room_to_delete)
        db.commit()
        room_deleted = True
    else:
        if room_after_leave:
            if remaining_players_count == 0:
                db.delete(room_after_leave)
                db.commit()
                room_deleted = True
            elif remaining_players_count == 1:
                if not is_waiting_room:
                    room_check_before_delete = db.get(Room, room_id)
                    if (
                        room_check_before_delete
                        and room_check_before_delete.status == GameStatus.PLAYING
                    ):
                        await send_game_state_update(room_code, db)
                        state_update_sent_sync = True

                last_player = db.scalar(
                    select(Player).where(Player.room_id == room_id)
                )
                if last_player:
                    if not is_waiting_room:
                        if last_player.score_total is None:
                            last_player.score_total = 0
                        last_player.score_total += last_player.score
                    db.delete(last_player)
                db.delete(room_after_leave)
                if room_code in room_timers:
                    del room_timers[room_code]
                if room_code in timer_tasks:
                    try:
                        timer_tasks[room_code].cancel()
                    except Exception:
                        pass
                    del timer_tasks[room_code]
                db.commit()
                room_deleted = True
            elif (
                is_explainer_leaving
                and next_explainer_id is not None
                and room_after_leave.status == GameStatus.PLAYING
            ):
                next_player_obj = db.get(Player, next_explainer_id)
                if next_player_obj:
                    next_player_obj.role = PlayerRole.EXPLAINING
                    db.commit()
                    await send_game_state_update(room_code, db)
                    state_update_sent_sync = True

    # Отправляем всем оставшимся игрокам сообщение о выходе игрока
    async def broadcast_player_left():
        try:
            player_left_message = {
                "type": "player_left",
                "player_id": player_id_leaving,
                "message": f"Игрок {username} покинул игру",
                "timestamp": time.time(),
            }
            await manager.broadcast(room_code, player_left_message)

        except Exception as e:
            pass

    background_tasks.add_task(broadcast_player_left)

    return {"success": True, "message": "Вы успешно покинули игру"}


# Отправка догадки
@router.post("/{room_code}/guess")
async def submit_guess(
    room_code: str,
    guess_data: GuessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Позволяет угадывающему игроку отправить свою догадку.

    Параметры:
    - room_code: Код комнаты.
    - guess_data: Данные догадки (текст догадки).

    Возвращает:
    - Результат проверки догадки.
    """
    room = db.scalar(select(Room).where(Room.code == room_code))
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    # Проверяем, что игра идет
    if room.status != GameStatus.PLAYING:
        raise HTTPException(status_code=400, detail="Игра не запущена")

    # Находим игрока в комнате
    player = db.scalar(
        select(Player)
        .where(Player.room_id == room.id, Player.user_id == current_user.id)
    )

    if not player:
        raise HTTPException(
            status_code=404, detail="Вы не являетесь участником этой комнаты"
        )

    # Проверяем, что игрок не является объясняющим
    if player.role != PlayerRole.GUESSING:
        raise HTTPException(
            status_code=400, detail="Только угадывающие игроки могут отправлять догадки"
        )

    # Находим текущее слово
    if not room.current_word_id:
        raise HTTPException(status_code=400, detail="В игре нет активного слова")

    try:
        word_data = get_word_by_id_internal(room.current_word_id, db)
    except HTTPException:
        raise HTTPException(status_code=500, detail="Не удалось найти текущее слово")

    # Проверяем догадку
    guess = guess_data.guess.lower().strip()
    correct = word_data["word"].lower() == guess

    if correct:
        player.score += 10
        player.correct_answers += 1

        explaining_player = db.scalar(
            select(Player)
            .where(Player.room_id == room.id, Player.role == PlayerRole.EXPLAINING)
        )

        if explaining_player:
            explaining_player.score += 5
            explaining_player.role = PlayerRole.GUESSING

        player.role = PlayerRole.EXPLAINING

        room.current_round += 1

        if room.current_round > room.rounds_total:
            room.status = GameStatus.WAITING
            room.current_round = 0

            for p in room.players:
                p.score_total += p.score
                p.score = 0
                p.role = PlayerRole.WAITING

            winner_id = max(room.players, key=lambda p: p.score_total).id
            db.commit()

            # Отправляем всем сообщение о завершении игры
            async def broadcast_game_finished():
                await manager.broadcast(
                    room_code,
                    {
                        "type": "game_finished",
                        "message": "Игра завершена!",
                        "winner": winner_id,
                    },
                )

            # Очищаем таймеры под защитой блокировки
            with timer_lock:
                if room_code in room_timers:
                    del room_timers[room_code]
                if room_code in timer_tasks:
                    try:
                        timer_tasks[room_code].cancel()
                    except Exception:
                        pass
                    del timer_tasks[room_code]

            # Останавливаем периодические обновления
            with updates_lock:
                if room_code in active_periodic_updates:
                    active_periodic_updates.remove(room_code)

            background_tasks.add_task(broadcast_game_finished)

            return {
                "correct": True,
                "message": "Поздравляем! Вы угадали последнее слово. Игра завершена!",
            }

        # Сохраняем старое слово для сообщения
        old_word = word_data["word"]
        player_id_correct = player.id
        player_name_correct = current_user.name

        # Выбираем новое слово
        if room.current_word_id:
            word_data = get_next_word(
                exclude_id=room.current_word_id, difficulty=room.difficulty, db=db
            )
            if word_data and "id" in word_data:
                room.current_word_id = word_data["id"]

        db.commit()

        # Обновляем таймер комнаты под защитой блокировки
        current_time = time.time()
        with timer_lock:
            # Отменяем предыдущий таймер, если он существует
            if room_code in timer_tasks:
                try:
                    timer_tasks[room_code].cancel()
                except Exception:
                    pass
                    
            # Создаем новый таймер
            room_timers[room_code] = {
                "start_time": current_time,
                "duration": room.time_per_round,
                "end_time": current_time + room.time_per_round,
            }
            
            timer_task = asyncio.create_task(
                start_round_timer(room_code, room.time_per_round, db)
            )
            timer_tasks[room_code] = timer_task

        # Отправляем обновленное состояние игры
        await send_game_state_update(room_code, db)

        # Отправляем всем сообщение о правильной догадке
        async def broadcast_correct_guess(p_id: int, p_name: str, word: str):
            await manager.broadcast(
                room_code,
                {
                    "type": "correct_guess",
                    "player_id": p_id,
                    "word": word,
                    "message": f"Игрок {p_name} правильно угадал слово: {word}",
                    "new_timer": True,
                    "timer_start": current_time,
                    "time_per_round": room.time_per_round,
                },
            )

        background_tasks.add_task(
            broadcast_correct_guess, player_id_correct, player_name_correct, old_word
        )

        return {"correct": True, "message": "Поздравляем! Вы угадали слово."}
    else:
        # Игрок не угадал слово
        player.wrong_answers += 1
        db.commit()

        # Сохраняем необходимые данные до передачи в background task
        player_id = player.id
        player_name = current_user.name
        guess_text = guess

        # Отправляем всем сообщение о неправильной догадке
        async def broadcast_wrong_guess():
            await manager.broadcast(
                room_code,
                {
                    "type": "wrong_guess",
                    "player_id": player_id,
                    "guess": guess_text,
                    "message": f"Игрок {player_name} пытается угадать: {guess_text}",
                },
            )

        background_tasks.add_task(broadcast_wrong_guess)

        return {"correct": False, "message": "Неправильно, попробуйте еще раз."}


@router.post("/{room_code}/chat")
async def send_chat_message(
    room_code: str,
    message_data: ChatMessageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Отправка сообщения в чат игры.

    Параметры:
    - room_code: Код комнаты
    - message_data: Данные сообщения (текст)

    Возвращает:
    - Подтверждение отправки сообщения
    """
    room = db.scalar(select(Room).where(Room.code == room_code))
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    # Проверяем, что пользователь находится в комнате
    player = db.scalar(
        select(Player)
        .where(Player.room_id == room.id, Player.user_id == current_user.id)
    )

    if not player:
        raise HTTPException(
            status_code=403, detail="Вы не являетесь участником этой комнаты"
        )

    chat_message = {
        "type": "chat_message",
        "player_id": str(player.id),
        "player_name": current_user.name,
        "player_role": player.role,
        "message": message_data.message,
        "timestamp": time.time(),
        "is_explaining": player.role == PlayerRole.EXPLAINING,
    }

    # Отправляем сообщение всем игрокам в комнате
    await manager.broadcast(room_code, chat_message)

    return {"success": True, "message": "Сообщение отправлено"}
