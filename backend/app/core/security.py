from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import jwt
from pydantic import BaseModel
from app.core.config import settings

# Настройки шифрования паролей
pwd_context = CryptContext(schemes=['bcrypt'], deprecated="auto")

# Настройки JWT
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


class Token(BaseModel):
    """Схема токена"""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Данные токена"""
    email: str | None = None
    exp: datetime | None = None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка соответсвия пароля хешу

    Args:
        plain_password: Веденный пароль
        hashed_password: Хеш пароля из БД
    Returns:
        bool: True если пароль верный
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Хеширование пароля
    Args:
        password: Пароль для хеширования
    Returns:
        str: Хеш пароля
    """
    return pwd_context.hash(password)

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

    # Установка времени истеченияя токена
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
        email: str = payload.get('sub')
        exp: datetime = datetime.fromtimestamp(payload.get('exp'))

        if email is None:
            return None
        
        return TokenData(email=email, exp=exp)
    except jwt.InvalidTokenError:
        return None