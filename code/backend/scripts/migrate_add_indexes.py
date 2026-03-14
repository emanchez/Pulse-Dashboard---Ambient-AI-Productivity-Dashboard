"""Migration script: add composite indexes for Phase 4 Step 5.

Idempotent — uses CREATE INDEX IF NOT EXISTS.
Run: cd code/backend && python scripts/migrate_add_indexes.py
"""
import asyncio
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from sqlalchemy import text
from app.db.session import engine


async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_action_logs_user_ts ON action_logs(user_id, timestamp)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_session_logs_user_ended ON session_logs(user_id, ended_at)"
        ))
    print("✓ Indexes created (or already exist).")


if __name__ == "__main__":
    asyncio.run(migrate())
