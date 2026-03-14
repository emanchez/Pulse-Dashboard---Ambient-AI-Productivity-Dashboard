from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_log import ActionLog, AUTH_ACTION_TYPES
from app.schemas.flow_state import FlowPointSchema, FlowStateSchema

_WINDOW_HOURS = 6
_BUCKET_MINUTES = 30
_NUM_BUCKETS = (_WINDOW_HOURS * 60) // _BUCKET_MINUTES  # 12


def _safe_mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


async def calculate_flow_state(db: AsyncSession, user_id: str) -> FlowStateSchema:
    """Calculate flow state using portable SQL + Python-side bucketing.

    Instead of SQLite-specific ``strftime``/``printf``, we fetch raw timestamps
    within the 6-hour window and bucket them in Python. With a single user and
    a 6-hour window the row count is bounded (~360 max at 1 action/min).
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now - timedelta(hours=_WINDOW_HOURS)

    # Portable SQL: fetch only timestamps within the window
    stmt = (
        select(ActionLog.timestamp)
        .where(ActionLog.user_id == user_id)
        .where(ActionLog.user_id.is_not(None))
        .where(ActionLog.timestamp >= window_start)
        .where(ActionLog.action_type.notin_(AUTH_ACTION_TYPES))
    )

    result = await db.execute(stmt)
    timestamps: list[datetime] = list(result.scalars().all())

    # Build the 12 bucket slots
    bucket_starts: list[datetime] = [
        window_start + timedelta(minutes=_BUCKET_MINUTES * i)
        for i in range(_NUM_BUCKETS)
    ]

    if not timestamps:
        return FlowStateSchema(
            flow_percent=0,
            change_percent=0,
            window_label="Last 6 hours",
            series=[],
        )

    # Bucket timestamps in Python: assign each to a 30-minute slot
    counts: list[int] = [0] * _NUM_BUCKETS
    for ts in timestamps:
        offset_minutes = (ts - window_start).total_seconds() / 60
        bucket_idx = int(offset_minutes // _BUCKET_MINUTES)
        # Clamp to valid range (timestamps exactly at window boundary edge)
        if 0 <= bucket_idx < _NUM_BUCKETS:
            counts[bucket_idx] += 1

    max_count = max(counts) if max(counts) > 0 else 1
    scores: list[float] = [(c / max_count) * 100.0 for c in counts]

    # flow_percent = mean of last 3 buckets, clamped [0, 100]
    flow_percent = int(max(0, min(100, _safe_mean(scores[-3:]))))

    # change_percent = last 3 mean minus preceding 3 mean
    preceding_mean = _safe_mean(scores[-6:-3])
    change_percent = int(_safe_mean(scores[-3:])) - int(preceding_mean)

    # NOTE: %-I is POSIX (Linux/macOS). On Windows use %#I.
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
