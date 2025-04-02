import random
from fastapi import FastAPI, APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, ORJSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Dict, Any, List
from pydantic import BaseModel

from app.db.deps import get_db
from app.models.word import WordWithAssociations
from app.models.room import Room, GameStatus
from app.models.player import Player, PlayerRole
from app.models.user import User
from app.core.security import get_current_user
from app.api.endpoints.ws import manager

router = APIRouter()

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
    # Находим комнату по коду
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
    
    # Находим текущее слово, если оно есть
    current_word = ""
    if room.status == GameStatus.PLAYING and room.current_word_id:
        word = db.query(WordWithAssociations).filter(
            WordWithAssociations.id == room.current_word_id
        ).first()
        
        # Текущее слово показываем только объясняющему игроку
        if word and player.role == PlayerRole.EXPLAINING:
            current_word = word.word
            
    # Текущий игрок (объясняющий) с ролью EXPLAINING
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
                "score": p.score
            })
    
    time_left = None
    if room.status == GameStatus.PLAYING:
        time_left = 60
    
    # Формируем ответ
    response = {
        "currentWord": current_word,
        "players": players,
        "round": room.current_round,
        "status": room.status,
        "timeLeft": time_left,
        "currentPlayer": current_player,
        "rounds_total": room.rounds_total
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
    # Находим комнату по коду
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
    
    # Выбираем случайное слово из базы
    word = db.query(WordWithAssociations).filter(
        WordWithAssociations.is_active == True
    ).order_by(func.random()).first()
    
    if not word:
        raise HTTPException(
            status_code=500,
            detail="Не удалось выбрать слово для игры"
        )
    
    room.status = GameStatus.PLAYING
    room.current_round = 1
    room.current_word_id = word.id
    
    # Назначаем первого игрока объясняющим
    first_player.role = PlayerRole.EXPLAINING
    
    for player in room.players[1:]:
        player.role = PlayerRole.GUESSING
    
    db.commit()
    
    # Отправляем всем участникам комнаты сообщение о начале игры
    async def broadcast_game_started():
        await manager.broadcast(
            room_code,
            {
                "type": "game_started", 
                "message": "Игра началась!",
                "redirect_to": f"/game/{room_code}"
            }
        )
    
    background_tasks.add_task(broadcast_game_started)
    
    return {"success": True, "message": "Игра успешно начата"}

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
    
    players = db.query(Player).filter(
        Player.room_id == room.id
    ).order_by(Player.id).all()
    
    current_index = players.index(current_player)
    
    next_index = (current_index + 1) % len(players)
    next_player = players[next_index]
    
    # Назначаем следующего игрока объясняющим
    next_player.role = PlayerRole.EXPLAINING
    
    # Если сделали полный круг, увеличиваем номер раунда и меняем слово
    if next_index == 0:
        room.current_round += 1
        
        if room.current_round > room.rounds_total:
            room.status = GameStatus.FINISHED
            
            # Сбрасываем роли всех игроков
            for player in players:
                player.role = PlayerRole.WAITING
                
            db.commit()
            
            # Отправляем всем сообщение о завершении игры
            async def broadcast_game_finished():
                await manager.broadcast(
                    room_code,
                    {
                        "type": "game_finished",
                        "message": "Игра завершена!",
                        "winner": max(players, key=lambda p: p.score).id
                    }
                )
            
            background_tasks.add_task(broadcast_game_finished)
            
            return {"success": True, "message": "Игра завершена!"}
        
        # Выбираем новое слово для следующего раунда
        word = db.query(WordWithAssociations).filter(
            WordWithAssociations.is_active == True,
            WordWithAssociations.id != room.current_word_id
        ).order_by(func.random()).first()
        
        if word:
            room.current_word_id = word.id
    
    db.commit()
    
    # Отправляем всем сообщение о смене игрока
    async def broadcast_turn_changed():
        user = db.query(User).filter(User.id == next_player.user_id).first()
        await manager.broadcast(
            room_code,
            {
                "type": "turn_changed",
                "message": f"Ход переходит к игроку {user.name if user else 'Неизвестный'}"
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
    
    player_id = player.id
    username = current_user.name
    
    # Если игрок является объясняющим, нужно передать ход следующему
    if player.role == PlayerRole.EXPLAINING and room.status == GameStatus.PLAYING:
        players = db.query(Player).filter(
            Player.room_id == room.id
        ).order_by(Player.id).all()
        
        current_index = players.index(player)
        next_index = (current_index + 1) % len(players)
        
        if len(players) > 1:
            next_player = players[next_index]
            next_player.role = PlayerRole.EXPLAINING
    
    db.delete(player)
    
    # Если это был создатель комнаты и игра еще не началась, закрываем комнату
    if room.players and len(room.players) > 0 and room.players[0].id == player.id and room.status == GameStatus.WAITING:
        for p in room.players:
            db.delete(p)
        db.delete(room)
    # Если это был последний игрок, удаляем комнату
    elif len(room.players) <= 1:
        if room.players:
            db.delete(room.players[0])
        db.delete(room)
    
    db.commit()
    
    # Отправляем всем оставшимся игрокам сообщение о выходе игрока
    async def broadcast_player_left():
        await manager.broadcast(
            room_code,
            {
                "type": "player_left",
                "player_id": player_id,
                "message": f"Игрок {username} покинул игру"
            }
        )
    
    background_tasks.add_task(broadcast_player_left)
    
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
    
    word = db.query(WordWithAssociations).filter(
        WordWithAssociations.id == room.current_word_id
    ).first()
    
    if not word:
        raise HTTPException(
            status_code=500,
            detail="Не удалось найти текущее слово"
        )
    
    guess = guess_data.guess.lower().strip()
    correct = word.word.lower() == guess
    
    if correct:
        player.score += 10
        player.correct_answers += 1

        explaining_player = db.query(Player).filter(
            Player.room_id == room.id,
            Player.role == PlayerRole.EXPLAINING
        ).first()
        
        if explaining_player:
            explaining_player.score += 5
        
        # Выбираем новое слово
        new_word = db.query(WordWithAssociations).filter(
            WordWithAssociations.is_active == True,
            WordWithAssociations.id != room.current_word_id
        ).order_by(func.random()).first()
        
        if new_word:
            room.current_word_id = new_word.id
        
        db.commit()
        
        # Отправляем всем сообщение о правильной догадке
        async def broadcast_correct_guess():
            await manager.broadcast(
                room_code,
                {
                    "type": "correct_guess",
                    "player_id": player.id,
                    "word": word.word,
                    "message": f"Игрок {current_user.name} правильно угадал слово: {word.word}"
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
