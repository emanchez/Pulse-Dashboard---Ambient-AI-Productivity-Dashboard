from typing import List
import os
from pydantic_settings import BaseSettings
from pydantic import Field, AnyUrl


class Settings(BaseSettings):
    database_url: str = Field("sqlite+aiosqlite:///./data/dev.db", env="DATABASE_URL")
    jwt_secret: str = Field("dev-secret-change-me", env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(60 * 24 * 7, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    frontend_cors_origins: List[str] = Field([
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ], env="FRONTEND_CORS_ORIGINS")

    class Config:
        env_file = None


def get_settings() -> Settings:
    s = Settings()
    # allow FRONTEND_CORS_ORIGINS to be supplied as a comma-separated string in .env
    origins = s.frontend_cors_origins
    if isinstance(origins, str):
        s.frontend_cors_origins = [o.strip() for o in origins.split(",") if o.strip()]
    return s
