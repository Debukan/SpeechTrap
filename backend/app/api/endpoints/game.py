import random
import asyncio
import time
from fastapi import FastAPI, APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, ORJSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Dict, Any, List
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.db.deps import get_db
from app.models.word import WordWithAssociations
from app.models.room import Room, GameStatus
from app.models.player import Player, PlayerRole
from app.models.user import User
from app.core.security import get_current_user
from app.api.endpoints.ws import manager
from app.api.endpoints.words import get_random_word, get_next_word, get_word_by_id

router = APIRouter()

# Словарь для хранения таймеров комнат
room_timers = {}
timer_tasks = {}

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
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        return
    
    if room.status != GameStatus.PLAYING:
        return
    
    db.expire_all()
    
    current_player = None
    explaining_player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.role == PlayerRole.EXPLAINING
    ).first()
    
    if explaining_player:
        current_player = str(explaining_player.id)
    
    players = []
    for p in room.players:
        user = db.query(User).filter(User.id == p.user_id).first()
        if user:
            players.append({
                "id": str(p.id),
                "username": user.name,
                "score": p.score,
                "role": p.role
            })
    
    time_left = None
    if room.status == GameStatus.PLAYING:
        if room_code in room_timers:
            timer_info = room_timers[room_code]
            current_time = time.time()
            elapsed = current_time - timer_info["start_time"]
            total_time = timer_info["duration"]
            time_left = max(0, int(total_time - elapsed))
        else:
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
        "time_per_round": room.time_per_round
    }
    
    # Отправляем сообщение всем игрокам
    await manager.broadcast(
        room_code,
        {
            "type": "game_state_update",
            "game_state": base_state
        }
    )
    
    # Отправляем отдельное сообщение объясняющему игроку с секретным словом
    if explaining_player and room.current_word_id and room.status == GameStatus.PLAYING:
        current_word = None
        associations = []
        
        if room.current_word_id:
            try:
                word_data = get_word_by_id(room.current_word_id, db)
                if word_data:
                    current_word = word_data["word"]
                    associations = word_data["associations"]
            except HTTPException:
                pass
        
        personal_state = base_state.copy()
        personal_state["currentWord"] = current_word
        personal_state["associations"] = associations

        if current_word:
            await manager.send_personal_message(
                str(explaining_player.user_id),
                {
                    "type": "game_state_update",
                    "game_state": personal_state
                }
            )


# Запуск периодического обновления состояния игры
async def start_periodic_game_state_updates(room_code: str, db: Session):
    """
    Запускает периодическую отправку состояния игры через WebSocket.
    """
    try:
        while True:
            db.expire_all()
            room = db.query(Room).filter(Room.code == room_code).first()
            if not room or room.status != GameStatus.PLAYING:
                break
                
            await send_game_state_update(room_code, db)
            
            # Пауза между обновлениями
            await asyncio.sleep(2)
    except Exception as e:
        print(f"Error in periodic game state updates: {e}")


