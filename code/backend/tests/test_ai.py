"""Tests for AI endpoints — Steps 3 (Synthesis) and 4 (Task Suggester, Co-Planning).

CRITICAL: All tests run in mock mode (LLM_API_KEY=""). No real LLM API calls.
Tests that exercise 429 or short-circuit paths assert LLMClient.run_prompt was NEVER called.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.db.session import async_session
from app.models.action_log import ActionLog
from app.models.ai_usage import AIUsageLog
from app.models.manual_report import ManualReport
from app.models.synthesis import SynthesisReport
from app.models.system_state import SystemState
from app.models.task import Task
from app.models.user import User
from app.core.security import get_password_hash

from sqlalchemy import delete, select, func

_FIXTURES = Path(__file__).parent / "fixtures"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Helpers — clear AI-related data between tests
# ---------------------------------------------------------------------------

def _get_user_id(client, auth_headers) -> str:
    """Extract user_id from the JWT by hitting a user-scoped endpoint."""
    # Decode from tasks endpoint — creating and deleting would be messy;
    # Instead we'll look up the user directly.
    async def _lookup():
        async with async_session() as session:
            stmt = select(User).where(User.username == "testuser")
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return user.id if user else None
    return _run(_lookup())


def _clear_ai_data(user_id: str):
    """Remove synthesis reports and usage logs for a user."""
    async def _clear():
        async with async_session() as session:
            await session.execute(delete(SynthesisReport).where(SynthesisReport.user_id == user_id))
            await session.execute(delete(AIUsageLog).where(AIUsageLog.user_id == user_id))
            await session.commit()
    _run(_clear())


def _insert_usage_logs(user_id: str, endpoint: str, count: int):
    """Insert usage log entries to simulate exhausted rate limits."""
    now = datetime.now(timezone.utc)
    async def _insert():
        async with async_session() as session:
            for i in range(count):
                entry = AIUsageLog(
                    user_id=user_id,
                    endpoint=endpoint,
                    llm_run_id=f"fake-run-{endpoint}-{i}",
                    prompt_chars=100,
                    was_mocked=False,
                    week_number=now.strftime("%G-W%V"),
                    day=now.strftime("%Y-%m-%d"),
                    timestamp=now.replace(tzinfo=None),
                )
                session.add(entry)
            await session.commit()
    _run(_insert())


def _create_report(user_id: str, title: str, body: str) -> str:
    """Create a ManualReport and return its ID."""
    async def _create():
        async with async_session() as session:
            report = ManualReport(
                title=title,
                body=body,
                word_count=len(body.split()),
                user_id=user_id,
                status="published",
            )
            session.add(report)
            await session.commit()
            await session.refresh(report)
            return report.id
    return _run(_create())


def _count_usage_logs(user_id: str, endpoint: str) -> int:
    """Count AIUsageLog entries for a user/endpoint."""
    async def _count():
        async with async_session() as session:
            stmt = select(func.count()).select_from(AIUsageLog).where(
                AIUsageLog.user_id == user_id,
                AIUsageLog.endpoint == endpoint,
            )
            result = await session.execute(stmt)
            return result.scalar() or 0
    return _run(_count())


def _create_system_state_returning(user_id: str):
    """Create a SystemState with requiresRecovery that ended recently (within 24h)."""
    now = _utcnow()
    async def _create():
        async with async_session() as session:
            ss = SystemState(
                mode_type="leave",
                start_date=now - timedelta(days=7),
                end_date=now - timedelta(hours=12),
                requires_recovery=True,
                user_id=user_id,
            )
            session.add(ss)
            await session.commit()
    _run(_create())


def _cleanup_system_states(user_id: str):
    async def _clear():
        async with async_session() as session:
            await session.execute(delete(SystemState).where(SystemState.user_id == user_id))
            await session.commit()
    _run(_clear())


# ===========================================================================
#  Step 3 — Sunday Synthesis Tests
# ===========================================================================


class TestTriggerSynthesis:
    """POST /ai/synthesis"""

    def test_trigger_synthesis_success(self, client, auth_headers):
        """Mock LLM response → 202, status=completed."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        r = client.post("/ai/synthesis", headers=auth_headers)
        assert r.status_code == 202, f"Expected 202, got {r.status_code}: {r.text}"
        data = r.json()
        assert "id" in data
        assert data["status"] in ("completed", "pending")

    def test_trigger_synthesis_unauthorized(self, client):
        """No JWT → 401."""
        r = client.post("/ai/synthesis")
        assert r.status_code == 401

    def test_trigger_synthesis_ai_disabled(self, client, auth_headers):
        """AI_ENABLED=false → synthesis stores status=failed (unit test)."""
        from app.services.synthesis_service import SynthesisService

        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        svc = SynthesisService()
        with patch.object(svc._llm_client, "_settings") as mock_llm_s:
            mock_llm_s.ai_enabled = False
            mock_llm_s.llm_api_key = ""
            mock_llm_s.app_env = "dev"

            async def _do():
                async with async_session() as db:
                    return await svc.trigger_synthesis(user_id, db)

            # The LLM client raises ServiceDisabledError, caught by try/except → status=failed
            report = _run(_do())
            assert report.status == "failed"
            assert "disabled" in report.summary.lower()
        _clear_ai_data(user_id)

    def test_trigger_synthesis_rate_limited(self, client, auth_headers):
        """Exhaust weekly synthesis cap (3) → 429. LLM must NOT be called."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)
        _insert_usage_logs(user_id, "synthesis", 3)

        with patch("app.services.llm_client.LLMClient.run_prompt", new_callable=AsyncMock) as mock_llm:
            r = client.post("/ai/synthesis", headers=auth_headers)
            assert r.status_code == 429
            data = r.json()
            assert "detail" in data
            assert "resetsIn" in data["detail"]
            # LLM must not have been called
            mock_llm.assert_not_called()

        _clear_ai_data(user_id)

    def test_trigger_synthesis_failed_run_not_counted(self, client, auth_headers):
        """LLM error → status=failed stored, no usage log entry (unit test)."""
        from app.services.synthesis_service import SynthesisService

        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        svc = SynthesisService()

        async def _run_failed():
            async with async_session() as db:
                with patch.object(svc._llm_client, "run_prompt", new_callable=AsyncMock) as mock_llm:
                    mock_llm.side_effect = RuntimeError("LLM exploded")
                    with patch.object(svc._llm_client, "_is_mock_mode", return_value=False):
                        return await svc.trigger_synthesis(user_id, db)

        report = _run(_run_failed())
        assert report.status == "failed"
        assert "LLM exploded" in report.summary

        # No usage log should exist for this failed run
        count = _count_usage_logs(user_id, "synthesis")
        assert count == 0, f"Expected 0 usage logs for failed run, got {count}"
        _clear_ai_data(user_id)


class TestGetSynthesis:
    """GET /ai/synthesis/latest and /ai/synthesis/{id}"""

    def test_get_latest_synthesis(self, client, auth_headers):
        """Create a synthesis → GET latest → 200 with fields."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        # Trigger a synthesis first (mock mode → completed)
        r = client.post("/ai/synthesis", headers=auth_headers)
        assert r.status_code == 202

        r = client.get("/ai/synthesis/latest", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data
        assert "theme" in data
        assert "commitmentScore" in data
        assert "suggestedTasks" in data
        assert "periodStart" in data
        assert "periodEnd" in data
        assert data["status"] == "completed"
        _clear_ai_data(user_id)

    def test_get_latest_synthesis_none(self, client, auth_headers):
        """No prior synthesis → 404."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)
        r = client.get("/ai/synthesis/latest", headers=auth_headers)
        assert r.status_code == 404

    def test_get_synthesis_by_id(self, client, auth_headers):
        """Create synthesis → get by ID → 200."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        r = client.post("/ai/synthesis", headers=auth_headers)
        assert r.status_code == 202
        synthesis_id = r.json()["id"]

        r = client.get(f"/ai/synthesis/{synthesis_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == synthesis_id
        _clear_ai_data(user_id)

    def test_get_synthesis_user_scoping(self, client, auth_headers, auth_headers_b):
        """Synthesis for user A → request as user B → 404."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        r = client.post("/ai/synthesis", headers=auth_headers)
        assert r.status_code == 202
        synthesis_id = r.json()["id"]

        # User B should get 404
        r = client.get(f"/ai/synthesis/{synthesis_id}", headers=auth_headers_b)
        assert r.status_code == 404
        _clear_ai_data(user_id)


# ===========================================================================
#  Step 4 — Task Suggester Tests
# ===========================================================================


class TestSuggestTasks:
    """POST /ai/suggest-tasks"""

    def test_suggest_tasks_success(self, client, auth_headers):
        """Mock LLM with suggestions → 200 with correct shape."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        r = client.post("/ai/suggest-tasks", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "suggestions" in data
        assert "isReEntryMode" in data
        assert "rationale" in data
        assert isinstance(data["suggestions"], list)
        if data["suggestions"]:
            s = data["suggestions"][0]
            assert "name" in s
            assert "priority" in s
        _clear_ai_data(user_id)

    def test_suggest_tasks_unauthorized(self, client):
        """No JWT → 401."""
        r = client.post("/ai/suggest-tasks")
        assert r.status_code == 401

    def test_suggest_tasks_ai_disabled(self, client, auth_headers):
        """AI_ENABLED=false → returns empty suggestions with error rationale (unit test)."""
        from app.services.ai_service import AIService

        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)

        svc = AIService()
        with patch.object(svc._llm_client, "_settings") as mock_llm_s:
            mock_llm_s.ai_enabled = False
            mock_llm_s.llm_api_key = ""
            mock_llm_s.app_env = "dev"

            async def _do():
                async with async_session() as db:
                    return await svc.suggest_tasks(user_id, db)

            # ServiceDisabledError is caught → returns empty suggestions
            result = _run(_do())
            assert result.suggestions == []
            assert "disabled" in result.rationale.lower() or "unable" in result.rationale.lower()
        _clear_ai_data(user_id)

    def test_suggest_tasks_re_entry_mode(self, client, auth_headers):
        """Context with is_returning_from_leave=True → isReEntryMode=True, all isLowFriction=True."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)
        _cleanup_system_states(user_id)
        _create_system_state_returning(user_id)

        r = client.post("/ai/suggest-tasks", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["isReEntryMode"] is True
        if data["suggestions"]:
            for s in data["suggestions"]:
                assert s["isLowFriction"] is True

        _cleanup_system_states(user_id)
        _clear_ai_data(user_id)

    def test_suggest_tasks_rate_limited(self, client, auth_headers):
        """Exhaust daily suggest cap (5) → 429. LLM not called."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)
        _insert_usage_logs(user_id, "suggest", 5)

        with patch("app.services.llm_client.LLMClient.run_prompt", new_callable=AsyncMock) as mock_llm:
            r = client.post("/ai/suggest-tasks", headers=auth_headers)
            assert r.status_code == 429
            mock_llm.assert_not_called()

        _clear_ai_data(user_id)


# ===========================================================================
#  Step 4 — Co-Planning Tests
# ===========================================================================


class TestCoPlan:
    """POST /ai/co-plan"""

    def test_co_plan_success(self, client, auth_headers):
        """Report with sufficient content, mock LLM → 200 with conflict analysis."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)
        report_id = _create_report(
            user_id,
            "Conflicting goals",
            "I want to refactor the entire auth system but also rebuild the frontend from scratch. "
            "Both are large initiatives that require full attention over the next two weeks. "
            "I am not sure which one to prioritize first and how to split my time effectively.",
        )

        r = client.post("/ai/co-plan", json={"reportId": report_id}, headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "hasConflict" in data
        _clear_ai_data(user_id)

    def test_co_plan_report_not_found(self, client, auth_headers):
        """Invalid report ID → 404."""
        r = client.post("/ai/co-plan", json={"reportId": "nonexistent-id"}, headers=auth_headers)
        assert r.status_code == 404

    def test_co_plan_user_scoping(self, client, auth_headers, auth_headers_b):
        """Report belongs to user A → user B gets 404."""
        user_id_a = _get_user_id(client, auth_headers)
        report_id = _create_report(
            user_id_a,
            "User A report",
            "Detailed enough report body with more than twenty words for the co-planning endpoint to actually reach the LLM call section properly.",
        )
        r = client.post("/ai/co-plan", json={"reportId": report_id}, headers=auth_headers_b)
        assert r.status_code == 404

    def test_co_plan_short_report(self, client, auth_headers):
        """Report < 20 words → hasConflict=false, no LLM call, no usage log."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)
        report_id = _create_report(user_id, "Short", "Just a few words here.")

        initial_count = _count_usage_logs(user_id, "coplan")

        with patch("app.services.llm_client.LLMClient.run_prompt", new_callable=AsyncMock) as mock_llm:
            r = client.post("/ai/co-plan", json={"reportId": report_id}, headers=auth_headers)
            assert r.status_code == 200
            data = r.json()
            assert data["hasConflict"] is False
            # LLM must not be called
            mock_llm.assert_not_called()

        # No new usage log entry
        after_count = _count_usage_logs(user_id, "coplan")
        assert after_count == initial_count
        _clear_ai_data(user_id)

    def test_co_plan_rate_limited(self, client, auth_headers):
        """Exhaust daily co-plan cap (3) → 429. LLM not called."""
        user_id = _get_user_id(client, auth_headers)
        _clear_ai_data(user_id)
        _insert_usage_logs(user_id, "coplan", 3)
        report_id = _create_report(
            user_id,
            "Big report",
            "This is a substantial report with enough words to pass the twenty word check for real co-planning analysis. "
            "It discusses multiple topics including auth refactoring and frontend rebuilds that could conflict.",
        )

        with patch("app.services.llm_client.LLMClient.run_prompt", new_callable=AsyncMock) as mock_llm:
            r = client.post("/ai/co-plan", json={"reportId": report_id}, headers=auth_headers)
            assert r.status_code == 429
            mock_llm.assert_not_called()

        _clear_ai_data(user_id)


# ===========================================================================
#  Step 4 — Accept Tasks Tests
# ===========================================================================


class TestAcceptTasks:
    """POST /ai/accept-tasks"""

    def test_accept_tasks_success(self, client, auth_headers):
        """Accept 2 tasks → 201, tasks appear in GET /tasks/."""
        payload = {
            "tasks": [
                {"name": "AI suggested task 1", "priority": "High"},
                {"name": "AI suggested task 2", "priority": "Low", "notes": "From AI"},
            ]
        }
        r = client.post("/ai/accept-tasks", json=payload, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert "createdTaskIds" in data
        assert len(data["createdTaskIds"]) == 2

        # Verify tasks appear in the task list
        tasks_r = client.get("/tasks/", headers=auth_headers)
        assert tasks_r.status_code == 200
        task_names = [t["name"] for t in tasks_r.json()]
        assert "AI suggested task 1" in task_names
        assert "AI suggested task 2" in task_names

        # Cleanup
        for tid in data["createdTaskIds"]:
            client.delete(f"/tasks/{tid}", headers=auth_headers)

    def test_accept_tasks_unauthorized(self, client):
        """No JWT → 401."""
        r = client.post("/ai/accept-tasks", json={"tasks": [{"name": "test"}]})
        assert r.status_code == 401

    def test_accept_tasks_no_rate_limit(self, client, auth_headers):
        """accept-tasks has no rate limit — never returns 429."""
        payload = {"tasks": [{"name": f"Batch task {i}"} for i in range(10)]}
        r = client.post("/ai/accept-tasks", json=payload, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert len(data["createdTaskIds"]) == 10

        # Cleanup
        for tid in data["createdTaskIds"]:
            client.delete(f"/tasks/{tid}", headers=auth_headers)

    def test_accept_tasks_action_log(self, client, auth_headers):
        """Accept a task → ActionLog entry exists for the POST request."""
        payload = {"tasks": [{"name": "AI task for action log test"}]}
        r = client.post("/ai/accept-tasks", json=payload, headers=auth_headers)
        assert r.status_code == 201
        created_ids = r.json()["createdTaskIds"]

        # Check ActionLog for the accept-tasks action
        # The ActionLogMiddleware captures POST /ai/accept-tasks
        async def _check():
            async with async_session() as session:
                stmt = (
                    select(ActionLog)
                    .order_by(ActionLog.timestamp.desc())
                    .limit(10)
                )
                result = await session.execute(stmt)
                logs = result.scalars().all()
                return any(
                    l.action_type == "AI_ACCEPT_TASKS"
                    for l in logs
                )
        has_log = _run(_check())
        assert has_log, "Expected ActionLog entry for POST /ai/accept-tasks (AI_ACCEPT_TASKS)"

        # Cleanup
        for tid in created_ids:
            client.delete(f"/tasks/{tid}", headers=auth_headers)
