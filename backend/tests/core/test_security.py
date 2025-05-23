import pytest
import jwt
from datetime import timedelta
from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    ALGORITHM,
)
from app.core.config import settings


def test_verify_password():
    """Тест проверки правильного пароля."""
    password = "plainpassword"
    hashed_password = get_password_hash(password)
    assert verify_password(password, hashed_password) is True


def test_verify_wrong_password():
    """Тест проверки неправильного пароля."""
    password = "plainpassword"
    wrong_password = "wrongpassword"
    hashed_password = get_password_hash(password)
    assert verify_password(wrong_password, hashed_password) is False


def test_get_password_hash():
    """Тест хеширования пароля."""
    password = "plainpassword"
    hashed_password = get_password_hash(password)
    assert isinstance(hashed_password, str)
    assert password != hashed_password


def test_create_access_token():
    """Тест создания токена доступа."""
    data = {"sub": "test@example.com"}
    token = create_access_token(data)
    assert isinstance(token, str)

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == data["sub"]
    assert "exp" in payload


def test_create_access_token_with_expiry():
    """Тест создания токена доступа с кастомным временем жизни."""
    data = {"sub": "test@example.com"}
    expires_delta = timedelta(minutes=15)
    token = create_access_token(data, expires_delta=expires_delta)
    assert isinstance(token, str)

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == data["sub"]
    assert "exp" in payload
