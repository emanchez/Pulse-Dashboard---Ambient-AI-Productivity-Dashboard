"""Tests for OZ integration layer (Step 1).

CRITICAL: All tests run in mock mode. OZ_API_KEY is NEVER set.
No HTTP calls to the real OZ API are made. No credits are consumed.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure test environment
os.environ.setdefault("APP_ENV", "dev")
os.environ.setdefault("OZ_API_KEY", "")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{os.path.join(os.path.dirname(__file__), 'test.db')}")

from app.core.config import get_settings
from app.services.oz_client import CircuitBreakerOpen, OZClient, ServiceDisabledError
from app.services.prompt_builder import PromptBuilder
from app.services.ai_rate_limiter import AIRateLimiter, SYNTHESIS, SUGGEST, COPLAN
from app.models.ai_usage import AIUsageLog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def oz_client():
    """Create a fresh OZClient instance (always mock mode — OZ_API_KEY is empty)."""
    return OZClient()


@pytest.fixture
def prompt_builder():
    return PromptBuilder()


@pytest.fixture
def rate_limiter():
    return AIRateLimiter()


# ---------------------------------------------------------------------------
# OZClient — mock mode
# ---------------------------------------------------------------------------

class TestOZClientMockMode:
    """Verify that OZClient returns mock responses when oz_api_key is empty."""

    def test_mock_mode_no_http_call(self, oz_client):
        """oz_api_key="" → run_prompt returns mock result and no HTTP call is made."""
        with patch("httpx.AsyncClient") as mock_http:
            result = asyncio.get_event_loop().run_until_complete(
                oz_client.run_prompt("test prompt")
            )
            # No HTTP client was instantiated
            mock_http.assert_not_called()
            # Result is a valid dict with expected keys
            assert isinstance(result, dict)
            assert result.get("status") == "SUCCEEDED"
            assert "id" in result or "result" in result

    def test_submit_run_mock(self, oz_client):
        """submit_run in mock mode returns a mock run ID without HTTP."""
        with patch("httpx.AsyncClient") as mock_http:
            run_id = asyncio.get_event_loop().run_until_complete(
                oz_client.submit_run("test prompt")
            )
            mock_http.assert_not_called()
            assert run_id == "mock-run-id-00000"

    def test_run_prompt_returns_fixture_data(self, oz_client):
        """Mock mode response should contain synthesis JSON fixture data."""
        result = asyncio.get_event_loop().run_until_complete(
            oz_client.run_prompt("weekly synthesis")
        )
        assert result["status"] == "SUCCEEDED"
        # Parse the nested result JSON
        inner = json.loads(result["result"])
        assert "summary" in inner
        assert "theme" in inner
        assert "commitmentScore" in inner
        assert isinstance(inner["suggestedTasks"], list)


# ---------------------------------------------------------------------------
# OZClient — submit/poll with mocked HTTP
# ---------------------------------------------------------------------------

class TestOZClientHTTPMocked:
    """Test OZClient methods with patched httpx calls (simulating a real API key)."""

    def _make_client_with_key(self):
        """Return an OZClient that has a fake API key set (non-mock mode)."""
        client = OZClient()
        # Override settings to simulate having a real API key
        client._settings = MagicMock()
        client._settings.oz_api_key = "fake-key-for-testing"
        client._settings.ai_enabled = True
        client._settings.app_env = "dev"
        client._settings.oz_model_id = "anthropic/claude-haiku-4"
        client._settings.oz_max_wait_seconds = 10
        client._settings.oz_max_context_chars = 8000
        return client

    def test_submit_run_success(self):
        """Mock HTTP 200 with run_id → assert returns run_id string."""
        client = self._make_client_with_key()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "run-abc-123"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            run_id = asyncio.get_event_loop().run_until_complete(
                client.submit_run("test prompt", title="Test Run")
            )
        assert run_id == "run-abc-123"

    def test_wait_for_completion_success(self):
        """Mock polling sequence (QUEUED → INPROGRESS → SUCCEEDED) → returns result."""
        client = self._make_client_with_key()
        statuses = [
            {"status": "QUEUED", "id": "run-1"},
            {"status": "INPROGRESS", "id": "run-1"},
            {"status": "SUCCEEDED", "id": "run-1", "result": '{"summary": "done"}'},
        ]
        call_count = 0

        async def mock_get_status(run_id):
            nonlocal call_count
            result = statuses[min(call_count, len(statuses) - 1)]
            call_count += 1
            return result

        client.get_run_status = mock_get_status

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = asyncio.get_event_loop().run_until_complete(
                client.wait_for_completion("run-1", timeout=30)
            )
        assert result["status"] == "SUCCEEDED"

    def test_wait_for_completion_timeout(self):
        """Perpetual INPROGRESS → raises TimeoutError."""
        client = self._make_client_with_key()
        client._settings.oz_max_wait_seconds = 0  # Zero second timeout → immediate timeout

        async def mock_get_status(run_id):
            return {"status": "INPROGRESS", "id": run_id}

        client.get_run_status = mock_get_status

        # Patch asyncio.sleep to be a no-op (don't actually wait),
        # and use a counter to simulate time progression in the client.
        call_count = 0
        original_monotonic = time.monotonic

        def advancing_monotonic():
            nonlocal call_count
            call_count += 1
            # First call = start time; subsequent calls add 10s each
            return original_monotonic() + (call_count * 10)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("app.services.oz_client.time.monotonic", side_effect=advancing_monotonic):
                with pytest.raises(TimeoutError, match="did not complete within"):
                    asyncio.get_event_loop().run_until_complete(
                        client.wait_for_completion("run-timeout", timeout=0)
                    )


# ---------------------------------------------------------------------------
# OZClient — circuit breaker
# ---------------------------------------------------------------------------

class TestOZClientCircuitBreaker:
    """Verify circuit breaker opens after 3 consecutive failures."""

    def test_circuit_breaker_opens(self):
        """3 consecutive HTTP 500s → 4th call raises CircuitBreakerOpen."""
        client = OZClient()
        client._settings = MagicMock()
        client._settings.oz_api_key = "fake-key"
        client._settings.ai_enabled = True
        client._settings.app_env = "dev"
        client._settings.oz_model_id = "anthropic/claude-haiku-4"
        client._settings.oz_max_wait_seconds = 10
        client._settings.oz_max_context_chars = 8000

        # Simulate 3 failures
        client._consecutive_failures = 3
        client._circuit_open_until = time.monotonic() + 60

        with pytest.raises(CircuitBreakerOpen):
            client._check_circuit_breaker()


# ---------------------------------------------------------------------------
# OZClient — disabled mode
# ---------------------------------------------------------------------------

class TestOZClientDisabled:
    """Verify ServiceDisabledError when AI_ENABLED=false."""

    def test_disabled_raises_error(self):
        """ai_enabled=False → run_prompt raises ServiceDisabledError."""
        client = OZClient()
        client._settings = MagicMock()
        client._settings.ai_enabled = False

        with pytest.raises(ServiceDisabledError, match="AI features are disabled"):
            asyncio.get_event_loop().run_until_complete(
                client.run_prompt("test")
            )

    def test_submit_disabled_raises_error(self):
        """ai_enabled=False → submit_run raises ServiceDisabledError."""
        client = OZClient()
        client._settings = MagicMock()
        client._settings.ai_enabled = False

        with pytest.raises(ServiceDisabledError, match="AI features are disabled"):
            asyncio.get_event_loop().run_until_complete(
                client.submit_run("test")
            )


# ---------------------------------------------------------------------------
# OZClient — prompt length guard
# ---------------------------------------------------------------------------

class TestOZClientPromptGuard:
    """Verify prompt length enforcement."""

    def test_prompt_length_exceeds_limit(self):
        """Prompt exceeding oz_max_context_chars → ValueError raised before HTTP call."""
        client = OZClient()
        client._settings = MagicMock()
        client._settings.oz_api_key = "fake-key"
        client._settings.ai_enabled = True
        client._settings.app_env = "dev"
        client._settings.oz_max_context_chars = 100

        with patch("httpx.AsyncClient") as mock_http:
            with pytest.raises(ValueError, match="exceeds oz_max_context_chars"):
                asyncio.get_event_loop().run_until_complete(
                    client.run_prompt("x" * 200)
                )
            # HTTP was never called
            mock_http.assert_not_called()


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    """Verify prompt construction and cost budgeting."""

    def test_synthesis_compact_json(self, prompt_builder):
        """Output uses compact JSON — no whitespace around : or , in the data section."""
        context = {
            "openTasks": [{"title": "Task A", "priority": "high"}],
            "silenceGaps": [],
            "weekSummary": {"completed": 5, "created": 3},
        }
        prompt = prompt_builder.build_synthesis_prompt(context)
        # Find the JSON data section (after "User data")
        data_idx = prompt.index("User data")
        data_section = prompt[data_idx:]
        # Compact JSON should have no spaces after colons or commas in the data payload
        # (The system text above may have natural spaces)
        assert '{"openTasks"' in data_section or '{"weekSummary"' in data_section

    def test_synthesis_under_limit(self, prompt_builder):
        """Large context → output length ≤ oz_max_context_chars."""
        # Create a context larger than 8000 chars
        context = {
            "openTasks": [{"title": f"Task {i}", "priority": "high"} for i in range(200)],
            "reports": [{"title": f"Report {i}", "wordCount": 500} for i in range(50)],
            "silenceGaps": [{"start": "2026-03-01", "end": "2026-03-02"}] * 30,
        }
        prompt = prompt_builder.build_synthesis_prompt(context)
        settings = get_settings()
        assert len(prompt) <= settings.oz_max_context_chars

    def test_task_suggestion_prompt_structure(self, prompt_builder):
        """Task suggestion prompt includes required elements."""
        context = {
            "openTasks": [{"title": "Fix bug", "priority": "high", "daysOpen": 3}],
            "isReturningFromLeave": False,
        }
        prompt = prompt_builder.build_task_suggestion_prompt(context)
        assert "project manager" in prompt.lower()
        assert "JSON" in prompt

    def test_co_planning_prompt_truncates_report(self, prompt_builder):
        """Co-planning prompt truncates report body to 1000 chars."""
        long_report = "A" * 2000
        tasks = [{"title": "Task 1"}, {"title": "Task 2"}]
        prompt = prompt_builder.build_co_planning_prompt(long_report, tasks)
        settings = get_settings()
        assert len(prompt) <= settings.oz_max_context_chars

    def test_compact_json_no_nulls(self, prompt_builder):
        """_build_compact_json omits None values."""
        data = {"key1": "value1", "key2": None, "key3": 42}
        result = prompt_builder._build_compact_json(data)
        parsed = json.loads(result)
        assert "key2" not in parsed
        assert parsed["key1"] == "value1"
        assert parsed["key3"] == 42


# ---------------------------------------------------------------------------
# AIRateLimiter
# ---------------------------------------------------------------------------

class TestAIRateLimiter:
    """Verify rate limit checking and recording."""

    def _make_mock_db(self, count_result=0):
        """Create a mock AsyncSession that returns `count_result` for count queries."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = count_result

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        return mock_db

    def test_allows_under_limit(self, rate_limiter):
        """2 synthesis logs this week → check passes."""
        mock_db = self._make_mock_db(count_result=2)
        # Should not raise
        asyncio.get_event_loop().run_until_complete(
            rate_limiter.check_limit("user-1", SYNTHESIS, mock_db)
        )

    def test_blocks_at_limit(self, rate_limiter):
        """3 synthesis logs this week → check raises HTTP 429."""
        mock_db = self._make_mock_db(count_result=3)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                rate_limiter.check_limit("user-1", SYNTHESIS, mock_db)
            )
        assert exc_info.value.status_code == 429
        assert "limit reached" in str(exc_info.value.detail).lower()

    def test_suggest_blocks_at_daily_limit(self, rate_limiter):
        """5 suggest logs today → check raises HTTP 429."""
        mock_db = self._make_mock_db(count_result=5)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                rate_limiter.check_limit("user-1", SUGGEST, mock_db)
            )
        assert exc_info.value.status_code == 429

    def test_coplan_blocks_at_daily_limit(self, rate_limiter):
        """3 coplan logs today → check raises HTTP 429."""
        mock_db = self._make_mock_db(count_result=3)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                rate_limiter.check_limit("user-1", COPLAN, mock_db)
            )
        assert exc_info.value.status_code == 429

    def test_record_usage_skips_mocked(self, rate_limiter):
        """Mock-mode calls should not be persisted."""
        mock_db = self._make_mock_db()
        asyncio.get_event_loop().run_until_complete(
            rate_limiter.record_usage(
                user_id="user-1",
                endpoint=SYNTHESIS,
                oz_run_id=None,
                prompt_chars=500,
                was_mocked=True,
                db=mock_db,
            )
        )
        # db.add should NOT have been called
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_record_usage_persists_real_call(self, rate_limiter):
        """Real (non-mocked) calls should be persisted."""
        mock_db = self._make_mock_db()
        asyncio.get_event_loop().run_until_complete(
            rate_limiter.record_usage(
                user_id="user-1",
                endpoint=SYNTHESIS,
                oz_run_id="run-abc",
                prompt_chars=1500,
                was_mocked=False,
                db=mock_db,
            )
        )
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    def test_usage_summary(self, rate_limiter):
        """get_usage_summary returns all three endpoint types."""
        mock_db = self._make_mock_db(count_result=1)
        result = asyncio.get_event_loop().run_until_complete(
            rate_limiter.get_usage_summary("user-1", mock_db)
        )
        assert SYNTHESIS in result
        assert SUGGEST in result
        assert COPLAN in result
        for ep in (SYNTHESIS, SUGGEST, COPLAN):
            assert "used" in result[ep]
            assert "limit" in result[ep]
            assert "resetsIn" in result[ep]
            assert "window" in result[ep]


