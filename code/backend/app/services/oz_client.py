"""Async wrapper around the OZ (Warp) Agent API.

Aligned with the Oz REST API reference (https://docs.warp.dev/reference/api-and-sdk/agent):
  - POST /agent/runs   — create a run (preferred endpoint)
  - GET  /agent/runs/{runId} — get run details
  - POST /agent/runs/{runId}/cancel — cancel a run

COST WARNING: Every call to run_prompt() / submit_run() consumes OZ credits.
- Always use mock mode in tests (oz_api_key == "" in dev).
- Default model is claude-haiku-4 (cheapest capable model).
- Never call this in background tasks or scheduled jobs without explicit user action.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from ..core.config import get_settings

logger = logging.getLogger(__name__)

OZ_BASE_URL = "https://app.warp.dev/api/v1"

# Path to the mock fixture returned when oz_api_key is empty (dev/test mode)
_MOCK_FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "mock_oz_synthesis.json"

# Oz API run states (from docs):
# QUEUED, PENDING, CLAIMED, INPROGRESS, SUCCEEDED, FAILED, BLOCKED, ERROR, CANCELLED
_TERMINAL_FAILURE_STATES = frozenset({"FAILED", "ERROR", "CANCELLED"})
_TERMINAL_SUCCESS_STATES = frozenset({"SUCCEEDED"})
_BLOCKED_STATES = frozenset({"BLOCKED"})


class ServiceDisabledError(Exception):
    """Raised when AI features are disabled via AI_ENABLED=false."""


class CircuitBreakerOpen(Exception):
    """Raised when the circuit breaker is open after consecutive failures."""


class OZClient:
    """Async OZ Agent API client with mock mode, circuit breaker, and prompt guard.

    Request body for POST /agent/runs:
    {
      "prompt": "...",               # The user-data prompt (always sent)
      "skill": "owner/repo:name",    # Top-level skill spec (takes precedence)
      "config": {
        "model_id": "...",           # LLM model
        "environment_id": "...",     # Cloud environment UID
        "skill_spec": "...",         # Fallback skill spec (if top-level absent)
        "name": "...",               # Label for grouping/filtering runs
      },
      "title": "...",                # Human-readable run title
    }
    """

    # Circuit breaker settings
    _CB_THRESHOLD = 3  # failures before opening
    _CB_COOLDOWN = 60  # seconds to wait before retrying

    def __init__(self) -> None:
        self._settings = get_settings()
        # Circuit breaker state (in-memory — fine for single-user app)
        self._consecutive_failures = 0
        self._circuit_open_until: float = 0.0

    # ── Public API ─────────────────────────────────────────────────────

    async def submit_run(self, prompt: str, title: str | None = None) -> str:
        """Submit a prompt to OZ. Returns run_id.

        Raises ServiceDisabledError if ai_enabled=False.
        Returns mock run_id if oz_api_key is empty (dev mode).
        """
        self._check_enabled()

        if self._is_mock_mode():
            logger.info("OZ mock mode active — no API call made, no credits consumed.")
            return "mock-run-id-00000"

        self._check_circuit_breaker()
        self._check_prompt_length(prompt)

        body = self._build_run_body(prompt, title=title)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{OZ_BASE_URL}/agent/runs",
                    headers=self._auth_headers(),
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
                run_id = data.get("run_id") or data.get("id") or data.get("runId", "")
                state = data.get("state", "UNKNOWN")
                at_capacity = data.get("at_capacity", False)
                logger.info(
                    "OZ run submitted: run_id=%s state=%s at_capacity=%s model=%s prompt_chars=%d",
                    run_id, state, at_capacity, self._settings.oz_model_id, len(prompt),
                )
                if self._settings.oz_skill_spec:
                    logger.info("OZ run using skill: %s", self._settings.oz_skill_spec)
                self._record_success()
                return str(run_id)
        except Exception as exc:
            self._record_failure()
            raise exc

    async def get_run_status(self, run_id: str) -> dict:
        """Get current run details. GET — does NOT consume run credits.

        Returns the full run details dict. Key fields:
          - state: QUEUED|PENDING|CLAIMED|INPROGRESS|SUCCEEDED|FAILED|BLOCKED|ERROR|CANCELLED
          - prompt: the submitted prompt
          - agent_config: resolved config
          - session_link: URL to view the agent session (when available)
        """
        if self._is_mock_mode():
            return {"state": "SUCCEEDED", "run_id": run_id, "status": "SUCCEEDED"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{OZ_BASE_URL}/agent/runs/{run_id}",
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            # Normalize: the Oz API uses "state" but we also set "status" for
            # backward compatibility with existing callers that check "status"
            if "state" in data and "status" not in data:
                data["status"] = data["state"]
            return data

    async def wait_for_completion(self, run_id: str, timeout: int | None = None) -> dict:
        """Poll every 5s until SUCCEEDED/FAILED/ERROR/CANCELLED/BLOCKED.

        Raises TimeoutError if exceeded. Raises RuntimeError on terminal failure.
        Polling GET calls are lightweight and do not consume run credits.
        """
        if self._is_mock_mode():
            return self._load_mock_response()

        max_wait = timeout or self._settings.oz_max_wait_seconds
        start = time.monotonic()
        while True:
            status_data = await self.get_run_status(run_id)
            # Oz API returns "state" field
            state = (status_data.get("state") or status_data.get("status") or "").upper()

            if state in _TERMINAL_SUCCESS_STATES:
                logger.info("OZ run completed: run_id=%s", run_id)
                return status_data

            if state in _TERMINAL_FAILURE_STATES:
                status_msg = status_data.get("status_message", {})
                error_detail = status_msg.get("message", "") if isinstance(status_msg, dict) else ""
                raise RuntimeError(
                    f"OZ run {run_id} ended with state: {state}"
                    + (f" — {error_detail}" if error_detail else "")
                )

            if state in _BLOCKED_STATES:
                logger.warning(
                    "OZ run %s is BLOCKED (may need user input/approval). "
                    "Treating as failure for automated pipeline.",
                    run_id,
                )
                raise RuntimeError(
                    f"OZ run {run_id} is BLOCKED — may require manual approval "
                    "on the Warp dashboard at https://app.warp.dev"
                )

            if time.monotonic() - start > max_wait:
                raise TimeoutError(f"OZ run {run_id} did not complete within {max_wait}s")
            await asyncio.sleep(5)

    async def run_prompt(self, prompt: str, title: str | None = None) -> dict:
        """Submit and wait for completion. Convenience method.

        This is the ONLY method that triggers a billable OZ agent run.
        Callers MUST check ai_rate_limiter before calling this.
        """
        self._check_enabled()

        if self._is_mock_mode():
            logger.info("OZ mock mode active — no API call made, no credits consumed.")
            return self._load_mock_response()

        self._check_prompt_length(prompt)
        run_id = await self.submit_run(prompt, title=title)
        return await self.wait_for_completion(run_id)

    # ── Internal helpers ───────────────────────────────────────────────

    def _build_run_body(self, prompt: str, title: str | None = None) -> dict[str, Any]:
        """Construct the POST /agent/runs request body per Oz API spec.

        Body structure:
          prompt  — the user-data context (always sent)
          skill   — top-level skill spec (if configured)
          config  — AmbientAgentConfig with model_id, environment_id, name
          title   — human-readable run title
        """
        config: dict[str, Any] = {
            "model_id": self._settings.oz_model_id,
        }

        # Environment — required for cloud agent runs
        if self._settings.oz_environment_id:
            config["environment_id"] = self._settings.oz_environment_id

        # Name — for grouping/filtering runs in the Warp dashboard
        config["name"] = "dashboard-assistant"

        body: dict[str, Any] = {
            "prompt": prompt,
            "config": config,
        }

        # Skill spec — tells Oz to use the SKILL.md as agent system instructions.
        # Top-level "skill" takes precedence over config.skill_spec per Oz docs.
        if self._settings.oz_skill_spec:
            body["skill"] = self._settings.oz_skill_spec

        if title:
            body["title"] = title

        return body

    def _check_enabled(self) -> None:
        if not self._settings.ai_enabled:
            raise ServiceDisabledError("AI features are disabled (AI_ENABLED=false)")

    def _is_mock_mode(self) -> bool:
        return self._settings.oz_api_key == "" and self._settings.app_env in ("dev", "test")

    def _check_prompt_length(self, prompt: str) -> None:
        max_chars = self._settings.oz_max_context_chars
        if len(prompt) > max_chars:
            raise ValueError(
                f"Prompt length ({len(prompt)} chars) exceeds oz_max_context_chars ({max_chars}). "
                "Truncation is the PromptBuilder's responsibility — this should not happen."
            )

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._settings.oz_api_key}"}

    def _load_mock_response(self) -> dict:
        """Load the deterministic mock fixture for dev/test."""
        if _MOCK_FIXTURE_PATH.exists():
            with open(_MOCK_FIXTURE_PATH) as f:
                return json.load(f)
        # Inline fallback if fixture file is missing
        return {
            "state": "SUCCEEDED",
            "status": "SUCCEEDED",
            "run_id": "mock-run-id-00000",
            "result": json.dumps({
                "summary": "Mock synthesis: A productive week focused on backend development.",
                "theme": "Infrastructure & Foundation",
                "commitmentScore": 7,
                "suggestedTasks": [
                    {"title": "Write unit tests for new endpoints", "priority": "high"},
                    {"title": "Update API documentation", "priority": "medium"},
                    {"title": "Refactor database queries", "priority": "low"},
                ],
            }),
        }

    # ── Circuit breaker ────────────────────────────────────────────────

    def _check_circuit_breaker(self) -> None:
        if self._consecutive_failures >= self._CB_THRESHOLD:
            if time.monotonic() < self._circuit_open_until:
                raise CircuitBreakerOpen(
                    f"Circuit breaker open — {self._consecutive_failures} consecutive failures. "
                    f"Retrying in {int(self._circuit_open_until - time.monotonic())}s."
                )
            # Cooldown expired — allow a single attempt (half-open)
            logger.info("Circuit breaker half-open — allowing retry attempt")

    def _record_success(self) -> None:
        self._consecutive_failures = 0

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._CB_THRESHOLD:
            self._circuit_open_until = time.monotonic() + self._CB_COOLDOWN
            logger.warning(
                "Circuit breaker OPEN after %d consecutive failures — cooling down for %ds",
                self._consecutive_failures,
                self._CB_COOLDOWN,
            )
