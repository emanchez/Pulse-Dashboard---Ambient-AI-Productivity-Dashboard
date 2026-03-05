from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.session_log import SessionLog, SessionStartRequest


async def get_active_session(db: AsyncSession, user_id: str) -> SessionLog | None:
    result = await db.execute(
        select(SessionLog)
        .where(SessionLog.user_id == user_id)
        .where(SessionLog.ended_at.is_(None))
        .order_by(SessionLog.started_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def start_session(db: AsyncSession, user_id: str, req: SessionStartRequest) -> SessionLog:
    existing = await get_active_session(db, user_id)
    if existing is not None:
        return existing

    session_log = SessionLog(
        user_id=user_id,
        task_id=req.task_id,
        task_name=req.task_name,
        goal_minutes=req.goal_minutes,
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(session_log)
    await db.commit()
    await db.refresh(session_log)
    return session_log


async def stop_session(db: AsyncSession, user_id: str) -> SessionLog | None:
    existing = await get_active_session(db, user_id)
    if existing is None:
        return None

    existing.ended_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(existing)
    return existing
