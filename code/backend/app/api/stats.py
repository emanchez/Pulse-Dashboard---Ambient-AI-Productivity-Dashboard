from datetime import datetime, timezone
from typing import Literal
from sqlalchemy import select, func
from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.db.session import get_async_session
from app.models.action_log import ActionLog, AUTH_ACTION_TYPES
from app.models.system_state import SystemState
from app.schemas.stats import PulseStatsSchema
from app.schemas.flow_state import FlowStateSchema
from app.services.flow_state import calculate_flow_state


router = APIRouter(prefix="/stats")


@router.get("/pulse", response_model=PulseStatsSchema)
async def get_pulse_stats(
    user_id: str = Depends(get_current_user),
    session=Depends(get_async_session),
):
    """
    Get pulse telemetry: silence state, last action timestamp, gap in minutes, and paused-until if applicable.

    Silence state logic:
    - paused: if active SystemState (Vacation/Leave) covering now
    - stagnant: if gap > 2880 minutes (48h) and not paused
    - engaged: otherwise (gap <= 48h or no actions)
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Get last ActionLog scoped to current user, excluding auth events
    last_action_stmt = (
        select(ActionLog)
        .where(ActionLog.user_id == user_id)
        .where(ActionLog.action_type.notin_(AUTH_ACTION_TYPES))
        .order_by(ActionLog.timestamp.desc())
        .limit(1)
    )
    result = await session.execute(last_action_stmt)
    last_action = result.scalar_one_or_none()

    if last_action:
        gap_minutes = int((now - last_action.timestamp).total_seconds() // 60)
        last_action_at = last_action.timestamp
    else:
        gap_minutes = 0
        last_action_at = None

    # Get active SystemState scoped to current user (paused if Vacation or Leave covering now)
    active_pause_stmt = (
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
    result = await session.execute(active_pause_stmt)
    active_pause = result.scalar_one_or_none()

    if active_pause:
        silence_state: Literal["paused", "stagnant", "engaged"] = "paused"
        paused_until = active_pause.end_date
    elif gap_minutes > 2880:
        silence_state = "stagnant"
        paused_until = None
    else:
        silence_state = "engaged"
        paused_until = None

    return PulseStatsSchema(
        silence_state=silence_state,
        last_action_at=last_action_at,
        gap_minutes=gap_minutes,
        paused_until=paused_until,
    )


@router.get("/flow-state", response_model=FlowStateSchema)
async def get_flow_state(
    user_id: str = Depends(get_current_user),
    db=Depends(get_async_session),
) -> FlowStateSchema:
    return await calculate_flow_state(db, user_id)