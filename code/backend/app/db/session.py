from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

from ..core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False, future=True)
async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
