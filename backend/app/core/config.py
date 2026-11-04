"""Centralised application configuration.

All runtime configuration comes from environment variables (or a .env file in
development). Nothing in the codebase should read os.environ directly; import
``get_settings`` instead so tests can override values in one place.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# The repository root holds the single .env file shared by the backend, the
# migration tool, and the database scripts. A .env in the current directory
# (if any) takes precedence so deployments can override it.
_REPO_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_REPO_ROOT_ENV), ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_database: str = "factory_sherlock"
    mysql_user: str = "sherlock_app"
    mysql_password: str = Field(default="", repr=False)

    jwt_secret_key: str = Field(default="", repr=False, min_length=32)
    jwt_access_token_minutes: int = 120
    jwt_algorithm: str = "HS256"

    seed_demo_password: str = Field(default="", repr=False)
    cors_origins: str = "http://localhost:5173"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def effective_database(self) -> str:
        """Tests must never touch development data, so they get their own schema."""
        if self.app_env == "test":
            return f"{self.mysql_database}_test"
        return self.mysql_database

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.effective_database}?charset=utf8mb4"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
