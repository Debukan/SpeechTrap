from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_password_hash, invalidate_token, create_access_token
from app.schemas.user import UserCreate, UserLogin
from app.schemas.auth import LogoutResponse
from app.models.user import User
from app.schemas.auth import Token
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

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
        email=user_data.email)
    user.set_password(user_data.password)

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


@router.post("/login", response_model=Token)
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Аутентификация пользователя по email и паролю.

    Если пользователь прошел проверку, возвращается JWT токен для дальнейшего использования.
    """
    # Поиск пользователя по email
    user = db.query(User).filter(User.email == user_data.email).first()
    
    # Если пользователь не найден
    if not user:
        logger.info("Пользователь не найден")
        raise HTTPException(
            status_code=401,
            detail="Неверные данные"
        )
    
    # Если пароль неверный
    if not user.check_password(user_data.password):
        raise HTTPException(
            status_code=401,
            detail="Неверные данные"
        )

    # Генерация JWT токена
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=30)
    )

    return {"access_token": access_token, "token_type": "bearer"}