from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_password_hash
from app.schemas.user import UserCreate
# TODO: раскоммитить когда будет сделана
from models.user import User

router = APIRouter()

@router.post('/register', response_model=UserCreate)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db))
    """
    Регистрация нового пользователя

    """
    # Проверяем, существует ли пользователь с таким email
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким email уже существует"
        )

    # Создаем нового пользователя
    user = User(
        name = user_data.name,
        email = user.data.email
        hashed_password=get_password_hash(user_data.password)
    )

    try:
        db.add(user)
        db.commit()
        db.refresh()
        return user_data
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Ошибка при регистрации пользователя"
        )