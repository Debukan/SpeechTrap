import pytest
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.main import app
import logging

logger = logging.getLogger(__name__)

def test_register_user(client):
    response = client.post(
        "/api/users/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"

def test_register_existing_user(client):
    # Первая регистрация
    client.post(
        '/api/users/register',
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "test@password123"
        }
    )

    # Повторная регистрация
    response = client.post(
        "/api/users/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Пользователь с таким email уже существует"

def test_logout(client):
    # Создаем тестовый токен
    token = create_access_token({"sub": "test@example.com"})
    response = client.post(
        "/api/users/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Успешный выход из системы"

def test_login_wrong_credentials(client):
    response = client.post(
        "/api/users/login",
        json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401
    assert response.json()['detail'] == "Неверные данные"