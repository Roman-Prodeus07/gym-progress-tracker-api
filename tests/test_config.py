import pytest
from pydantic import ValidationError

from app.core.config import Settings

VALID_DATABASE_URL = (
    "postgresql+psycopg://app_user:strong-database-password@db:5432/gym_tracker"
)
VALID_JWT_SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef"


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="database_url"):
        Settings(
            _env_file=None,
            jwt_secret_key=VALID_JWT_SECRET,
        )


def test_sensitive_settings_are_masked() -> None:
    settings = Settings(
        _env_file=None,
        database_url=VALID_DATABASE_URL,
        jwt_secret_key=VALID_JWT_SECRET,
    )

    representation = repr(settings)

    assert "strong-database-password" not in representation
    assert VALID_JWT_SECRET not in representation
    assert "**********" in representation


def test_valid_production_settings_are_accepted() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url=VALID_DATABASE_URL,
        jwt_secret_key=VALID_JWT_SECRET,
    )

    assert settings.environment == "production"


def test_production_rejects_placeholder_database_credentials() -> None:
    with pytest.raises(
        ValidationError,
        match="DATABASE_URL must not contain placeholder values in production",
    ):
        Settings(
            _env_file=None,
            environment="production",
            database_url=(
                "postgresql+psycopg://app_user:change_me@db:5432/gym_tracker"
            ),
            jwt_secret_key=VALID_JWT_SECRET,
        )


def test_production_rejects_placeholder_jwt_secret() -> None:
    with pytest.raises(
        ValidationError,
        match="JWT_SECRET_KEY must not contain placeholder values in production",
    ):
        Settings(
            _env_file=None,
            environment="production",
            database_url=VALID_DATABASE_URL,
            jwt_secret_key="replace_me_with_a_secure_random_secret_1234567890",
        )


def test_development_allows_documented_local_placeholders() -> None:
    settings = Settings(
        _env_file=None,
        environment="development",
        database_url=(
            "postgresql+psycopg://gym_tracker:change_me@localhost:5432/"
            "gym_progress_tracker"
        ),
        jwt_secret_key="change_me_for_local_development_only_1234567890",
    )

    assert settings.environment == "development"
