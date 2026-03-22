"""Tests for InferenceContextBuilder (Step 2).

These tests exercise the context builder in isolation using the test DB.
No LLM calls are made — this service is read-only data aggregation.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.db.session import async_session
from app.models.action_log import ActionLog
from app.models.manual_report import ManualReport
from app.models.system_state import SystemState
from app.models.task import Task
from app.models.user import User
from app.core.security import get_password_hash
from app.services.inference_context import InferenceContextBuilder
from app.schemas.inference import InferenceContext

from sqlalchemy import delete, select


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _run(coro):
    """Run an async function in the current event loop."""
    return asyncio.get_event_loop().run_until_complete(coro)


async def _ensure_user(username: str = "ctx_testuser") -> User:
    """Create or fetch a test user and return the ORM object."""
    async with async_session() as session:
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            user = User(username=username, hashed_password=get_password_hash("testpass"))
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def _cleanup_user_data(user_id: str) -> None:
    """Remove all data for a user so tests are isolated."""
    async with async_session() as session:
        await session.execute(delete(ActionLog).where(ActionLog.user_id == user_id))
        await session.execute(delete(ManualReport).where(ManualReport.user_id == user_id))
        await session.execute(delete(SystemState).where(SystemState.user_id == user_id))
        await session.execute(delete(Task).where(Task.user_id == user_id))
        await session.commit()


@pytest.fixture(autouse=True)
def ctx_user():
    """Create a test user and clean up their data before each test."""
    user = _run(_ensure_user())
    _run(_cleanup_user_data(user.id))
    yield user
    _run(_cleanup_user_data(user.id))


# ---------------------------------------------------------------------------
# test_build_context_with_full_data
# ---------------------------------------------------------------------------

def test_build_context_with_full_data(ctx_user):
    """Seed user with tasks, actions, reports, system state → all fields populated."""
    now = _utcnow()
    builder = InferenceContextBuilder()

    async def _setup_and_build():
        async with async_session() as session:
            # Task
            task = Task(name="Write tests", priority="High", is_completed=False, user_id=ctx_user.id)
            session.add(task)
            await session.flush()

            # Actions (recent)
            for i in range(3):
                session.add(ActionLog(
                    timestamp=now - timedelta(hours=i * 2),
                    task_id=task.id,
                    action_type="TASK_UPDATED",
                    user_id=ctx_user.id,
                ))

            # Report
            session.add(ManualReport(
                title="Weekly progress",
                body="Made good progress on the test suite this week.",
                word_count=8,
                user_id=ctx_user.id,
            ))

            await session.commit()

            # Build context
            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_setup_and_build())
    assert isinstance(ctx, InferenceContext)
    assert len(ctx.tasks) >= 1
    assert len(ctx.reports) >= 1
    assert ctx.weekly_summary.total_actions >= 3
    assert ctx.weekly_summary.reports_written >= 1
    assert ctx.is_returning_from_leave is False


# ---------------------------------------------------------------------------
# test_silence_gap_detection
# ---------------------------------------------------------------------------

def test_silence_gap_detection(ctx_user):
    """Create actions with a 72h gap → assert one SilenceGap with ~72h duration."""
    now = _utcnow()
    builder = InferenceContextBuilder()

    async def _setup_and_build():
        async with async_session() as session:
            # Two actions with a 72-hour gap
            session.add(ActionLog(
                timestamp=now - timedelta(hours=96),
                action_type="TASK_CREATED",
                user_id=ctx_user.id,
            ))
            session.add(ActionLog(
                timestamp=now - timedelta(hours=24),
                action_type="TASK_UPDATED",
                user_id=ctx_user.id,
            ))
            await session.commit()

            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_setup_and_build())
    # Should detect a 72h gap between the two actions
    assert len(ctx.silence_gaps) >= 1
    gap_72 = [g for g in ctx.silence_gaps if 70 <= g.duration_hours <= 74]
    assert len(gap_72) == 1, f"Expected one ~72h gap, got: {[g.duration_hours for g in ctx.silence_gaps]}"
    assert gap_72[0].explained is False


# ---------------------------------------------------------------------------
# test_silence_gap_excluded_during_system_state
# ---------------------------------------------------------------------------

def test_silence_gap_excluded_during_system_state(ctx_user):
    """Create a gap overlapping a vacation → assert gap is NOT in result."""
    now = _utcnow()
    builder = InferenceContextBuilder()

    async def _setup_and_build():
        async with async_session() as session:
            # Two actions with a 72h gap
            action_early = now - timedelta(hours=96)
            action_late = now - timedelta(hours=24)
            session.add(ActionLog(
                timestamp=action_early,
                action_type="TASK_CREATED",
                user_id=ctx_user.id,
            ))
            session.add(ActionLog(
                timestamp=action_late,
                action_type="TASK_UPDATED",
                user_id=ctx_user.id,
            ))
            # SystemState covering the entire gap
            session.add(SystemState(
                mode_type="vacation",
                start_date=action_early - timedelta(hours=1),
                end_date=action_late + timedelta(hours=1),
                requires_recovery=False,
                user_id=ctx_user.id,
            ))
            await session.commit()

            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_setup_and_build())
    # The 72h gap should be excluded because a SystemState covers it
    gap_72 = [g for g in ctx.silence_gaps if 70 <= g.duration_hours <= 74]
    assert len(gap_72) == 0, f"Expected no ~72h gap (excluded by system state), got: {[g.duration_hours for g in ctx.silence_gaps]}"


# ---------------------------------------------------------------------------
# test_silence_gap_explained_by_report
# ---------------------------------------------------------------------------

def test_silence_gap_explained_by_report(ctx_user):
    """Create a gap with a report in the middle → assert explained=True."""
    now = _utcnow()
    builder = InferenceContextBuilder()

    async def _setup_and_build():
        async with async_session() as session:
            action_early = now - timedelta(hours=96)
            action_late = now - timedelta(hours=24)
            session.add(ActionLog(
                timestamp=action_early,
                action_type="TASK_CREATED",
                user_id=ctx_user.id,
            ))
            session.add(ActionLog(
                timestamp=action_late,
                action_type="TASK_UPDATED",
                user_id=ctx_user.id,
            ))
            # Report within the gap window
            session.add(ManualReport(
                title="Explaining my absence",
                body="Took a personal day to handle life admin.",
                word_count=8,
                user_id=ctx_user.id,
                created_at=now - timedelta(hours=60),  # in the middle of the 72h gap
            ))
            await session.commit()

            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_setup_and_build())
    gap_72 = [g for g in ctx.silence_gaps if 70 <= g.duration_hours <= 74]
    assert len(gap_72) == 1
    assert gap_72[0].explained is True
    assert gap_72[0].explanation == "Explaining my absence"


# ---------------------------------------------------------------------------
# test_returning_from_leave_true
# ---------------------------------------------------------------------------

def test_returning_from_leave_true(ctx_user):
    """SystemState with requiresRecovery ended within 48h → is_returning_from_leave=True."""
    now = _utcnow()
    builder = InferenceContextBuilder()

    async def _setup_and_build():
        async with async_session() as session:
            session.add(SystemState(
                mode_type="leave",
                start_date=now - timedelta(days=7),
                end_date=now - timedelta(hours=12),
                requires_recovery=True,
                user_id=ctx_user.id,
            ))
            await session.commit()

            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_setup_and_build())
    assert ctx.is_returning_from_leave is True


# ---------------------------------------------------------------------------
# test_returning_from_leave_false
# ---------------------------------------------------------------------------

def test_returning_from_leave_false(ctx_user):
    """No recent ended SystemState → is_returning_from_leave=False."""
    builder = InferenceContextBuilder()

    async def _build():
        async with async_session() as session:
            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_build())
    assert ctx.is_returning_from_leave is False


# ---------------------------------------------------------------------------
# test_returning_from_leave_false_old_state
# ---------------------------------------------------------------------------

def test_returning_from_leave_false_old_state(ctx_user):
    """SystemState with requiresRecovery ended > 48h ago → False."""
    now = _utcnow()
    builder = InferenceContextBuilder()

    async def _setup_and_build():
        async with async_session() as session:
            session.add(SystemState(
                mode_type="leave",
                start_date=now - timedelta(days=14),
                end_date=now - timedelta(hours=72),  # ended 72h ago — outside 48h window
                requires_recovery=True,
                user_id=ctx_user.id,
            ))
            await session.commit()

            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_setup_and_build())
    assert ctx.is_returning_from_leave is False


# ---------------------------------------------------------------------------
# test_empty_data
# ---------------------------------------------------------------------------

def test_empty_data(ctx_user):
    """User with no activity → valid context with zero values and empty lists."""
    builder = InferenceContextBuilder()

    async def _build():
        async with async_session() as session:
            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_build())
    assert isinstance(ctx, InferenceContext)
    assert len(ctx.tasks) == 0
    assert len(ctx.completed_tasks) == 0
    assert len(ctx.open_tasks) == 0
    assert len(ctx.silence_gaps) == 0
    assert len(ctx.reports) == 0
    assert ctx.system_state is None
    assert ctx.is_returning_from_leave is False
    assert ctx.weekly_summary.total_actions == 0
    assert ctx.weekly_summary.tasks_completed == 0
    assert ctx.weekly_summary.reports_written == 0
    assert ctx.weekly_summary.longest_silence_hours == 0.0
    assert ctx.weekly_summary.active_days == 0


# ---------------------------------------------------------------------------
# test_context_serialization
# ---------------------------------------------------------------------------

def test_context_serialization(ctx_user):
    """model_dump(by_alias=True) produces camelCase keys."""
    builder = InferenceContextBuilder()

    async def _build():
        async with async_session() as session:
            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_build())
    data = ctx.model_dump(by_alias=True)

    # Top-level keys should be camelCase
    assert "periodStart" in data
    assert "periodEnd" in data
    assert "silenceGaps" in data
    assert "completedTasks" in data
    assert "openTasks" in data
    assert "isReturningFromLeave" in data
    assert "weeklySummary" in data

    # Nested weekly summary keys
    ws = data["weeklySummary"]
    assert "totalActions" in ws
    assert "tasksCompleted" in ws
    assert "longestSilenceHours" in ws
    assert "activeDays" in ws


# ---------------------------------------------------------------------------
# test_action_log_auth_exclusion
# ---------------------------------------------------------------------------

def test_action_log_auth_exclusion(ctx_user):
    """Auth events (LOGIN_SUCCESS, LOGIN_FAILED) excluded from action counts and silence gaps."""
    now = _utcnow()
    builder = InferenceContextBuilder()

    async def _setup_and_build():
        async with async_session() as session:
            # Non-auth action
            session.add(ActionLog(
                timestamp=now - timedelta(hours=2),
                action_type="TASK_CREATED",
                user_id=ctx_user.id,
            ))
            # Auth events — should be excluded
            session.add(ActionLog(
                timestamp=now - timedelta(hours=1),
                action_type="LOGIN_SUCCESS",
                user_id=ctx_user.id,
            ))
            session.add(ActionLog(
                timestamp=now - timedelta(minutes=30),
                action_type="LOGIN_FAILED",
                user_id=ctx_user.id,
            ))
            await session.commit()

            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_setup_and_build())
    # Only the TASK_CREATED action should count
    assert ctx.weekly_summary.total_actions == 1
    assert ctx.weekly_summary.active_days == 1


# ---------------------------------------------------------------------------
# test_report_body_preview_truncation
# ---------------------------------------------------------------------------

def test_report_body_preview_truncation(ctx_user):
    """Reports with bodies > 200 chars get truncated body_preview with '...'."""
    now = _utcnow()
    builder = InferenceContextBuilder()
    long_body = "A" * 300

    async def _setup_and_build():
        async with async_session() as session:
            session.add(ManualReport(
                title="Long report",
                body=long_body,
                word_count=1,
                user_id=ctx_user.id,
            ))
            await session.commit()

            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_setup_and_build())
    assert len(ctx.reports) == 1
    assert ctx.reports[0].body_preview == "A" * 200 + "..."
    assert len(ctx.reports[0].body_preview) == 203


# ---------------------------------------------------------------------------
# test_task_action_count
# ---------------------------------------------------------------------------

def test_task_action_count(ctx_user):
    """Task action_count reflects the number of non-auth ActionLog entries."""
    now = _utcnow()
    builder = InferenceContextBuilder()

    async def _setup_and_build():
        async with async_session() as session:
            task = Task(name="Counted task", priority="Medium", is_completed=False, user_id=ctx_user.id)
            session.add(task)
            await session.flush()

            for i in range(5):
                session.add(ActionLog(
                    timestamp=now - timedelta(hours=i),
                    task_id=task.id,
                    action_type="TASK_UPDATED",
                    user_id=ctx_user.id,
                ))
            # Also add a LOGIN event for this task_id (edge case) — should not count
            session.add(ActionLog(
                timestamp=now - timedelta(hours=6),
                task_id=task.id,
                action_type="LOGIN_SUCCESS",
                user_id=ctx_user.id,
            ))
            await session.commit()

            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_setup_and_build())
    counted = [t for t in ctx.tasks if t.name == "Counted task"]
    assert len(counted) == 1
    assert counted[0].action_count == 5


# ---------------------------------------------------------------------------
# test_weekly_summary_active_days
# ---------------------------------------------------------------------------

def test_weekly_summary_active_days(ctx_user):
    """active_days counts distinct calendar days with at least one action."""
    now = _utcnow()
    builder = InferenceContextBuilder()

    async def _setup_and_build():
        async with async_session() as session:
            # Actions on 3 distinct days
            for day_offset in [0, 1, 3]:
                ts = now - timedelta(days=day_offset)
                session.add(ActionLog(
                    timestamp=ts,
                    action_type="TASK_UPDATED",
                    user_id=ctx_user.id,
                ))
            # Two actions on the same day (day 0)
            session.add(ActionLog(
                timestamp=now - timedelta(hours=1),
                action_type="TASK_CREATED",
                user_id=ctx_user.id,
            ))
            await session.commit()

            ctx = await builder.build(ctx_user.id, session)
            return ctx

    ctx = _run(_setup_and_build())
    assert ctx.weekly_summary.active_days == 3
    assert ctx.weekly_summary.total_actions == 4
