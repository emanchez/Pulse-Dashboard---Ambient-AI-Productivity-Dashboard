"""Ghost List Service — identifies wheel-spinning / stale tasks.

Implements Step 5 of Phase 4.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import func, select, case, literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_log import ActionLog
from app.models.task import Task
from app.models.session_log import SessionLog
from app.models.manual_report import ManualReport
from app.schemas.stats import GhostTask, GhostListResponse, WeeklySummaryResponse

# Task-related action types — only these are meaningful for ghost detection.
# Other action types (e.g. LOGIN_SUCCESS, REPORT_*) may share the task_id column
# but are irrelevant when measuring task-specific activity.
_TASK_ACTION_TYPES = (
    "TASK_CREATE", "TASK_UPDATE", "TASK_COMPLETE", "TASK_DELETE",
    "SESSION_START", "SESSION_STOP",
)

GHOST_STALE_DAYS: int = 14
GHOST_LOW_ACTIVITY: int = 2
GHOST_HIGH_EDITS: int = 5


class GhostListService:
    """Identifies 'wheel-spinning' tasks — open tasks with suspicious activity patterns."""

    async def get_ghost_list(self, user_id: str, db: AsyncSession) -> GhostListResponse:
        """Find tasks that show signs of wheel-spinning.

        Criteria:
        1. Open (not completed) for > GHOST_STALE_DAYS days
        2. With fewer than GHOST_LOW_ACTIVITY task-related actions → "stale"
        3. OR tasks with many edits (> GHOST_HIGH_EDITS) but still open → "wheel-spinning"
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = now - timedelta(days=GHOST_STALE_DAYS)

        # Sub-query: count task-related actions per task
        action_subq = (
            select(
                ActionLog.task_id,
                func.count(ActionLog.id).label("action_count"),
                func.max(ActionLog.timestamp).label("last_action"),
            )
            .where(ActionLog.user_id == user_id)
            .where(ActionLog.action_type.in_(_TASK_ACTION_TYPES))
            .group_by(ActionLog.task_id)
            .subquery()
        )

        stmt = (
            select(
                Task.id,
                Task.name,
                Task.priority,
                Task.created_at,
                func.coalesce(action_subq.c.action_count, literal(0)).label("action_count"),
                action_subq.c.last_action.label("last_action"),
            )
            .outerjoin(action_subq, action_subq.c.task_id == Task.id)
            .where(Task.user_id == user_id)
            .where(Task.is_completed == False)  # noqa: E712
            .where(Task.created_at <= cutoff)
        )

        result = await db.execute(stmt)
        rows = result.all()

        ghosts: list[GhostTask] = []
        for row in rows:
            days_open = int((now - row.created_at).total_seconds() / 86400)
            action_count = int(row.action_count)

            if action_count > GHOST_HIGH_EDITS:
                ghost_reason: Literal["stale", "wheel-spinning"] = "wheel-spinning"
            elif action_count < GHOST_LOW_ACTIVITY:
                ghost_reason = "stale"
            else:
                # Task is old but has moderate activity — not a ghost
                continue

            ghosts.append(GhostTask(
                id=row.id,
                name=row.name,
                priority=row.priority or "Medium",
                days_open=days_open,
                action_count=action_count,
                last_action_at=row.last_action,
                ghost_reason=ghost_reason,
            ))

        return GhostListResponse(ghosts=ghosts, total=len(ghosts))

    async def get_weekly_summary(self, user_id: str, db: AsyncSession) -> WeeklySummaryResponse:
        """Aggregate stats for the current week (Mon–Sun)."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Find the most recent Monday at 00:00
        days_since_monday = now.weekday()  # 0=Mon
        period_start = (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        period_end = now

        # Total actions this week
        total_actions_q = (
            select(func.count(ActionLog.id))
            .where(ActionLog.user_id == user_id)
            .where(ActionLog.timestamp >= period_start)
        )
        total_actions = (await db.execute(total_actions_q)).scalar() or 0

        # Tasks completed this week
        tasks_completed_q = (
            select(func.count(Task.id))
            .where(Task.user_id == user_id)
            .where(Task.is_completed == True)  # noqa: E712
            .where(Task.updated_at >= period_start)
        )
        tasks_completed = (await db.execute(tasks_completed_q)).scalar() or 0

        # Tasks created this week
        tasks_created_q = (
            select(func.count(Task.id))
            .where(Task.user_id == user_id)
            .where(Task.created_at >= period_start)
        )
        tasks_created = (await db.execute(tasks_created_q)).scalar() or 0

        # Reports written this week
        reports_written_q = (
            select(func.count(ManualReport.id))
            .where(ManualReport.user_id == user_id)
            .where(ManualReport.created_at >= period_start)
        )
        reports_written = (await db.execute(reports_written_q)).scalar() or 0

        # Sessions completed this week
        sessions_completed_q = (
            select(func.count(SessionLog.id))
            .where(SessionLog.user_id == user_id)
            .where(SessionLog.ended_at.is_not(None))
            .where(SessionLog.ended_at >= period_start)
        )
        sessions_completed = (await db.execute(sessions_completed_q)).scalar() or 0

        # Longest silence (gap between consecutive actions) — simplified
        # Fetch action timestamps this week, compute max gap in Python
        actions_ts_q = (
            select(ActionLog.timestamp)
            .where(ActionLog.user_id == user_id)
            .where(ActionLog.timestamp >= period_start)
            .order_by(ActionLog.timestamp.asc())
        )
        actions_ts = (await db.execute(actions_ts_q)).scalars().all()

        longest_silence_hours = 0.0
        if len(actions_ts) > 1:
            max_gap = max(
                (actions_ts[i + 1] - actions_ts[i]).total_seconds()
                for i in range(len(actions_ts) - 1)
            )
            longest_silence_hours = round(max_gap / 3600, 2)

        # Active days — distinct dates with at least one action
        active_days_q = (
            select(func.count(func.distinct(func.date(ActionLog.timestamp))))
            .where(ActionLog.user_id == user_id)
            .where(ActionLog.timestamp >= period_start)
        )
        active_days = (await db.execute(active_days_q)).scalar() or 0

        return WeeklySummaryResponse(
            total_actions=total_actions,
            tasks_completed=tasks_completed,
            tasks_created=tasks_created,
            reports_written=reports_written,
            sessions_completed=sessions_completed,
            longest_silence_hours=longest_silence_hours,
            active_days=active_days,
            period_start=period_start,
            period_end=period_end,
        )
