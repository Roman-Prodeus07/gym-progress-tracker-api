from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, PositiveInt, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PRODUCTION_PLACEHOLDER_MARKERS = (
    "change_me",
    "changeme",
    "placeholder",
    "replace-me",
    "replace_me",
)


def _contains_placeholder(value: str) -> bool:
    normalized_value = value.casefold()
    return any(marker in normalized_value for marker in PRODUCTION_PLACEHOLDER_MARKERS)


class Settings(BaseSettings):
    app_name: str = "Gym Progress Tracker API"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "production"] = "development"
    database_url: SecretStr = Field(min_length=1)

    jwt_secret_key: SecretStr = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_access_token_expire_minutes: PositiveInt = 30
    jwt_issuer: str = "gym-progress-tracker-api"
    jwt_audience: str = "gym-progress-tracker-api"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Self:
        if self.environment != "production":
            return self

        if _contains_placeholder(self.database_url.get_secret_value()):
            raise ValueError(
                "DATABASE_URL must not contain placeholder values in production."
            )

        if _contains_placeholder(self.jwt_secret_key.get_secret_value()):
            raise ValueError(
                "JWT_SECRET_KEY must not contain placeholder values in production."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