# Получение состояния игры
@router.get("/{room_code}/state")
async def get_game_state(
    room_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение текущего состояния игры по коду комнаты.
    
    Параметры:
    - room_code: Код комнаты.
    
    Возвращает:
    - Состояние игры: текущее слово, игроки, текущий раунд и т.д.
    """
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    
    if not player:
        raise HTTPException(
            status_code=403,
            detail="Вы не являетесь участником этой комнаты"
        )
    
    # Находим текущее слово, если оно есть
    current_word = ""
    if room.status == GameStatus.PLAYING and room.current_word_id:
        try:
            word_data = get_word_by_id(room.current_word_id, db)
            if word_data and player.role == PlayerRole.EXPLAINING:
                current_word = word_data["word"]
        except HTTPException:
            pass
            
    current_player = None
    explaining_player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.role == PlayerRole.EXPLAINING
    ).first()
    
    if explaining_player:
        current_player = str(explaining_player.id)
    
    # Формируем список игроков
    players = []
    for p in room.players:
        user = db.query(User).filter(User.id == p.user_id).first()
        if user:
            players.append({
                "id": str(p.id),
                "username": user.name,
                "score": p.score,
                "score_total": p.score_total
            })
    
    time_left = None
    if room.status == GameStatus.PLAYING:
        if room_code in room_timers:
            timer_info = room_timers[room_code]
            current_time = time.time()
            elapsed = current_time - timer_info["start_time"]
            total_time = timer_info["duration"]
            time_left = max(0, int(total_time - elapsed))
            if time_left < 1:
                time_left = 0
        else:
            time_left = room.time_per_round
            start_time = time.time()
            room_timers[room_code] = {
                "start_time": start_time,
                "duration": room.time_per_round,
                "end_time": start_time + room.time_per_round
            }
    
    response = {
        "currentWord": current_word,
        "players": players,
        "round": room.current_round,
        "status": room.status.upper(),
        "timeLeft": time_left,
        "currentPlayer": current_player,
        "rounds_total": room.rounds_total,
        "time_per_round": room.time_per_round
    }

    
    return response

# Начало игры
@router.post("/{room_code}/start")
async def start_game(
    room_code: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Начинает игру в комнате.
    
    Параметры:
    - room_code: Код комнаты.
    
    Возвращает:
    - Сообщение об успешном начале игры или ошибку.
    """
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    # Проверяем, что пользователь находится в комнате и является создателем
    if not room.players or len(room.players) == 0:
        raise HTTPException(status_code=400, detail="В комнате нет игроков")
        
    first_player = room.players[0]
    if first_player.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Только создатель комнаты может начать игру"
        )
    
    # Проверяем, можно ли начать игру
    if room.status != GameStatus.WAITING:
        raise HTTPException(
            status_code=400,
            detail="Игра уже началась или завершена"
        )
    
    if len(room.players) < 2:
        raise HTTPException(
            status_code=400,
            detail="Для начала игры нужно минимум 2 игрока"
        )
    
    # Сбрасываем очки текущей игры
    for player in room.players:
        player.score = 0

    # Выбираем случайное слово из базы 
    word_data = get_random_word(db)
    
    if not word_data or "id" not in word_data:
        raise HTTPException(
            status_code=500,
            detail="Не удалось выбрать слово для игры"
        )
    
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
    
    # Инициализация таймера для комнаты
    room_timers[room_code] = {
        "start_time": time.time(),
        "duration": room.time_per_round,
        "end_time": time.time() + room.time_per_round
    }
    
    # Запускаем фоновую задачу для отсчета времени
    if room_code in timer_tasks:
        timer_tasks[room_code].cancel()
    timer_task = asyncio.create_task(start_round_timer(room_code, room.time_per_round, db))
    timer_tasks[room_code] = timer_task

    # Запускаем периодические обновления состояния игры через WebSocket
    background_tasks.add_task(start_periodic_game_state_updates, room_code, db)
    
    await manager.broadcast(
                room_code,
                {
                    "type": "game_started", 
                    "message": "Игра началась!",
                    "redirect_to": f"/game/{room_code}",
                    "time_per_round": room.time_per_round,
                    "timer_start": time.time()
                }
            )
    
    await send_game_state_update(room_code, db)
    
    return {"success": True, "message": "Игра успешно начата"}

