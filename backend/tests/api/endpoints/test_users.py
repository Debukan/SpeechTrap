import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch
from app.main import app
from app.models.user import User
from app.core.security import get_password_hash, create_access_token

client = TestClient(app)


def test_register_user(test_db: Session):
    """Тест регистрации нового пользователя."""
    user_data = {
        "name": "Test Register",
        "email": "testregister@example.com",
        "password": "strongpassword123",
    }

    response = client.post("/api/users/register", json=user_data)
    assert response.status_code == 200

    db_user = test_db.query(User).filter(User.email == user_data["email"]).first()
    assert db_user is not None
    assert db_user.name == user_data["name"]
    assert db_user.email == user_data["email"]


def test_register_existing_user(test_db: Session):
    """Тест попытки регистрации с уже существующим email."""
    existing_user = User(
        name="Existing User",
        email="existing@example.com",
        hashed_password=get_password_hash("password123"),
    )
    test_db.add(existing_user)
    test_db.commit()

    user_data = {
        "name": "New User Same Email",
        "email": "existing@example.com",
        "password": "newpassword123",
    }

    response = client.post("/api/users/register", json=user_data)
    assert response.status_code == 400
    assert "уже существует" in response.json()["detail"]


def test_login_success(test_db: Session):
    """Тест успешной авторизации пользователя."""
    password = "correctpassword123"
    user = User(
        name="Login Test User",
        email="logintest@example.com",
        hashed_password=get_password_hash(password),
    )
    test_db.add(user)
    test_db.commit()

    login_data = {"email": "logintest@example.com", "password": password}

    response = client.post("/api/users/login", json=login_data)
    assert response.status_code == 200

    assert "access_token" in response.json()
    assert "token_type" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_invalid_credentials(test_db: Session):
    """Тест авторизации с неверными учетными данными."""
    user = User(
        name="Invalid Login Test",
        email="invalidlogin@example.com",
        hashed_password=get_password_hash("correctpass123"),
    )
    test_db.add(user)
    test_db.commit()

    login_data = {"email": "invalidlogin@example.com", "password": "wrongpassword"}

    response = client.post("/api/users/login", json=login_data)
    assert response.status_code == 401
    assert "Неверные данные" in response.json()["detail"]


def test_get_profile(test_db: Session):
    """Тест получения профиля авторизованного пользователя."""
    user = User(
        name="Profile Test",
        email="profiletest@example.com",
        hashed_password=get_password_hash("profilepass123"),
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    token = create_access_token(data={"sub": user.email})

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/users/me", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user.email
    assert data["name"] == user.name
    assert "id" in data


def test_get_profile_unauthorized():
    """Тест получения профиля без авторизации."""
    response = client.get("/api/users/me")
    assert response.status_code == 401


def test_update_profile(test_db: Session):
    """Тест обновления профиля пользователя."""
    original_password = "originalpass123"
    user = User(
        name="Original Name",
        email="updatetest@example.com",
        hashed_password=get_password_hash(original_password),
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    token = create_access_token(data={"sub": user.email})
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
        "Content-Type": "application/json",
    }
    client.cookies.clear()

    update_data = {
        "name": "Updated Name",
        "email": user.email,
        "new_password": "newpass456",
        "confirm_password": "newpass456",
        "current_password": original_password,
    }

    response = client.put("/api/users/me", json=update_data, headers=headers)

    assert response.status_code in (200, 204), response.text

    test_db.refresh(user)
    assert user.name == update_data["name"]

    login_data = {"email": user.email, "password": update_data["new_password"]}

    login_response = client.post("/api/users/login", json=login_data)
    assert login_response.status_code == 200


def test_logout_success(monkeypatch):
    token = "dummy.token.value"
    monkeypatch.setenv("TESTING", "True")
    with patch("app.api.endpoints.users.invalidate_token") as mock_inval:
        mock_inval.return_value = None
        response = client.post(
            "/api/users/logout", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Успешный выход из системы"


def test_logout_failure(monkeypatch):
    token = "dummy.token.value"
    with patch("app.api.endpoints.users.invalidate_token") as mock_inval:
        mock_inval.side_effect = Exception("fail")
        response = client.post(
            "/api/users/logout", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 500
        assert "Ошибка при выходе" in response.json()["detail"]


def test_update_profile_email_conflict(test_db):
    from app.models.user import User

    u1 = User(
        name="U1", email="u1@example.com", hashed_password=get_password_hash("p1")
    )
    u2 = User(
        name="U2", email="u2@example.com", hashed_password=get_password_hash("p2")
    )
    test_db.add_all([u1, u2])
    test_db.commit()
    token = create_access_token(data={"sub": u1.email})
    headers = {"Authorization": f"Bearer {token}"}
    data = {"email": u2.email}
    response = client.put("/api/users/me", json=data, headers=headers)
    assert response.status_code == 400
    assert "Email уже используется" in response.json()["detail"]


def test_update_profile_invalid_current_password(test_db):
    user = User(
        name="U3", email="u3@example.com", hashed_password=get_password_hash("orig")
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    token = create_access_token(data={"sub": user.email})
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "new_password": "newpass1",
        "confirm_password": "newpass1",
        "current_password": "wrong",
    }
    response = client.put("/api/users/me", json=data, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "Неверный текущий пароль"
