from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
    )

    database_url: str = Field("sqlite+aiosqlite:///./data/dev.db", validation_alias="DATABASE_URL")
    jwt_secret: str = Field("dev-secret-change-me", validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(60 * 24 * 7, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    # Stored as a raw comma-separated string so pydantic-settings does not
    # attempt JSON pre-parsing on env vars of type List[str].
    frontend_cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
        validation_alias="FRONTEND_CORS_ORIGINS",
    )

    def get_cors_origins(self) -> list[str]:
        """Split the raw comma-separated origin string into a list."""
        return [o.strip() for o in self.frontend_cors_origins.split(",") if o.strip()]


def get_settings() -> Settings:
    return Settings()
