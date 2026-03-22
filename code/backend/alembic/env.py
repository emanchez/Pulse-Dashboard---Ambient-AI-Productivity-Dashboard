"""Alembic environment configuration — async SQLAlchemy (aiosqlite / asyncpg).

The URL is resolved at runtime from app.core.config.get_settings().database_url
so that migrations work against both the dev SQLite DB and the production Neon
PostgreSQL instance without modifying this file.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# ── Project imports ─────────────────────────────────────────────────────────
# Import Base so its metadata is populated, then import every model module so
# their Table objects register against Base.metadata before autogenerate runs.
from app.db.base import Base  # noqa: E402

import app.models.user          # noqa: F401
import app.models.task          # noqa: F401
import app.models.action_log    # noqa: F401
import app.models.session_log   # noqa: F401
import app.models.manual_report # noqa: F401
import app.models.system_state  # noqa: F401
import app.models.ai_usage      # noqa: F401
import app.models.synthesis     # noqa: F401

from app.core.config import get_settings  # noqa: E402

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to alembic.ini values.
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for 'autogenerate' support.
target_metadata = Base.metadata


def get_url() -> str:
    """Return the database URL from application settings.

    asyncpg uses postgresql+asyncpg://...; aiosqlite uses
    sqlite+aiosqlite://... . Both are async-compatible.
    """
    return get_settings().database_url


# ---------------------------------------------------------------------------
# Offline mode (emit SQL script without a live DB connection)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations without a live DB connection."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode (run against a live DB connection, async)
# ---------------------------------------------------------------------------

def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # required for SQLite ALTER TABLE constraint changes
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations within a sync wrapper."""
    url = get_url()
    connectable = create_async_engine(url, echo=False, future=True)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for the 'online' migration mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
