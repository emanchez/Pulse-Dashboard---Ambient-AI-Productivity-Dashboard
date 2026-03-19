import asyncio
import os

# Ensure imports resolve
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
import sys
sys.path.insert(0, ROOT)
# Ensure DATABASE_URL points to a writable file under the backend directory
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{os.path.join(ROOT, 'data', 'dev.db')}")

from app.db.session import async_session, engine
from app.models.user import User
from app.core.security import get_password_hash
from app.db.base import Base

async def main():
    # ensure DB and tables exist
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        from sqlalchemy import select
        q = await session.execute(select(User).where(User.username == "devuser"))
        existing = q.scalars().first()
        if existing:
            # Preserve the existing user ID so orphaned data is never created.
            # Only reset the password so the script remains idempotent.
            existing.hashed_password = get_password_hash("devpass")
            await session.commit()
            print(f"devuser already exists (id={existing.id}) — password reset to devpass. ID preserved.")
        else:
            user = User(username="devuser", hashed_password=get_password_hash("devpass"))
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"Created user devuser / devpass (id={user.id})")

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
