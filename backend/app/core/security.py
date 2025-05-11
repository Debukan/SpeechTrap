import bcrypt
from datetime import datetime, timedelta
from typing import Optional
import jwt
from pydantic import BaseModel
from fastapi import HTTPException, Depends, status
from sqlmodel import select
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from app.db.deps import get_db

# Настройки JWT
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Хранение недействительных токенов
blacklisted_tokens = set()

# Определение способа получения токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    """Схема токена"""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Данные токена"""

    email: Optional[str] = None
    exp: Optional[datetime] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка соответсвия пароля хешу

    Args:
        plain_password: Веденный пароль
        hashed_password: Хеш пароля из БД
    Returns:
        bool: True если пароль верный
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """
    Хеширование пароля
    Args:
        password: Пароль для хеширования
    Returns:
        str: Хеш пароля
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Создание JWT токена

    Args:
        data: Данные для включения в токен
        expires_delta: Время жизни токена
    Returns:
        str: JWT токен
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Декодирование JWT токена

    Args:
        token: JWT токен дл декодирования
    Returns:
        dict: Данные из токена
    Raises:
        jwt.InvalidTokenError: Если токен недействителен
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        exp: datetime = datetime.fromtimestamp(payload.get("exp"))

        if email is None:
            return None

        return TokenData(email=email, exp=exp)
    except jwt.InvalidTokenError:
        return None


def invalidate_token(token: str) -> None:
    """Добавление токена в черный список"""
    blacklisted_tokens.add(token)


def is_token_valid(token: str) -> bool:
    """Проверка валидности токена"""
    return token not in blacklisted_tokens


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """
    Получает текущего пользователя по JWT токену.

    Args:
        token (str): JWT токен пользователя.
        db (Session): Сессия базы данных.
    Returns:
        User: Объект пользователя, если токен действителен.
    Raises:
        HTTPException: 401 если токен недействителен или пользователь не найден.
    """

    # Проверка валидности токена
    if not is_token_valid(token):
        raise HTTPException(status_code=401, detail="Токен недействителен")

    # Декодирование данных из токена
    token_data = decode_access_token(token)
    if not token_data or not token_data.email:
        raise HTTPException(status_code=401, detail="Неверные учетные данные")

    # Поиск пользователя в базе данных по email
    user = get_user_from_db(token_data.email, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_user_from_db(email: str, db: Session):
    """
    Поиск пользователя по email в базе данных.

    Args:
        email (str): Электронная почта пользователя.
        db (Session): Сессия базы данных.

    Returns:
        User: Объект пользователя, если он найден в базе данных, иначе None.
    """
    from app.models.user import User

    statement = select(User).where(User.email == email)
    result = db.execute(statement).first()

    if result is None:
        return None

    user = result[0]

    return user
