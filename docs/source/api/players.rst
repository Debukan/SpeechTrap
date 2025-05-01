Players API
===========

Модуль для управления игроками и обработки их ответов в игре.

HTTP Endpoints
--------------

Создание игрока
~~~~~~~~~~~~~~~
.. http:post:: /players/

   Регистрирует нового игрока в системе.

   **Тело запроса:**

   .. sourcecode:: json

      {
        "name": "string (required, 3-50 chars)",
        "avatar": "string (optional, URL)"
      }

   **Пример успешного ответа (201 Created):**

   .. sourcecode:: json

      {
        "id": 42,
        "name": "Игрок1",
        "avatar": "https://example.com/avatar.jpg",
        "created_at": "2023-01-01T00:00:00",
        "score": 0,
        "correct_answers": 0,
        "wrong_answers": 0
      }

Обработка ответа игрока
~~~~~~~~~~~~~~~~~~~~~~~
.. http:post:: /players/{player_id}/answer

   Проверяет ответ игрока на ассоциацию к слову.

   **Параметры:**

   * **player_id** (path, integer, required): ID игрока
   * **word_id** (body, integer, required): ID слова
   * **guessed_association** (body, string, required): Предложенная ассоциация

   **Пример запроса:**

   .. sourcecode:: json

      {
        "word_id": 101,
        "guessed_association": "круглый"
      }

   **Пример ответа (200 OK):**

   .. sourcecode:: json

      {
        "correct": true,
        "player_score": 15,
        "player_success_rate": 0.75,
        "word_success_rate": 0.62
      }

Модели данных
-------------

PlayerCreate
~~~~~~~~~~~~
.. autoclass:: app.schemas.player.PlayerCreate
   :members:
   :undoc-members:

   **Поля:**

   .. list-table::
      :header-rows: 1
      :widths: 20 20 60

      * - Поле
        - Тип
        - Описание
      * - name
        - str
        - Имя игрока (3-50 символов)
      * - avatar
        - Optional[str]
        - URL аватара (необязательно)

PlayerResponse
~~~~~~~~~~~~~
.. autoclass:: app.schemas.player.PlayerResponse
   :members:
   :undoc-members:

   **Поля:**

   .. list-table::
      :header-rows: 1
      :widths: 20 20 60

      * - Поле
        - Тип
        - Описание
      * - id
        - int
        - Уникальный ID
      * - name
        - str
        - Имя игрока
      * - avatar
        - Optional[str]
        - URL аватара
      * - created_at
        - datetime
        - Дата регистрации
      * - score
        - int
        - Текущие очки
      * - correct_answers
        - int
        - Верные ответы
      * - wrong_answers
        - int
        - Неверные ответы

Ошибки API
----------

.. list-table:: Коды ошибок
   :header-rows: 1
   :widths: 10 30 60

   * - Код
     - Тип
     - Описание
   * - 400
     - Bad Request
     - Невалидные данные (например, имя короче 3 символов)
   * - 404
     - Not Found
     - Игрок или слово не найдены
   * - 422
     - Unprocessable Entity
     - Ошибка валидации входных данных

Примеры использования
---------------------

Создание игрока (Python)
~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

   import httpx

   async def create_player(name: str, avatar: str = None):
       async with httpx.AsyncClient() as client:
           response = await client.post(
               "http://api.example.com/players/",
               json={"name": name, "avatar": avatar}
           )
           return response.json()

Отправка ответа (cURL)
~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: bash

   curl -X POST "http://api.example.com/players/42/answer" \
        -H "Content-Type: application/json" \
        -d '{"word_id":101,"guessed_association":"солнечный"}'