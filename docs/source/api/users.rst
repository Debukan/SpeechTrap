Users API Documentation
=======================

.. contents::
   :local:
   :depth: 2

Overview
--------
Модуль для управления пользователями и аутентификации. Обеспечивает:

- Регистрацию новых пользователей
- Аутентификацию по email/паролю
- Управление профилем пользователя
- JWT-авторизацию
- Выход из системы

API Endpoints
------------

Register User
~~~~~~~~~~~~
.. http:post:: /users/register

   Регистрация нового пользователя в системе.

   **Request Body:**
   .. code-block:: json

      {
        "name": "string (required, min 2 chars)",
        "email": "string (required, email format)",
        "password": "string (required, min 8 chars)"
      }

   **Success Response (200):**
   .. code-block:: json

      {
        "name": "Иван Иванов",
        "email": "user@example.com"
      }

   **Error Responses:**
   - 400: Пользователь с таким email уже существует
   - 422: Ошибка валидации данных

User Login
~~~~~~~~~
.. http:post:: /users/login

   Аутентификация пользователя. Возвращает JWT токен.

   **Request Body:**
   .. code-block:: json

      {
        "email": "string (required)",
        "password": "string (required)"
      }

   **Success Response (200):**
   .. code-block:: json

      {
        "access_token": "eyJhbGciOi...",
        "token_type": "bearer"
      }

   **Error Responses:**
   - 401: Неверные учетные данные

User Logout
~~~~~~~~~~
.. http:post:: /users/logout

   Выход пользователя из системы (инвалидация токена).

   **Headers:**
   - Authorization: Bearer {token}

   **Success Response (200):**
   .. code-block:: json

      {
        "message": "Успешный выход из системы"
      }

Get User Profile
~~~~~~~~~~~~~~~
.. http:get:: /users/me

   Получение данных текущего пользователя.

   **Headers:**
   - Authorization: Bearer {token}

   **Success Response (200):**
   .. code-block:: json

      {
        "id": 1,
        "name": "Иван Иванов",
        "email": "user@example.com",
        "created_at": "2023-01-01T00:00:00"
      }

Update Profile
~~~~~~~~~~~~~
.. http:put:: /users/me

   Обновление данных пользователя.

   **Headers:**
   - Authorization: Bearer {token}

   **Request Body:**
   .. code-block:: json

      {
        "name": "string (optional)",
        "email": "string (optional)",
        "current_password": "string (required if changing password)",
        "new_password": "string (optional, min 8 chars)"
      }

   **Success Response (200):**
   .. code-block:: json

      {
        "id": 1,
        "name": "Новое имя",
        "email": "new@example.com",
        "created_at": "2023-01-01T00:00:00"
      }

   **Error Responses:**
   - 400: Неверный текущий пароль или email занят
   - 401: Неавторизованный доступ
   - 422: Ошибка валидации

Security
--------
Все защищенные endpoints используют:
- JWT-авторизацию через OAuth2
- Токен должен передаваться в заголовке:

- Токен действителен 30 минут

Data Models
-----------

UserCreate
~~~~~~~~~~
.. list-table::
 :header-rows: 1
 :widths: 20 20 60

 * - Поле
   - Тип
   - Описание
 * - name
   - str
   - Полное имя (2-50 символов)
 * - email
   - str
   - Email (уникальный)
 * - password
   - str
   - Пароль (мин. 8 символов)

UserLogin
~~~~~~~~
.. list-table::
 :header-rows: 1
 :widths: 20 20 60

 * - Поле
   - Тип
   - Описание
 * - email
   - str
   - Email пользователя
 * - password
   - str
   - Пароль

UserUpdate
~~~~~~~~~
.. list-table::
 :header-rows: 1
 :widths: 20 20 60

 * - Поле
   - Тип
   - Описание
 * - name
   - Optional[str]
   - Новое имя
 * - email
   - Optional[str]
   - Новый email
 * - current_password
   - Optional[str]
   - Текущий пароль (обязателен при смене)
 * - new_password
   - Optional[str]
   - Новый пароль
