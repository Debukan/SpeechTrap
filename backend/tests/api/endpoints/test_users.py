import pytest
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.main import app

def test_register_user(client):
    response = client.post(
        "/users/register",
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
        '/users/register',
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "test@password123"
        }
    )

    # Повторная регистрация
    response = client.post(
        "/users/register",
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
        "/users/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Успешный выход из системы"