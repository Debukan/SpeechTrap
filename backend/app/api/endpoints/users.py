from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_password_hash, invalidate_token
from app.schemas.user import UserCreate
from app.schemas.auth import LogoutResponse
# TODO: раскоммитить когда будет сделана
from app.models.user import User

# Схема OAuth2 для получени токена из заголовка
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter()

@router.post('/register', response_model=UserCreate)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
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
        name=user_data.name,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password)
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user_data
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Ошибка при регистрации пользователя"
        )
    

@router.post("/logout", response_model=LogoutResponse)
async def logout(token: str = Depends(oauth2_scheme)):
    """
    Выход пользователя из системы

    Args:
        token: JWT токен пользователя
    Returns:
        LogoutResponse: Сообщение об успешном выходе
    """
    try:
        invalidate_token(token)
        return LogoutResponse(message="Успешный выход из системы")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при выходе из системы"
        )