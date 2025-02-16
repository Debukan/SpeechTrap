from sqlmodel import SQLModel

from app.models.word import WordWithAssociations
from app.models.room import Room
from app.models.player import Player
from app.models.user import User


# Создание таблиц
Base = SQLModel
