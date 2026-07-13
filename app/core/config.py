from functools import lru_cache
from typing import Literal

from pydantic import Field, PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gym Progress Tracker API"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "production"] = "development"
    database_url: str = (
        "postgresql+psycopg://gym_tracker:change_me@localhost:5432/gym_progress_tracker"
    )

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