# Функция для отсчета времени раунда
async def start_round_timer(room_code: str, duration: int, db: Session):
    """
    Запускает таймер для раунда и обрабатывает его завершение.
    
    Параметры:
    - room_code: Код комнаты.
    - duration: Продолжительность раунда в секундах.
    - db: Сессия базы данных.
    """
    try:
        # Ждем необходимое время
        await asyncio.sleep(duration)

        if room_code in room_timers:
            del room_timers[room_code]
        if room_code in timer_tasks:
            del timer_tasks[room_code]
        
        room = db.query(Room).filter(Room.code == room_code).first()
        if not room or room.status != GameStatus.PLAYING:
            if room_code in room_timers:
                del room_timers[room_code]
            if room_code in timer_tasks:
                del timer_tasks[room_code]
            return
        
        # Находим текущего объясняющего игрока
        current_player = db.query(Player).filter(
            Player.room_id == room.id,
            Player.role == PlayerRole.EXPLAINING
        ).first()
        
        if not current_player:
            return
        
        # Меняем роль текущего игрока на угадывающего
        current_player.role = PlayerRole.GUESSING
        
        # Находим всех игроков в комнате и сортируем их по ID
        players = db.query(Player).filter(
            Player.room_id == room.id
        ).order_by(Player.id).all()
        
        # Находим индекс текущего игрока
        current_index = players.index(current_player)
        
        # Определяем следующего игрока
        next_index = (current_index + 1) % len(players)
        next_player = players[next_index]
        
        # Назначаем следующего игрока объясняющим
        next_player.role = PlayerRole.EXPLAINING
        
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
            db.commit()
            
            # Отправляем сообщение о завершении игры
            await manager.broadcast(
                room_code,
                {
                    "type": "game_finished",
                    "message": "Игра завершена!",
                    "winner": winner_id
                }
            )
            
            # Удаляем таймер комнаты
            if room_code in room_timers:
                del room_timers[room_code]
            if room_code in timer_tasks:
                del timer_tasks[room_code]
            
            return
        
        # Выбираем новое слово для следующего раунда
        if room.current_word_id:
            word_data = get_next_word(room.current_word_id, db)
            if word_data and "id" in word_data:
                room.current_word_id = word_data["id"]
        
        db.commit()
        
        # Обновляем таймер комнаты
        room_timers[room_code] = {
            "start_time": time.time(),
            "duration": room.time_per_round,
            "end_time": time.time() + room.time_per_round
        }
        
        # Отправляем всем сообщение о смене игрока и обновлении таймера
        user = db.query(User).filter(User.id == next_player.user_id).first()
        await manager.broadcast(
            room_code,
            {
                "type": "turn_changed",
                "message": f"Ход переходит к игроку {user.name if user else 'Неизвестный'}",
                "current_player": str(next_player.id),
                "new_timer": True,
                "timer_start": time.time(),
                "time_per_round": room.time_per_round
            }
        )
        
        # Запускаем новый таймер для следующего раунда
        if room_code in timer_tasks:
            timer_tasks[room_code].cancel()
        timer_task = asyncio.create_task(start_round_timer(room_code, room.time_per_round, db))
        timer_tasks[room_code] = timer_task
        
        await send_game_state_update(room_code, db)
    except asyncio.CancelledError:
        print(f"Timer for room {room_code} was cancelled")
    except Exception as e:
        print(f"Error in timer for room {room_code}: {e}")
        if room_code in room_timers:
                del room_timers[room_code]
        if room_code in timer_tasks:
            del timer_tasks[room_code]

