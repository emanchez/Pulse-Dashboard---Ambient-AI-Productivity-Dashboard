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
        # Remove existing devuser if present
        from sqlalchemy import select
        q = await session.execute(select(User).where(User.username == "devuser"))
        existing = q.scalars().first()
        if existing:
            await session.delete(existing)
            await session.commit()

        user = User(username="devuser", hashed_password=get_password_hash("devpass"))
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print("Created user devuser / devpass")

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
