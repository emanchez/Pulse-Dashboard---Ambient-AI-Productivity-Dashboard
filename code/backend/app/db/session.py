from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

from ..core.config import get_settings

settings = get_settings()

_is_sqlite = "sqlite" in settings.database_url

_engine_kwargs: dict = {
    "echo": False,
    "future": True,
}

if not _is_sqlite:
    # PostgreSQL connection pool settings (tuned for Neon serverless)
    # pool_size=5       — base pool connections kept open
    # max_overflow=10   — extra connections allowed above pool_size
    # pool_pre_ping     — test connections before use (handles Neon idle disconnects)
    # pool_recycle=300  — recycle connections every 5 min (Neon closes long-idle connections)
    _engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 300,
    })

engine = create_async_engine(settings.database_url, **_engine_kwargs)
async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Enable FK enforcement for SQLite connections (no-op on PostgreSQL)
if _is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_fk_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
