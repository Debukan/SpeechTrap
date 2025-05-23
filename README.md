![pylint](https://img.shields.io/badge/Pylint%20Score-9.09-yellow?logo=python&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.8-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19.1.0-61DAFB?logo=react&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13-336791?logo=postgresql&logoColor=white)

# SpeechTrap 🎯

Электронная версия популярной настольной игры Taboo. Игроки описывают слова, не используя запрещенные слова, а другие участники должны их угадать.

## 🎮 Особенности игры

- **Многопользовательские комнаты** - до 8 игроков
- **Реальное время** - синхронизация через WebSockets  
- **Различные сложности слов** - базовая, средняя, сложная
- **Система рейтингов** - отслеживание статистики игроков
- **Чат** - общение между игроками
- **Настраиваемые параметры** - время раунда, количество раундов, сложность

## 🏗️ Архитектура

### Backend (FastAPI + Python)
- **FastAPI** - современный веб-фреймворк
- **SQLModel/SQLAlchemy** - ORM для работы с БД
- **WebSockets** - для реального времени
- **JWT** - аутентификация
- **Pytest** - тестирование

### Frontend (React + TypeScript)
- **React 19** - пользовательский интерфейс
- **TypeScript** - типизация
- **Vite** - сборщик
- **Tailwind CSS** - стилизация
- **Radix UI** - компоненты UI

### База данных
- **PostgreSQL** - основная БД
- **Отдельная тестовая БД** - для тестов

## 📁 Структура проекта

```
SpeechTrap/
├── backend/
│   ├── app/
│   │   ├── api/       # API роутеры
│   │   ├── core/      # Базовые функции
│   │   ├── db/        # База данных
│   │   ├── models/    # SQLModel модели
│   │   ├── schemas/   # Pydantic схемы
│   │   └── main.py    # Главный файл
│   └── tests/         # Тесты
├── frontend/
│   ├── src/
│   │   ├── components/ # Страницы и компоненты
│   │   └── utils/      # Различные функции
│   └── public/
├── docker-compose.yml     # Для разработки
├── docker-compose.prod.yml # Для продакшена
└── requirements.txt       # Python зависимости
```

## 🎯 Игровой процесс

1. **Регистрация/Вход** - создайте аккаунт или войдите
2. **Создание комнаты** - настройте параметры игры
3. **Приглашение друзей** - поделитесь кодом комнаты
4. **Игра** - описывайте слова и угадывайте
5. **Результаты** - просматривайте статистику

## 🚀 Дальнейшие планы

- [ ] Голосовой чат
- [ ] Увеличенная база данных слов
- [ ] Система достижений