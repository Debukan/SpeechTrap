from fastapi import Depends
from app.db.deps import get_db
from app.core.security import get_current_user, oauth2_scheme

# Переэкспортировка функции для удобства импорта в других модулях
__all__ = ['get_db', 'get_current_user', 'oauth2_scheme']