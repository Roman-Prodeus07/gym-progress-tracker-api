from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gym Progress Tracker API"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "production"] = "development"
    database_url: str = (
        "postgresql+psycopg://gym_tracker:change_me@localhost:5432/gym_progress_tracker"
    )

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
