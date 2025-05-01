WebSocket API Documentation (ws.py)
==================================

Overview
--------
Модуль для управления WebSocket-подключениями в игровых комнатах. Обеспечивает:

- Реальное время взаимодействия между игроками
- Рассылку сообщений всем участникам комнаты
- Персональные сообщения
- Управление подключениями

Основные компоненты
-------------------

ConnectionManager
~~~~~~~~~~~~~~~~
Класс для управления WebSocket-подключениями.

**Методы:**

.. py:method:: connect(websocket: WebSocket, room_code: str, user_id: int = None)
   :async:

   Устанавливает новое подключение к комнате.

   - ``websocket``: WebSocket-соединение
   - ``room_code``: Код комнаты
   - ``user_id``: ID пользователя (опционально)

.. py:method:: disconnect(room_code: str, user_id: int = None, websocket: WebSocket = None)

   Закрывает подключение.

   - ``room_code``: Код комнаты
   - ``user_id``: ID пользователя (опционально)
   - ``websocket``: WebSocket-соединение (опционально)

.. py:method:: broadcast(room_code: str, message: dict, exclude_user_id: int = None, exclude_websocket: WebSocket = None)
   :async:

   Рассылает сообщение всем участникам комнаты.

   - ``room_code``: Код комнаты
   - ``message``: Сообщение для рассылки
   - ``exclude_user_id``: ID пользователя для исключения
   - ``exclude_websocket``: WebSocket для исключения

.. py:method:: send_personal_message(user_id: str, message: dict)
   :async:

   Отправляет личное сообщение пользователю.

   - ``user_id``: ID пользователя
   - ``message``: Сообщение

WebSocket Endpoint
-----------------

websocket_endpoint
~~~~~~~~~~~~~~~~~~
.. py:function:: websocket_endpoint(websocket: WebSocket, room_code: str, user_id: int, db: Session = Depends(get_db))
   :async:

   Основная точка входа для WebSocket-подключений.

   **Параметры:**
   - ``websocket``: WebSocket-соединение
   - ``room_code``: Код комнаты
   - ``user_id``: ID пользователя
   - ``db``: Сессия базы данных

   **Логика работы:**
   1. Проверяет существование комнаты и пользователя
   2. Устанавливает соединение
   3. Отправляет текущее состояние комнаты
   4. Обрабатывает входящие сообщения:
      - Чат-сообщения
      - Игровые действия

   **Типы сообщений:**
   - ``chat``: Текстовые сообщения чата
   - ``game_action``: Действия в игре

Примеры сообщений
-----------------

**Чат-сообщение:**
.. code-block:: json

   {
     "type": "chat",
     "user_id": 123,
     "message": "Привет всем!"
   }

**Игровое действие:**
.. code-block:: json

   {
     "type": "game_action",
     "user_id": 123,
     "action": "start_game"
   }

Пример использования
--------------------

**Подключение к комнате:**
.. code-block:: javascript

   const socket = new WebSocket(
     `ws://api.example.com/ws/${roomCode}/${userId}`
   );

   socket.onmessage = (event) => {
     const data = JSON.parse(event.data);
     console.log('Received:', data);
   };

**Отправка сообщения:**
.. code-block:: javascript

   socket.send(JSON.stringify({
     type: "chat",
     message: "Hello world!"
   }));

Примечания
----------
- Все сообщения передаются в формате JSON
- Требуется авторизация пользователя
- Поддерживается только текстовый формат сообщений