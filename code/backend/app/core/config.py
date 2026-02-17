from typing import List
from pydantic import BaseSettings, Field, AnyUrl


class Settings(BaseSettings):
    database_url: str = Field("sqlite+aiosqlite:///./data/dev.db", env="DATABASE_URL")
    jwt_secret: str = Field("dev-secret-change-me", env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(60 * 24 * 7, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    frontend_cors_origins: List[str] = Field(["http://localhost:3000"], env="FRONTEND_CORS_ORIGINS")

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()
