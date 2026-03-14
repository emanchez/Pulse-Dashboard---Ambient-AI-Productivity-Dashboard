from __future__ import annotations

from functools import lru_cache
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
    access_token_expire_minutes: int = Field(60 * 8, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")  # 8 hours
    app_env: str = Field("dev", validation_alias="APP_ENV")
    # Stored as a raw comma-separated string so pydantic-settings does not
    # attempt JSON pre-parsing on env vars of type List[str].
    frontend_cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
        validation_alias="FRONTEND_CORS_ORIGINS",
    )

    # ── OZ / AI settings ──────────────────────────────────────────────────
    oz_api_key: str = Field("", validation_alias="OZ_API_KEY")
    # Cost tip: claude-haiku-4 is cheapest; only upgrade model if output quality is insufficient
    oz_model_id: str = Field("anthropic/claude-haiku-4", validation_alias="OZ_MODEL_ID")
    ai_enabled: bool = Field(True, validation_alias="AI_ENABLED")
    oz_max_wait_seconds: int = Field(90, validation_alias="OZ_MAX_WAIT_SECONDS")
    oz_max_context_chars: int = Field(8000, validation_alias="OZ_MAX_CONTEXT_CHARS")
    # Rate limit caps — enforced by AIRateLimiter (service layer, not SlowAPI)
    oz_max_synthesis_per_week: int = Field(3, validation_alias="OZ_MAX_SYNTHESIS_PER_WEEK")
    oz_max_suggestions_per_day: int = Field(5, validation_alias="OZ_MAX_SUGGESTIONS_PER_DAY")
    oz_max_coplan_per_day: int = Field(3, validation_alias="OZ_MAX_COPLAN_PER_DAY")

    def get_cors_origins(self) -> list[str]:
        """Split the raw comma-separated origin string into a validated list.

        In non-dev environments, raises ValueError if any origin contains
        localhost/127.0.0.1 — fail-closed to prevent accidental prod misconfiguration.
        """
        origins = [o.strip() for o in self.frontend_cors_origins.split(",") if o.strip()]
        if self.app_env != "dev":
            for o in origins:
                if "localhost" in o or "127.0.0.1" in o:
                    raise ValueError(
                        f"CORS origin '{o}' contains localhost/127.0.0.1. "
                        "Set FRONTEND_CORS_ORIGINS to the production domain."
                    )
        return origins

    def validate_oz_config(self) -> None:
        """Startup guard: OZ_API_KEY must be set when AI is enabled in non-dev mode."""
        if self.app_env != "dev" and self.oz_api_key == "" and self.ai_enabled:
            raise RuntimeError(
                "OZ_API_KEY must be set when AI_ENABLED=true in non-dev environments. "
                "Run `python scripts/setup_oz.py` to configure your API key, "
                "or set AI_ENABLED=false to disable AI features."
            )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    The Settings object is created once and reused. Tests that need to
    override settings should call ``get_settings.cache_clear()`` after
    patching environment variables.
    """
    return Settings()
