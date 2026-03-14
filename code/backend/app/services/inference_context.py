"""Inference Context Builder — assembles ambient data into structured context for AI prompts.

This service only queries and structures data — it never calls OZ.  Its output
feeds PromptBuilder, which enforces the ``oz_max_context_chars`` hard cap before
any token is sent to OZ.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.action_log import ActionLog, AUTH_ACTION_TYPES
from ..models.manual_report import ManualReport
from ..models.system_state import SystemState
from ..models.task import Task
from ..schemas.inference import (
    InferenceContext,
    ReportSummary,
    SilenceGap,
    SystemStateSummary,
    TaskSummary,
    WeeklySummary,
)


class InferenceContextBuilder:
    """Assembles ambient data into structured context for AI prompts."""

    LOOKBACK_DAYS: int = 7
    MAX_ACTIONS: int = 50
    MAX_REPORTS: int = 5
    MAX_TASKS: int = 100
    SILENCE_THRESHOLD_HOURS: float = 48.0
    RETURNING_FROM_LEAVE_HOURS: float = 48.0

    async def build(self, user_id: str, db: AsyncSession) -> InferenceContext:
        """Build full inference context for a user's last LOOKBACK_DAYS."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        since = now - timedelta(days=self.LOOKBACK_DAYS)

        # Gather raw data concurrently-safe (sequential for SQLite safety)
        tasks = await self._get_tasks(user_id, db, since)
        actions = await self._get_action_logs(user_id, db, since)
        reports = await self._get_reports(user_id, db, since)
        system_state = await self._get_system_state(user_id, db, now)
        system_states_in_window = await self._get_system_states_in_window(user_id, db, since, now)
        is_returning = await self._check_returning_from_leave(user_id, db, now)

        silence_gaps = self._compute_silence_gaps(actions, reports, system_states_in_window, now)

        completed = [t for t in tasks if t.is_completed]
        open_tasks = [t for t in tasks if not t.is_completed]

        weekly_summary = self._build_weekly_summary(actions, tasks, reports, silence_gaps, since)

        return InferenceContext(
            period_start=since,
            period_end=now,
            tasks=tasks,
            completed_tasks=completed,
            open_tasks=open_tasks,
            silence_gaps=silence_gaps,
            reports=reports,
            system_state=system_state,
            weekly_summary=weekly_summary,
            is_returning_from_leave=is_returning,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_tasks(
        self, user_id: str, db: AsyncSession, since: datetime
    ) -> list[TaskSummary]:
        """Fetch all tasks with action counts, capped at MAX_TASKS."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Sub-query: action counts per task
        action_count_sub = (
            select(
                ActionLog.task_id,
                func.count(ActionLog.id).label("action_count"),
                func.max(ActionLog.timestamp).label("last_action_at"),
            )
            .where(ActionLog.user_id == user_id)
            .where(ActionLog.action_type.notin_(AUTH_ACTION_TYPES))
            .group_by(ActionLog.task_id)
            .subquery()
        )

        stmt = (
            select(
                Task,
                func.coalesce(action_count_sub.c.action_count, 0).label("action_count"),
                action_count_sub.c.last_action_at,
            )
            .outerjoin(action_count_sub, Task.id == action_count_sub.c.task_id)
            .where(Task.user_id == user_id)
            .order_by(Task.created_at.desc())
            .limit(self.MAX_TASKS)
        )

        result = await db.execute(stmt)
        rows = result.all()

        summaries: list[TaskSummary] = []
        for row in rows:
            task = row[0]
            action_count = row[1]
            last_action_at = row[2]
            days_open = max(0, (now - task.created_at).days) if task.created_at else 0

            summaries.append(
                TaskSummary(
                    id=task.id,
                    name=task.name,
                    priority=task.priority,
                    is_completed=task.is_completed,
                    days_open=days_open,
                    action_count=action_count,
                    last_action_at=last_action_at,
                )
            )
        return summaries

    async def _get_action_logs(
        self, user_id: str, db: AsyncSession, since: datetime
    ) -> list[ActionLog]:
        """Fetch recent action logs, excluding auth events, capped at MAX_ACTIONS."""
        stmt = (
            select(ActionLog)
            .where(ActionLog.user_id == user_id)
            .where(ActionLog.action_type.notin_(AUTH_ACTION_TYPES))
            .where(ActionLog.timestamp >= since)
            .order_by(ActionLog.timestamp.asc())
            .limit(self.MAX_ACTIONS)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    def _compute_silence_gaps(
        self,
        actions: list[ActionLog],
        reports: list[ReportSummary],
        system_states: list[SystemState],
        now: datetime,
    ) -> list[SilenceGap]:
        """Identify gaps > SILENCE_THRESHOLD_HOURS between consecutive actions.

        - Cross-reference with reports to mark gaps as 'explained'.
        - Exclude gaps during active SystemState periods.
        """
        threshold = timedelta(hours=self.SILENCE_THRESHOLD_HOURS)
        gaps: list[SilenceGap] = []

        if not actions:
            return gaps

        timestamps = [a.timestamp for a in actions]

        # Check consecutive action gaps
        for i in range(len(timestamps) - 1):
            gap_start = timestamps[i]
            gap_end = timestamps[i + 1]
            duration = gap_end - gap_start
            if duration >= threshold:
                gap = self._make_gap(gap_start, gap_end, duration, reports, system_states)
                if gap is not None:
                    gaps.append(gap)

        # Check gap from last action to now (current silence)
        last_to_now = now - timestamps[-1]
        if last_to_now >= threshold:
            gap = self._make_gap(timestamps[-1], now, last_to_now, reports, system_states)
            if gap is not None:
                gaps.append(gap)

        return gaps

    def _make_gap(
        self,
        start: datetime,
        end: datetime,
        duration: timedelta,
        reports: list[ReportSummary],
        system_states: list[SystemState],
    ) -> SilenceGap | None:
        """Create a SilenceGap if the gap is not fully covered by a SystemState."""
        # Exclude gap if any SystemState overlaps it entirely
        for ss in system_states:
            ss_start = ss.start_date
            ss_end = ss.end_date
            if ss_start is None:
                continue
            # If end_date is None the state is still active — treat as covering to ∞
            if ss_end is None:
                if ss_start <= start:
                    return None
            else:
                # SystemState overlaps the gap if it covers the gap window
                if ss_start <= start and ss_end >= end:
                    return None

        # Check if any report explains the gap
        explained = False
        explanation: str | None = None
        for r in reports:
            if start <= r.created_at <= end:
                explained = True
                explanation = r.title
                break

        return SilenceGap(
            start=start,
            end=end,
            duration_hours=round(duration.total_seconds() / 3600, 2),
            explained=explained,
            explanation=explanation,
        )

    async def _get_reports(
        self, user_id: str, db: AsyncSession, since: datetime
    ) -> list[ReportSummary]:
        """Fetch recent manual reports with body preview, capped at MAX_REPORTS."""
        stmt = (
            select(ManualReport)
            .where(ManualReport.user_id == user_id)
            .where(ManualReport.created_at >= since)
            .order_by(ManualReport.created_at.desc())
            .limit(self.MAX_REPORTS)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

        summaries: list[ReportSummary] = []
        for r in rows:
            body = r.body or ""
            preview = body[:200].rstrip() + ("..." if len(body) > 200 else "")
            summaries.append(
                ReportSummary(
                    id=r.id,
                    title=r.title,
                    body_preview=preview,
                    word_count=r.word_count or len(body.split()),
                    associated_task_ids=r.associated_task_ids or [],
                    created_at=r.created_at,
                )
            )
        return summaries

    async def _get_system_state(
        self, user_id: str, db: AsyncSession, now: datetime
    ) -> SystemStateSummary | None:
        """Get current active system state, if any."""
        stmt = (
            select(SystemState)
            .where(SystemState.user_id == user_id)
            .where(SystemState.start_date <= now)
            .where(
                (SystemState.end_date.is_(None)) | (SystemState.end_date >= now)
            )
            .order_by(SystemState.start_date.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        ss = result.scalar_one_or_none()
        if ss is None:
            return None

        return SystemStateSummary(
            mode_type=ss.mode_type,
            start_date=ss.start_date,
            end_date=ss.end_date,
            requires_recovery=ss.requires_recovery or False,
            is_active=True,
        )

    async def _get_system_states_in_window(
        self, user_id: str, db: AsyncSession, since: datetime, now: datetime
    ) -> list[SystemState]:
        """Fetch all SystemStates that overlap with the lookback window."""
        stmt = (
            select(SystemState)
            .where(SystemState.user_id == user_id)
            .where(SystemState.start_date <= now)
            .where(
                (SystemState.end_date.is_(None)) | (SystemState.end_date >= since)
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _check_returning_from_leave(
        self, user_id: str, db: AsyncSession, now: datetime
    ) -> bool:
        """Check if a SystemState with requiresRecovery ended in the last 48 hours."""
        cutoff = now - timedelta(hours=self.RETURNING_FROM_LEAVE_HOURS)
        stmt = (
            select(SystemState)
            .where(SystemState.user_id == user_id)
            .where(SystemState.requires_recovery == True)  # noqa: E712
            .where(SystemState.end_date.isnot(None))
            .where(
                and_(
                    SystemState.end_date <= now,
                    SystemState.end_date >= cutoff,
                )
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _build_weekly_summary(
        self,
        actions: list[ActionLog],
        tasks: list[TaskSummary],
        reports: list[ReportSummary],
        silence_gaps: list[SilenceGap],
        since: datetime,
    ) -> WeeklySummary:
        """Aggregate weekly statistics from collected data."""
        total_actions = len(actions)
        tasks_completed = sum(1 for t in tasks if t.is_completed)
        tasks_created = sum(
            1 for t in tasks
            # We don't have raw created_at on TaskSummary, so count all tasks
            # as "created" in the window. The task query already fetches recent tasks.
        )
        reports_written = len(reports)

        # Longest silence (from gaps or 0)
        longest_silence = max(
            (g.duration_hours for g in silence_gaps), default=0.0
        )

        # Active days: distinct calendar days with at least one action
        active_days_set: set[str] = set()
        for a in actions:
            active_days_set.add(a.timestamp.strftime("%Y-%m-%d"))

        return WeeklySummary(
            total_actions=total_actions,
            tasks_completed=tasks_completed,
            tasks_created=len(tasks),
            reports_written=reports_written,
            longest_silence_hours=longest_silence,
            active_days=len(active_days_set),
        )
