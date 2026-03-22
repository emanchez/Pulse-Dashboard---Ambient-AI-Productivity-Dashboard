from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _resolve_env_file() -> str | None:
    """Return the env file path to load, in priority order:

    1. .env.{APP_ENV}  (e.g. .env.dev or .env.prod) — environment-specific
    2. .env            — legacy fallback / CI override
    3. None            — rely entirely on real environment variables
    """
    app_env = os.environ.get("APP_ENV", "dev")
    specific = _BASE_DIR / f".env.{app_env}"
    if specific.exists():
        return str(specific)
    legacy = _BASE_DIR / ".env"
    if legacy.exists():
        return str(legacy)
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
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

    # OZ Cloud Environment — UID of the environment to run agents in.
    # Create one at https://app.warp.dev → Environments. Required for non-mock runs.
    oz_environment_id: str = Field("", validation_alias="OZ_ENVIRONMENT_ID")

    # OZ Skill Spec — identifies the dashboard-assistant skill in the repo.
    # Format: "owner/repo:skill_name" e.g. "myuser/my-repo:dashboard-assistant"
    # When set, Oz uses `.agents/skills/dashboard-assistant/SKILL.md` as the
    # agent's system instructions. Leave empty to send prompts without a skill.
    oz_skill_spec: str = Field("", validation_alias="OZ_SKILL_SPEC")

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
        """Startup guard: OZ_API_KEY must be set when AI is enabled in non-dev mode.

        Also warns if OZ_ENVIRONMENT_ID or OZ_SKILL_SPEC are missing, since
        cloud agent runs need an environment and skill reference.
        """
        if self.app_env != "dev" and self.oz_api_key == "" and self.ai_enabled:
            raise RuntimeError(
                "OZ_API_KEY must be set when AI_ENABLED=true in non-dev environments. "
                "Run `python scripts/setup_oz.py` to configure your API key, "
                "or set AI_ENABLED=false to disable AI features."
            )
        if self.ai_enabled and self.oz_api_key:
            import logging
            _log = logging.getLogger(__name__)
            if not self.oz_environment_id:
                _log.warning(
                    "OZ_ENVIRONMENT_ID is not set. Cloud agent runs require an "
                    "environment. Create one at https://app.warp.dev → Environments "
                    "and set OZ_ENVIRONMENT_ID in .env."
                )
            if not self.oz_skill_spec:
                _log.warning(
                    "OZ_SKILL_SPEC is not set. Without a skill spec, prompts are "
                    "sent without the dashboard-assistant skill instructions. "
                    "Set OZ_SKILL_SPEC=owner/repo:dashboard-assistant in .env."
                )

    def validate_database_config(self) -> None:
        """Startup guard: prevent SQLite from being used in production.

        In prod, DATABASE_URL must be explicitly set to a PostgreSQL connection
        string. Falling back to the SQLite default in production would silently
        use a local file that is not appropriate for a deployed environment.
        """
        if self.app_env != "dev" and self.database_url.startswith("sqlite"):
            raise RuntimeError(
                "DATABASE_URL is set to SQLite but APP_ENV is not 'dev'. "
                "Set DATABASE_URL to a PostgreSQL connection string in .env.prod "
                "(e.g. postgresql+asyncpg://user:pass@host/db). "
                "See .env.prod.example for the required format."
            )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    The Settings object is created once and reused. Tests that need to
    override settings should call ``get_settings.cache_clear()`` after
    patching environment variables.
    """
    return Settings()
