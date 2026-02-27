from __future__ import annotations

import statistics
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_log import ActionLog
from app.schemas.flow_state import FlowPointSchema, FlowStateSchema

_WINDOW_HOURS = 6
_BUCKET_MINUTES = 30
_NUM_BUCKETS = (_WINDOW_HOURS * 60) // _BUCKET_MINUTES  # 12


def _safe_mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


async def calculate_flow_state(db: AsyncSession, user_id: str) -> FlowStateSchema:
    now = datetime.utcnow()
    window_start = now - timedelta(hours=_WINDOW_HOURS)

    result = await db.execute(
        select(ActionLog.timestamp)
        .where(ActionLog.user_id == user_id)
        .where(ActionLog.user_id.is_not(None))
        .where(ActionLog.timestamp >= window_start)
        .order_by(ActionLog.timestamp.asc())
    )
    rows = result.scalars().all()

    if not rows:
        return FlowStateSchema(
            flow_percent=0,
            change_percent=0,
            window_label="Last 6 hours",
            series=[],
        )

    # Build 12 buckets
    counts: list[int] = [0] * _NUM_BUCKETS
    bucket_starts: list[datetime] = [
        window_start + timedelta(minutes=_BUCKET_MINUTES * i)
        for i in range(_NUM_BUCKETS)
    ]

    for ts in rows:
        idx = int((ts - window_start).total_seconds() // (_BUCKET_MINUTES * 60))
        idx = max(0, min(idx, _NUM_BUCKETS - 1))
        counts[idx] += 1

    max_count = max(counts) if max(counts) > 0 else 1
    scores: list[float] = [(c / max_count) * 100.0 for c in counts]

    # flow_percent = mean of last 3 buckets, clamped [0, 100]
    flow_percent = int(max(0, min(100, _safe_mean(scores[-3:]))))

    # change_percent = last 3 mean minus preceding 3 mean
    preceding_mean = _safe_mean(scores[-6:-3])
    change_percent = int(_safe_mean(scores[-3:])) - int(preceding_mean)

    series = [
        FlowPointSchema(
            time=bucket_starts[i].strftime("%-I:%M %p"),
            activity_score=round(scores[i], 2),
        )
        for i in range(_NUM_BUCKETS)
    ]

    return FlowStateSchema(
        flow_percent=flow_percent,
        change_percent=change_percent,
        window_label="Last 6 hours",
        series=series,
    )
