"""E2E integration tests for the full Phase 4 synthesis pipeline.

Tests the complete flow: login → synthesis → accept tasks → ghost list → rate limits.
All tests use mock LLM mode (no real API calls).

Rate limit tests insert usage logs directly into the shared SQLite test.db
with was_mocked=False to simulate real LLM calls being counted against caps.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.db.session import async_session
from app.models.ai_usage import AIUsageLog
from app.models.manual_report import ManualReport
from app.models.synthesis import SynthesisReport
from app.models.user import User

from sqlalchemy import delete, select


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_user_id(client, auth_headers) -> str:
    """Look up user_id from DB."""
    async def _lookup():
        async with async_session() as session:
            stmt = select(User).where(User.username == "testuser")
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return str(user.id) if user else None
    uid = _run(_lookup())
    assert uid is not None, "testuser must exist"
    return uid


def _clear_ai_data(user_id: str):
    """Remove synthesis reports and usage logs for a user."""
    async def _clear():
        async with async_session() as session:
            await session.execute(
                delete(SynthesisReport).where(SynthesisReport.user_id == user_id)
            )
            await session.execute(
                delete(AIUsageLog).where(AIUsageLog.user_id == user_id)
            )
            await session.commit()
    _run(_clear())


def _insert_usage_logs(user_id: str, endpoint: str, count: int):
    """Insert AI usage logs to simulate exhausted quotas.

    Uses was_mocked=False so the rate limiter counts them.
    Sets week_number and day to the current period for window matching.
    """
    now = datetime.now(timezone.utc)

    async def _insert():
        async with async_session() as session:
            for i in range(count):
                log = AIUsageLog(
                    user_id=user_id,
                    endpoint=endpoint,
                    llm_run_id=f"fake-e2e-run-{endpoint}-{i}",
                    prompt_chars=100,
                    was_mocked=False,
                    week_number=now.strftime("%G-W%V"),
                    day=now.strftime("%Y-%m-%d"),
                    timestamp=_utcnow() - timedelta(minutes=i),
                )
                session.add(log)
            await session.commit()
    _run(_insert())


# ---------------------------------------------------------------------------
# Test: Full synthesis pipeline
# ---------------------------------------------------------------------------

class TestFullSynthesisFlow:
    """Complete e2e: login → trigger synthesis → fetch result → accept task."""

    def test_full_synthesis_flow(self, client, auth_headers):
        """Exercise the full synthesis → accept pipeline in mock mode."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        # Create some tasks via API so action logs are generated
        task_ids = []
        for i in range(3):
            r = client.post("/tasks/", json={"name": f"Synth Test Task {i}"}, headers=auth_headers)
            assert r.status_code == 201
            task_ids.append(r.json()["id"])

        # 1. Trigger synthesis
        r = client.post("/ai/synthesis", json={}, headers=auth_headers)
        assert r.status_code == 202, f"Expected 202, got {r.status_code}: {r.text}"
        data = r.json()
        assert "id" in data
        assert data["status"] in ("completed", "pending")
        synthesis_id = data["id"]

        # 2. Fetch latest synthesis
        r = client.get("/ai/synthesis/latest", headers=auth_headers)
        assert r.status_code == 200
        synthesis = r.json()
        assert synthesis["id"] == synthesis_id
        assert "summary" in synthesis
        assert "theme" in synthesis
        assert "commitmentScore" in synthesis
        assert isinstance(synthesis["commitmentScore"], (int, float))

        # 3. Fetch by ID
        r = client.get(f"/ai/synthesis/{synthesis_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == synthesis_id

        # 4. Suggest tasks
        r = client.post("/ai/suggest-tasks", json={}, headers=auth_headers)
        assert r.status_code == 200
        suggestions = r.json()
        assert "suggestions" in suggestions
        assert isinstance(suggestions["suggestions"], list)

        # 5. Accept a task (if suggestions exist)
        if suggestions["suggestions"]:
            task = suggestions["suggestions"][0]
            r = client.post(
                "/ai/accept-tasks",
                json={"tasks": [{"name": task["name"], "priority": task.get("priority", "Medium")}]},
                headers=auth_headers,
            )
            assert r.status_code == 201
            assert "createdTaskIds" in r.json()
            assert len(r.json()["createdTaskIds"]) == 1

        # 6. Verify usage endpoint shape
        r = client.get("/ai/usage", headers=auth_headers)
        assert r.status_code == 200
        usage = r.json()
        assert "synthesis" in usage
        assert "suggest" in usage
        assert "coplan" in usage
        assert usage["synthesis"]["limit"] == 3
        assert "resetsIn" in usage["synthesis"]
        assert "used" in usage["synthesis"]

        # Cleanup tasks
        for tid in task_ids:
            client.delete(f"/tasks/{tid}", headers=auth_headers)
        _clear_ai_data(user_id)

    def test_ghost_list_endpoint(self, client, auth_headers):
        """Ghost list endpoint returns well-formed response."""
        r = client.get("/stats/ghost-list", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "ghosts" in data
        assert "total" in data
        assert isinstance(data["ghosts"], list)

    def test_weekly_summary_endpoint(self, client, auth_headers):
        """Weekly summary endpoint returns aggregate stats."""
        r = client.get("/stats/weekly-summary", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "totalActions" in data
        assert "tasksCompleted" in data
        assert "tasksCreated" in data
        assert "reportsWritten" in data
        assert "sessionsCompleted" in data
        assert "periodStart" in data
        assert "periodEnd" in data


# ---------------------------------------------------------------------------
# Test: Rate limit enforcement
# ---------------------------------------------------------------------------

class TestSynthesisFlowRateLimits:
    """Exhaust limits via direct DB inserts (was_mocked=False) → confirm 429."""

    def test_synthesis_rate_limit_429(self, client, auth_headers):
        """After 3 synthesis entries (the weekly cap), the next should return 429."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        # Insert 3 non-mock usage logs to exhaust the weekly limit
        _insert_usage_logs(user_id, "synthesis", 3)

        # Next synthesis should be rate limited
        r = client.post("/ai/synthesis", json={}, headers=auth_headers)
        assert r.status_code == 429, f"Expected 429, got {r.status_code}: {r.text}"

        # Suggest tasks should be unaffected (separate limit bucket)
        r = client.post("/ai/suggest-tasks", json={}, headers=auth_headers)
        assert r.status_code == 200

        _clear_ai_data(user_id)

    def test_suggest_tasks_rate_limit_429(self, client, auth_headers):
        """After 5 suggest entries (the daily cap), the next should return 429."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        _insert_usage_logs(user_id, "suggest", 5)

        r = client.post("/ai/suggest-tasks", json={}, headers=auth_headers)
        assert r.status_code == 429, f"Expected 429, got {r.status_code}: {r.text}"

        _clear_ai_data(user_id)

    def test_coplan_rate_limit_429(self, client, auth_headers):
        """After 3 co-plan entries (the daily cap), the next should return 429."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        # Create a report via API (>= 20 words to avoid short-circuit)
        long_body = " ".join(["word"] * 25) + " This has enough words for co-planning analysis."
        r = client.post(
            "/reports",
            json={"title": "Co-Plan Rate Test", "body": long_body},
            headers=auth_headers,
        )
        assert r.status_code == 201
        report_id = r.json()["id"]

        _insert_usage_logs(user_id, "coplan", 3)

        r = client.post("/ai/co-plan", json={"reportId": report_id}, headers=auth_headers)
        assert r.status_code == 429, f"Expected 429, got {r.status_code}: {r.text}"

        # Cleanup
        client.delete(f"/reports/{report_id}", headers=auth_headers)
        _clear_ai_data(user_id)

    def test_accept_tasks_never_rate_limited(self, client, auth_headers):
        """POST /ai/accept-tasks should never return 429 — no LLM call, no limit."""
        r = client.post(
            "/ai/accept-tasks",
            json={"tasks": [{"name": "Test Task", "priority": "Medium"}]},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert "createdTaskIds" in r.json()

    def test_coplan_short_report_no_slot_consumed(self, client, auth_headers):
        """Co-plan with < 20 words returns hasConflict=false without consuming a slot."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        # Create a very short report via API
        r = client.post(
            "/reports",
            json={"title": "Short Report", "body": "Too short."},
            headers=auth_headers,
        )
        assert r.status_code == 201
        report_id = r.json()["id"]

        r = client.post("/ai/co-plan", json={"reportId": report_id}, headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["hasConflict"] is False

        # Verify no usage log was created (check both mock and non-mock)
        async def _check_no_usage():
            async with async_session() as session:
                stmt = select(AIUsageLog).where(
                    AIUsageLog.user_id == user_id,
                    AIUsageLog.endpoint == "coplan",
                )
                result = await session.execute(stmt)
                return result.scalars().all()
        logs = _run(_check_no_usage())
        assert len(logs) == 0, "Short report co-plan should not consume a rate limit slot"

        # Cleanup
        client.delete(f"/reports/{report_id}", headers=auth_headers)
        _clear_ai_data(user_id)
