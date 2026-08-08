"""Unit tests for application configuration settings."""

import os
from unittest.mock import patch

from finreg.config.settings import Settings, get_settings


def test_default_settings() -> None:
    """Verify default setting values when no env vars or .env file are provided."""
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_name == "finreg-intelligence"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.postgres_host == "localhost"
    assert settings.postgres_port == 5432
    assert settings.postgres_db == "finreg_db"
    assert settings.postgres_user == "finreg_user"
    assert settings.postgres_password == "finreg_password"
    assert "postgresql+psycopg2://" in settings.database_url


def test_custom_env_settings() -> None:
    """Verify settings parse custom environment variables correctly."""
    env_override = {
        "APP_NAME": "test-finreg",
        "ENVIRONMENT": "testing",
        "POSTGRES_PORT": "5433",
        "POSTGRES_DB": "test_db",
    }
    with patch.dict(os.environ, env_override):
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.app_name == "test-finreg"
        assert settings.environment == "testing"
        assert settings.postgres_port == 5433
        assert settings.postgres_db == "test_db"
        assert ":5433/test_db" in settings.database_url


def test_cached_get_settings() -> None:
    """Verify get_settings returns a cached Settings instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
