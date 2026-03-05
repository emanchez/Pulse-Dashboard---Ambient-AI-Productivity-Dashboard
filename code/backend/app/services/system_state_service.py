from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.system_state import SystemState, SystemStateCreate, SystemStateUpdate


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _check_overlap(
    db: AsyncSession,
    user_id: str,
    start_date: datetime,
    end_date: datetime | None,
    exclude_id: str | None = None,
) -> bool:
    """Return True if a conflicting SystemState already exists for this user."""
    stmt = select(SystemState).where(SystemState.user_id == user_id)

    if exclude_id:
        stmt = stmt.where(SystemState.id != exclude_id)

    # Overlap condition:
    # existing.start_date < new.end_date  (or new end is NULL → infinite)
    # AND (existing.end_date IS NULL OR existing.end_date > new.start_date)
    if end_date is not None:
        stmt = stmt.where(SystemState.start_date < end_date)
    # If new end_date is None (infinite), every existing record that starts
    # before infinity overlaps → no start_date filter needed.

    stmt = stmt.where(
        SystemState.end_date.is_(None) | (SystemState.end_date > start_date)
    )

    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def create_state(
    db: AsyncSession,
    user_id: str,
    data: SystemStateCreate,
) -> SystemState:
    # Naive UTC for storage (consistent with TimestampedBase pattern)
    start = data.start_date.replace(tzinfo=None) if data.start_date.tzinfo else data.start_date
    end = data.end_date.replace(tzinfo=None) if (data.end_date and data.end_date.tzinfo) else data.end_date

    if await _check_overlap(db, user_id, start, end):
        raise HTTPException(status_code=409, detail="Overlapping system state exists")

    state = SystemState(
        user_id=user_id,
        mode_type=data.mode_type,  # already lowercased by validator
        start_date=start,
        end_date=end,
        requires_recovery=data.requires_recovery,
        description=data.description,
    )
    db.add(state)
    await db.commit()
    await db.refresh(state)
    return state


async def list_states(
    db: AsyncSession,
    user_id: str,
) -> list[SystemState]:
    result = await db.execute(
        select(SystemState)
        .where(SystemState.user_id == user_id)
        .order_by(SystemState.start_date.desc())
    )
    return list(result.scalars().all())


async def get_active_state(
    db: AsyncSession,
    user_id: str,
) -> SystemState | None:
    """Matches the exact query logic used in GET /stats/pulse."""
    now = _now_naive()
    result = await db.execute(
        select(SystemState)
        .where(SystemState.user_id == user_id)
        .where(SystemState.start_date <= now)
        .where(
            SystemState.end_date.is_(None) | (SystemState.end_date >= now)
        )
        .where(func.lower(SystemState.mode_type).in_(["vacation", "leave"]))
        .order_by(
            func.coalesce(SystemState.end_date, datetime.max).desc()
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_state(
    db: AsyncSession,
    user_id: str,
    state_id: str,
) -> SystemState | None:
    result = await db.execute(
        select(SystemState)
        .where(SystemState.id == state_id)
        .where(SystemState.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_state(
    db: AsyncSession,
    user_id: str,
    state_id: str,
    data: SystemStateUpdate,
) -> SystemState | None:
    state = await get_state(db, user_id, state_id)
    if state is None:
        return None

    updates = data.model_dump(exclude_unset=True)

    # Determine effective dates after update for overlap check
    new_start = updates.get("start_date", state.start_date)
    new_end = updates.get("end_date", state.end_date)

    if new_start is not None:
        new_start = new_start.replace(tzinfo=None) if hasattr(new_start, "tzinfo") and new_start.tzinfo else new_start
    if new_end is not None:
        new_end = new_end.replace(tzinfo=None) if hasattr(new_end, "tzinfo") and new_end.tzinfo else new_end

    # Only re-check overlap if dates are changing
    if "start_date" in updates or "end_date" in updates:
        if await _check_overlap(db, user_id, new_start, new_end, exclude_id=state_id):
            raise HTTPException(status_code=409, detail="Overlapping system state exists")

    for field, value in updates.items():
        if field in {"start_date", "end_date"} and value is not None:
            value = value.replace(tzinfo=None) if hasattr(value, "tzinfo") and value.tzinfo else value
        if field == "mode_type" and value is not None:
            value = value.strip().lower()
        setattr(state, field, value)

    await db.commit()
    await db.refresh(state)
    return state


async def delete_state(
    db: AsyncSession,
    user_id: str,
    state_id: str,
) -> bool:
    state = await get_state(db, user_id, state_id)
    if state is None:
        return False
    await db.delete(state)
    await db.commit()
    return True
