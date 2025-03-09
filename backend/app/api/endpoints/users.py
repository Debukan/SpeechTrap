from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import timedelta
from app.db.session import get_db
from app.core.security import get_password_hash, invalidate_token, create_access_token, get_current_user
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserUpdate
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


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """
    Получение профиля текущего пользователя.
    """

    return current_user


@router.put("/me", response_model=UserResponse)
def update_profile(
        user_update: UserUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Обновление профиля.

    Позволяет изменить имя, email и пароль (при условии совпадения паролей).
    """

    if user_update.name:
        current_user.name = user_update.name

    if user_update.email:
        # Проверяем, не занята ли новая почта
        existing_user = db.query(User).filter(User.email == user_update.email, User.id != current_user.id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email уже используется другим пользователем")
        current_user.email = user_update.email

    if user_update.new_password:
        # Проверяем текущий пароль перед изменением старого
        if not user_update.current_password or not current_user.check_password(user_update.current_password):
            raise HTTPException(status_code=400, detail="Неверный текущий пароль")
        current_user.set_password(user_update.new_password)

    try:
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при обновлении профиля")
