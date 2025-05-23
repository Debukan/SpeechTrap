from app.core.config import settings
import os


def test_settings_load():
    """
    Тест проверяет, что основные настройки загружаются.
    """
    assert settings.SECRET_KEY is not None
    assert isinstance(settings.SECRET_KEY, str)
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES is not None
    assert isinstance(settings.ACCESS_TOKEN_EXPIRE_MINUTES, int)

    assert settings.POSTGRES_USER == os.getenv("POSTGRES_USER")
    assert settings.POSTGRES_PASSWORD == os.getenv("POSTGRES_PASSWORD")
    assert settings.POSTGRES_DB == os.getenv("POSTGRES_DB")
