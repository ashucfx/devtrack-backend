from app.core.config import Settings, get_settings


def test_settings_defaults() -> None:
    settings = get_settings()
    assert settings.PROJECT_NAME == "DevTrack Backend"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.ALGORITHM == "HS256"
    assert "postgresql+asyncpg://" in settings.async_database_url
    assert "postgresql://" in settings.sync_database_url


def test_custom_database_url_override() -> None:
    custom_url = "postgresql+asyncpg://custom_user:custom_pass@custom_host:5432/custom_db"
    settings = Settings(DATABASE_URL=custom_url)
    assert settings.async_database_url == custom_url
