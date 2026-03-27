import asyncio
import os

# Ensure imports resolve
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
import sys
sys.path.insert(0, ROOT)

# Ensure DATABASE_URL is set before importing app modules
# For production: export APP_ENV=prod before running this script
app_env = os.environ.get("APP_ENV", "dev")
if "DATABASE_URL" not in os.environ:
    print(f"[ERROR] DATABASE_URL environment variable is not set")
    print(f"[INFO] For production: export APP_ENV=prod && export DATABASE_URL=<your-prod-db-url>")
    sys.exit(1)

from app.db.session import async_session, engine
from app.models.user import User
from app.core.security import get_password_hash
from app.db.base import Base

async def main():
    # Ensure DB and tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        from sqlalchemy import select
        q = await session.execute(select(User).where(User.username == "guestuser"))
        existing = q.scalars().first()
        if existing:
            # Preserve the existing user ID so orphaned data is never created.
            # Only reset the password so the script remains idempotent.
            existing.hashed_password = get_password_hash("guestpass1")
            await session.commit()
            print(f"guestuser already exists (id={existing.id}) — password reset to guestpass1. ID preserved.")
        else:
            user = User(username="guestuser", hashed_password=get_password_hash("guestpass1"))
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"Created user guestuser / guestpass1 (id={user.id})")

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
