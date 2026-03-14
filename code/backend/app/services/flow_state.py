from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, func, select, cast, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_log import ActionLog, AUTH_ACTION_TYPES
from app.schemas.flow_state import FlowPointSchema, FlowStateSchema

_WINDOW_HOURS = 6
_BUCKET_MINUTES = 30
_NUM_BUCKETS = (_WINDOW_HOURS * 60) // _BUCKET_MINUTES  # 12


def _safe_mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


async def calculate_flow_state(db: AsyncSession, user_id: str) -> FlowStateSchema:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now - timedelta(hours=_WINDOW_HOURS)

    # SQL aggregation: bucket actions into 30-minute intervals using strftime.
    # Each bucket is identified by its floored timestamp string.
    # This avoids materializing all timestamps into Python memory (M-3).
    bucket_expr = func.strftime(
        '%Y-%m-%d %H:',
        ActionLog.timestamp,
    ) + func.printf(
        '%02d',
        (cast(func.strftime('%M', ActionLog.timestamp), Integer) / _BUCKET_MINUTES) * _BUCKET_MINUTES,
    )

    stmt = (
        select(
            bucket_expr.label('bucket'),
            func.count().label('action_count'),
        )
        .where(ActionLog.user_id == user_id)
        .where(ActionLog.user_id.is_not(None))
        .where(ActionLog.timestamp >= window_start)
        .where(ActionLog.action_type.notin_(AUTH_ACTION_TYPES))
        .group_by('bucket')
        .order_by('bucket')
    )

    result = await db.execute(stmt)
    bucket_rows = result.all()

    if not bucket_rows:
        return FlowStateSchema(
            flow_percent=0,
            change_percent=0,
            window_label="Last 6 hours",
            series=[],
        )

    # Build the 12 bucket slots
    bucket_starts: list[datetime] = [
        window_start + timedelta(minutes=_BUCKET_MINUTES * i)
        for i in range(_NUM_BUCKETS)
    ]

    # Map SQL bucket keys to counts
    bucket_map: dict[str, int] = {}
    for row in bucket_rows:
        bucket_map[row.bucket] = row.action_count

    # Fill the counts array
    counts: list[int] = [0] * _NUM_BUCKETS
    for i, bs in enumerate(bucket_starts):
        key = bs.strftime('%Y-%m-%d %H:') + f'{(bs.minute // _BUCKET_MINUTES) * _BUCKET_MINUTES:02d}'
        counts[i] = bucket_map.get(key, 0)

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