# Завершение хода
@router.post("/{room_code}/end-turn")
async def end_turn(
    room_code: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Завершает текущий ход и передает право хода следующему игроку.
    
    Параметры:
    - room_code: Код комнаты.
    
    Возвращает:
    - Сообщение об успешном завершении хода или ошибку.
    """
    # Находим комнату по коду
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    # Проверяем, что игра идет
    if room.status != GameStatus.PLAYING:
        raise HTTPException(
            status_code=400,
            detail="Игра не запущена"
        )
    
    # Находим текущего объясняющего игрока
    current_player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.role == PlayerRole.EXPLAINING
    ).first()
    
    if not current_player:
        raise HTTPException(
            status_code=400,
            detail="Не удалось найти текущего игрока"
        )
    
    # Проверяем, что запрос отправлен от текущего объясняющего игрока
    if current_player.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Только текущий объясняющий игрок может завершить ход"
        )
    
    # Меняем роль текущего игрока на угадывающего
    current_player.role = PlayerRole.GUESSING
    
    # Находим всех игроков в комнате и сортируем их по ID
    players = db.query(Player).filter(
        Player.room_id == room.id
    ).order_by(Player.id).all()
    
    # Находим индекс текущего игрока
    current_index = players.index(current_player)
    
    # Определяем следующего игрока
    next_index = (current_index + 1) % len(players)
    next_player = players[next_index]
    
    # Назначаем следующего игрока объясняющим
    next_player.role = PlayerRole.EXPLAINING
    
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
                    "winner": winner_id
                }
            )

        if room_code in room_timers:
                del room_timers[room_code]
        if room_code in timer_tasks:
            del timer_tasks[room_code]
        
        background_tasks.add_task(broadcast_game_finished)
        
        return {"success": True, "message": "Игра завершена!"}
    
    # Выбираем новое слово для следующего раунда
    if room.current_word_id:
        word_data = get_next_word(room.current_word_id, db)
        if word_data and "id" in word_data:
            room.current_word_id = word_data["id"]
    
    db.commit()
    
    # Обновляем таймер комнаты
    room_timers[room_code] = {
        "start_time": time.time(),
        "duration": room.time_per_round,
        "end_time": time.time() + room.time_per_round
    }

    await send_game_state_update(room_code, db)
    
    # Отправляем всем сообщение о смене игрока
    async def broadcast_turn_changed():
        user = db.query(User).filter(User.id == next_player.user_id).first()
        await manager.broadcast(
            room_code,
            {
                "type": "turn_changed",
                "message": f"Ход переходит к игроку {user.name if user else 'Неизвестный'}",
                "current_player": str(next_player.id),
                "new_timer": True,
                "timer_start": time.time(),
                "time_per_round": room.time_per_round
            }
        )
    
    background_tasks.add_task(broadcast_turn_changed)
    
    return {"success": True, "message": "Ход успешно завершен"}

# Выход из игры
@router.post("/{room_code}/leave")
async def leave_game(
    room_code: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Позволяет игроку выйти из игры.
    
    Параметры:
    - room_code: Код комнаты.
    
    Возвращает:
    - Сообщение об успешном выходе из игры или ошибку.
    """
    # Находим комнату по коду
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    # Находим игрока в комнате
    player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    
    if not player:
        raise HTTPException(
            status_code=404,
            detail="Вы не являетесь участником этой комнаты"
        )
    
    # Сохраняем необходимые данные перед удалением игрока
    player_id = player.id
    username = current_user.name
    
    # Если игрок является объясняющим, нужно передать ход следующему
    if player.role == PlayerRole.EXPLAINING and room.status == GameStatus.PLAYING:
        players = db.query(Player).filter(
            Player.room_id == room.id
        ).order_by(Player.id).all()
        
        current_index = players.index(player)
        next_index = (current_index + 1) % len(players)
        
        # Если есть другие игроки, передаем ход
        if len(players) > 1:
            next_player = players[next_index]
            next_player.role = PlayerRole.EXPLAINING
    
    # Удаляем игрока из комнаты
    db.delete(player)
    db.commit()

    db.expire_all()
    room_deleted = False
    
    # Если это был создатель комнаты и игра еще не началась, закрываем комнату
    if room.players and len(room.players) > 0 and room.players[0].id == player.id and room.status == GameStatus.WAITING:
        for p in room.players:
            db.delete(p)
        db.delete(room)
    elif len(room.players) <= 1:
        if room.players:
            if room.status == GameStatus.PLAYING:
                last_player = room.players[0]
                last_player.score_total += last_player.score
                db.commit()
            db.delete(room.players[0])
        db.delete(room)
        room_deleted = True
    elif room.status == GameStatus.PLAYING:
        remaining_players = len(room.players)
        if remaining_players < 2:
            room.status = GameStatus.WAITING
            last_player = room.players[0]
            last_player.score_total += last_player.score
            last_player.score = 0
            last_player.role = PlayerRole.WAITING
            db.commit()

    # Отправляем всем оставшимся игрокам сообщение о выходе игрока
    async def broadcast_player_left():
        try:
            player_left_message = {
                "type": "player_left",
                "player_id": player_id,
                "message": f"Игрок {username} покинул игру",
                "timestamp": time.time()
            }
            
            await manager.broadcast(room_code, player_left_message)
                
            await send_game_state_update(room_code, db)
            print(f"Game state update sent after player {player_id} left")
        except Exception as e:
            print(f"Error in broadcast_player_left: {e}")
    
    # Запускаем задачу и ждем небольшую задержку, чтобы она успела запуститься
    background_tasks.add_task(broadcast_player_left)

    if not room_deleted:
        db.refresh(room)
    
    return {"success": True, "message": "Вы успешно покинули игру"}

# Отправка догадки
@router.post("/{room_code}/guess")
async def submit_guess(
    room_code: str,
    guess_data: GuessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Позволяет угадывающему игроку отправить свою догадку.
    
    Параметры:
    - room_code: Код комнаты.
    - guess_data: Данные догадки (текст догадки).
    
    Возвращает:
    - Результат проверки догадки.
    """
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    # Проверяем, что игра идет
    if room.status != GameStatus.PLAYING:
        raise HTTPException(
            status_code=400,
            detail="Игра не запущена"
        )
    
    # Находим игрока в комнате
    player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    
    if not player:
        raise HTTPException(
            status_code=404,
            detail="Вы не являетесь участником этой комнаты"
        )
    
    # Проверяем, что игрок не является объясняющим
    if player.role != PlayerRole.GUESSING:
        raise HTTPException(
            status_code=400,
            detail="Только угадывающие игроки могут отправлять догадки"
        )
    
    # Находим текущее слово
    if not room.current_word_id:
        raise HTTPException(
            status_code=400,
            detail="В игре нет активного слова"
        )
    
    try:
        word_data = get_word_by_id(room.current_word_id, db)
    except HTTPException:
        raise HTTPException(
            status_code=500,
            detail="Не удалось найти текущее слово"
        )
    
    # Проверяем догадку
    guess = guess_data.guess.lower().strip()
    correct = word_data["word"].lower() == guess
    
    if correct:
        player.score += 10
        player.correct_answers += 1
        
        explaining_player = db.query(Player).filter(
            Player.room_id == room.id,
            Player.role == PlayerRole.EXPLAINING
        ).first()
        
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
                        "winner": winner_id
                    }
                )
            
            if room_code in room_timers:
                del room_timers[room_code]
            if room_code in timer_tasks:
                del timer_tasks[room_code]

            background_tasks.add_task(broadcast_game_finished)
            
            return {"correct": True, "message": "Поздравляем! Вы угадали последнее слово. Игра завершена!"}
        
        # Сохраняем старое слово для сообщения
        old_word = word_data["word"]
        
        # Выбираем новое слово
        if room.current_word_id:
            word_data = get_next_word(room.current_word_id, db)
            if word_data and "id" in word_data:
                room.current_word_id = word_data["id"]
        
        db.commit()
        
        # Обновляем таймер комнаты
        room_timers[room_code] = {
            "start_time": time.time(),
            "duration": room.time_per_round,
            "end_time": time.time() + room.time_per_round
        }
        
        # Запускаем новый таймер для следующего слова
        if room_code in timer_tasks:
            timer_tasks[room_code].cancel()
        timer_task = asyncio.create_task(start_round_timer(room_code, room.time_per_round, db))
        timer_tasks[room_code] = timer_task
        
        # Отправляем обновленное состояние игры
        await send_game_state_update(room_code, db)
        
        # Отправляем всем сообщение о правильной догадке
        async def broadcast_correct_guess():
            await manager.broadcast(
                room_code,
                {
                    "type": "correct_guess",
                    "player_id": player.id,
                    "word": old_word,
                    "message": f"Игрок {current_user.name} правильно угадал слово: {old_word}",
                    "new_timer": True,
                    "timer_start": time.time(),
                    "time_per_round": room.time_per_round
                }
            )
        
        background_tasks.add_task(broadcast_correct_guess)
        
        return {"correct": True, "message": "Поздравляем! Вы угадали слово."}
    else:
        # Игрок не угадал слово
        player.wrong_answers += 1
        db.commit()
        
        # Отправляем всем сообщение о неправильной догадке
        async def broadcast_wrong_guess():
            await manager.broadcast(
                room_code,
                {
                    "type": "wrong_guess",
                    "player_id": player.id,
                    "guess": guess,
                    "message": f"Игрок {current_user.name} пытается угадать: {guess}"
                }
            )
        
        background_tasks.add_task(broadcast_wrong_guess)
        
        return {"correct": False, "message": "Неправильно, попробуйте еще раз."}


@router.post("/{room_code}/chat")
async def send_chat_message(
    room_code: str,
    message_data: ChatMessageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отправка сообщения в чат игры.
    
    Параметры:
    - room_code: Код комнаты
    - message_data: Данные сообщения (текст)
    
    Возвращает:
    - Подтверждение отправки сообщения
    """
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    # Проверяем, что пользователь находится в комнате
    player = db.query(Player).filter(
        Player.room_id == room.id,
        Player.user_id == current_user.id
    ).first()
    
    if not player:
        raise HTTPException(
            status_code=403,
            detail="Вы не являетесь участником этой комнаты"
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