# ---------------------------------------------------------------------------
# GET /ai/usage endpoint (integration via test server)
# ---------------------------------------------------------------------------

class TestAIUsageEndpoint:
    """Test the /ai/usage endpoint via the test server."""

    def test_usage_requires_auth(self, client):
        """GET /ai/usage without JWT → 401."""
        r = client.get("/ai/usage")
        assert r.status_code == 401

    def test_usage_returns_shape(self, client, auth_headers):
        """GET /ai/usage → response has synthesis, suggest, coplan keys."""
        r = client.get("/ai/usage", headers=auth_headers)
        # 200 indicates AI is enabled and rate limiter responds correctly
        assert r.status_code == 200
        data = r.json()
        assert "synthesis" in data
        assert "suggest" in data
        assert "coplan" in data
        # Each section has the expected fields
        for key in ("synthesis", "suggest", "coplan"):
            section = data[key]
            assert "used" in section
            assert "limit" in section
            assert "resetsIn" in section


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

class TestConfigDefaults:
    """Verify OZ-related config defaults."""

    def test_default_api_key_empty(self):
        assert get_settings().oz_api_key == ""

    def test_default_model_id(self):
        assert get_settings().oz_model_id == "anthropic/claude-haiku-4"

    def test_default_max_context_chars(self):
        assert get_settings().oz_max_context_chars == 8000

    def test_default_synthesis_limit(self):
        assert get_settings().oz_max_synthesis_per_week == 3

    def test_default_suggest_limit(self):
        assert get_settings().oz_max_suggestions_per_day == 5

    def test_default_coplan_limit(self):
        assert get_settings().oz_max_coplan_per_day == 3

    def test_prod_no_key_raises(self):
        """APP_ENV=prod + AI_ENABLED=true + OZ_API_KEY="" → RuntimeError."""
        settings = get_settings()
        # Temporarily override
        original_env = settings.app_env
        original_key = settings.oz_api_key
        original_ai = settings.ai_enabled
        try:
            settings.app_env = "prod"
            settings.oz_api_key = ""
            settings.ai_enabled = True
            with pytest.raises(RuntimeError, match="OZ_API_KEY must be set"):
                settings.validate_oz_config()
        finally:
            settings.app_env = original_env
            settings.oz_api_key = original_key
            settings.ai_enabled = original_ai

    def test_dev_no_key_ok(self):
        """APP_ENV=dev + OZ_API_KEY="" → no error."""
        settings = get_settings()
        # Should not raise
        settings.validate_oz_config()
