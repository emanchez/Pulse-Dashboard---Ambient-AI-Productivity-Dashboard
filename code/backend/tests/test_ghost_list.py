"""Tests for Ghost List & Weekly Summary endpoints (Step 5)."""
from datetime import datetime, timedelta, timezone
import asyncio

from sqlalchemy import delete

from app.db.session import async_session
from app.models.action_log import ActionLog
from app.models.task import Task
from app.models.manual_report import ManualReport
from app.models.session_log import SessionLog
from app.models.user import User
from app.core.security import get_password_hash


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _auth_headers(client):
    r = client.post("/login", json={"username": "testuser", "password": "testpass"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_user_id() -> str:
    async def _g():
        from sqlalchemy import select
        async with async_session() as s:
            result = await s.execute(select(User).where(User.username == "testuser"))
            user = result.scalar_one()
            return user.id
    return asyncio.get_event_loop().run_until_complete(_g())


def _clear_ghost_tables():
    async def _c():
        async with async_session() as s:
            await s.execute(delete(ActionLog))
            await s.execute(delete(Task))
            await s.execute(delete(ManualReport))
            await s.execute(delete(SessionLog))
            await s.commit()
    asyncio.get_event_loop().run_until_complete(_c())


def _insert_task(user_id: str, name: str, is_completed: bool = False, days_ago: int = 0) -> str:
    """Insert a task and return its ID."""
    async def _i():
        async with async_session() as s:
            created = _now() - timedelta(days=days_ago)
            task = Task(
                name=name,
                user_id=user_id,
                is_completed=is_completed,
                priority="Medium",
                created_at=created,
                updated_at=created,
            )
            s.add(task)
            await s.commit()
            await s.refresh(task)
            return task.id
    return asyncio.get_event_loop().run_until_complete(_i())


def _insert_action(user_id: str, task_id: str, action_type: str = "TASK_UPDATE", hours_ago: float = 0):
    async def _i():
        async with async_session() as s:
            ts = _now() - timedelta(hours=hours_ago)
            s.add(ActionLog(
                timestamp=ts,
                action_type=action_type,
                task_id=task_id,
                user_id=user_id,
            ))
            await s.commit()
    asyncio.get_event_loop().run_until_complete(_i())


def _insert_report(user_id: str, title: str = "Test Report", hours_ago: float = 0):
    async def _i():
        async with async_session() as s:
            ts = _now() - timedelta(hours=hours_ago)
            s.add(ManualReport(
                title=title,
                body="Test body content for report",
                word_count=5,
                user_id=user_id,
                created_at=ts,
                updated_at=ts,
            ))
            await s.commit()
    asyncio.get_event_loop().run_until_complete(_i())


def _insert_session(user_id: str, hours_ago_start: float = 2, hours_ago_end: float = 1):
    async def _i():
        async with async_session() as s:
            s.add(SessionLog(
                user_id=user_id,
                task_name="Test Session",
                started_at=_now() - timedelta(hours=hours_ago_start),
                ended_at=_now() - timedelta(hours=hours_ago_end),
            ))
            await s.commit()
    asyncio.get_event_loop().run_until_complete(_i())


# ---------------------------------------------------------------------------
#  Ghost List Tests
# ---------------------------------------------------------------------------

def test_ghost_list_requires_auth(client):
    r = client.get("/stats/ghost-list")
    assert r.status_code == 401


def test_ghost_list_empty(client, create_user):
    """No tasks → empty ghost list."""
    _clear_ghost_tables()
    headers = _auth_headers(client)
    r = client.get("/stats/ghost-list", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["ghosts"] == []
    assert data["total"] == 0


def test_ghost_list_stale_task(client, create_user):
    """Task open 20 days with 1 action → stale."""
    _clear_ghost_tables()
    user_id = _get_user_id()
    task_id = _insert_task(user_id, "Old neglected task", days_ago=20)
    _insert_action(user_id, task_id, "TASK_CREATE", hours_ago=20 * 24)

    headers = _auth_headers(client)
    r = client.get("/stats/ghost-list", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    ghost = next(g for g in data["ghosts"] if g["name"] == "Old neglected task")
    assert ghost["ghostReason"] == "stale"
    assert ghost["daysOpen"] >= 19
    assert ghost["actionCount"] <= 1


def test_ghost_list_wheel_spinning_task(client, create_user):
    """Task open 15 days with 8 actions, not completed → wheel-spinning."""
    _clear_ghost_tables()
    user_id = _get_user_id()
    task_id = _insert_task(user_id, "Spinning in circles", days_ago=15)
    for i in range(8):
        _insert_action(user_id, task_id, "TASK_UPDATE", hours_ago=i * 24)

    headers = _auth_headers(client)
    r = client.get("/stats/ghost-list", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    ghost = next(g for g in data["ghosts"] if g["name"] == "Spinning in circles")
    assert ghost["ghostReason"] == "wheel-spinning"
    assert ghost["actionCount"] >= 6


def test_ghost_list_excludes_completed(client, create_user):
    """Completed task, even if old → not in ghost list."""
    _clear_ghost_tables()
    user_id = _get_user_id()
    _insert_task(user_id, "Done and dusted", is_completed=True, days_ago=30)

    headers = _auth_headers(client)
    r = client.get("/stats/ghost-list", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert all(g["name"] != "Done and dusted" for g in data["ghosts"])


def test_ghost_list_excludes_recent(client, create_user):
    """Task open 3 days → not old enough to be a ghost."""
    _clear_ghost_tables()
    user_id = _get_user_id()
    _insert_task(user_id, "Fresh task", days_ago=3)

    headers = _auth_headers(client)
    r = client.get("/stats/ghost-list", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert all(g["name"] != "Fresh task" for g in data["ghosts"])


def test_ghost_list_user_scoping(client, create_user, auth_headers_b):
    """Ghost tasks belong only to the authenticated user."""
    _clear_ghost_tables()
    user_id = _get_user_id()
    _insert_task(user_id, "User A ghost", days_ago=20)

    # User B should not see User A's ghosts
    r = client.get("/stats/ghost-list", headers=auth_headers_b)
    assert r.status_code == 200
    data = r.json()
    assert all(g["name"] != "User A ghost" for g in data["ghosts"])


# ---------------------------------------------------------------------------
#  Weekly Summary Tests
# ---------------------------------------------------------------------------

def test_weekly_summary_requires_auth(client):
    r = client.get("/stats/weekly-summary")
    assert r.status_code == 401


def test_weekly_summary_empty(client, create_user):
    """No activity (besides login) → all zeros except totalActions (login creates one)."""
    _clear_ghost_tables()
    headers = _auth_headers(client)
    # Clear action logs AFTER login so the LOGIN_SUCCESS entry is removed
    _clear_ghost_tables()
    r = client.get("/stats/weekly-summary", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["totalActions"] == 0
    assert data["tasksCompleted"] == 0
    assert data["tasksCreated"] == 0
    assert data["reportsWritten"] == 0
    assert data["sessionsCompleted"] == 0
    assert data["longestSilenceHours"] == 0.0
    assert data["activeDays"] == 0
    assert "periodStart" in data
    assert "periodEnd" in data


def test_weekly_summary_with_activity(client, create_user):
    """Seed actions, tasks, reports, sessions → assert correct counts."""
    _clear_ghost_tables()
    user_id = _get_user_id()

    # Create tasks (today = within the week)
    task_id = _insert_task(user_id, "Weekly task 1", days_ago=0)
    _insert_task(user_id, "Weekly task 2 (done)", is_completed=True, days_ago=0)

    # Actions
    _insert_action(user_id, task_id, "TASK_CREATE", hours_ago=2)
    _insert_action(user_id, task_id, "TASK_UPDATE", hours_ago=1)

    # Report
    _insert_report(user_id, "Weekly Report", hours_ago=1)

    # Session
    _insert_session(user_id, hours_ago_start=3, hours_ago_end=2)

    headers = _auth_headers(client)
    r = client.get("/stats/weekly-summary", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["totalActions"] >= 2
    assert data["tasksCreated"] >= 2
    assert data["tasksCompleted"] >= 1
    assert data["reportsWritten"] >= 1
    assert data["sessionsCompleted"] >= 1


# ---------------------------------------------------------------------------
#  Flow State Backward Compatibility (M-3)
# ---------------------------------------------------------------------------

def test_flow_state_backward_compat(client, auth_headers):
    """Assert response shape unchanged after SQL aggregation optimization."""
    r = client.get("/stats/flow-state", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "flowPercent" in data
    assert "changePercent" in data
    assert "windowLabel" in data
    assert "series" in data
    assert isinstance(data["series"], list)
    assert 0 <= data["flowPercent"] <= 100
    assert data["windowLabel"] == "Last 6 hours"
