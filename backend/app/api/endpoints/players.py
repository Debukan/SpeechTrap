from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.player import Player
from app.schemas.player import PlayerCreate, PlayerResponse

router = APIRouter()


@router.post("/", response_model=PlayerResponse)
async def create_player(player: PlayeCreate, db: Session = Depends(get_db)):
    db_player = Player(**player.dict())
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player
