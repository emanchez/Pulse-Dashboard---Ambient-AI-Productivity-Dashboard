"""Provider-agnostic LLM client for AI inference.

Supports:
  - Anthropic Claude (primary — pay-per-use, best quality)
  - Groq (secondary — free tier, open-source models)

Controlled by LLM_PROVIDER env var. Empty LLM_API_KEY → mock mode (no credits).

COST WARNING: Every call to run_prompt() with a real API key consumes credits.
- Always use mock mode in tests (llm_api_key == "" in dev).
- Default Anthropic model: claude-3-5-haiku-latest (cheapest capable model).
- Never call this in background tasks or scheduled jobs without explicit user action.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Paths to mock fixtures returned when llm_api_key is empty (dev/test mode)
_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"

# Per-provider default models
_PROVIDER_DEFAULTS: dict[str, str] = {
    "anthropic": "claude-3-5-haiku-latest",
    "groq": "llama-3.1-8b-instant",
}


class ServiceDisabledError(Exception):
    """Raised when AI features are disabled via AI_ENABLED=false."""


class CircuitBreakerOpen(Exception):
    """Raised when the circuit breaker is open after consecutive failures."""


class LLMClient:
    """Provider-agnostic LLM client with mock mode, circuit breaker, and prompt guard.

    Supported providers (set via LLM_PROVIDER env var):
      - "anthropic" — Anthropic Claude via anthropic SDK
      - "groq"      — Groq Llama via groq SDK

    Mock mode: when llm_api_key == "" no real API call is made; a local
    fixture file is loaded and returned instead.
    """

    # Circuit breaker settings
    _CB_THRESHOLD = 3   # consecutive failures before opening
    _CB_COOLDOWN = 60   # seconds to wait before allowing retry

    def __init__(self) -> None:
        self._settings = get_settings()
        # Circuit breaker state (in-memory — fine for single-user app)
        self._consecutive_failures = 0
        self._circuit_open_until: float = 0.0

    # ── Public API ────────────────────────────────────────────────────

    def _is_mock_mode(self) -> bool:
        """Return True when no API key is configured (dev / test mode)."""
        return self._settings.llm_api_key == ""

    async def run_prompt(self, prompt: str, *, title: str = "inference") -> dict:
        """Run a prompt against the configured LLM provider.

        Returns:
            {"result": "<response_text_or_json_string>", "provider": "anthropic|groq|mock"}

        Raises:
            ServiceDisabledError   — when AI_ENABLED=false
            CircuitBreakerOpen     — when circuit breaker is open
            ValueError             — on oversized prompt (should be caught by PromptBuilder)
        """
        self._check_enabled()

        if self._is_mock_mode():
            logger.info("LLM mock mode active — no API call made, no credits consumed.")
            return self._load_mock_response(title)

        self._check_circuit_breaker()
        self._check_prompt_length(prompt)

        try:
            if self._settings.llm_provider == "anthropic":
                result_text = await self._call_anthropic(prompt)
            elif self._settings.llm_provider == "groq":
                result_text = await self._call_groq(prompt)
            else:
                raise ValueError(
                    f"Unknown LLM_PROVIDER: {self._settings.llm_provider!r}. "
                    "Use 'anthropic' or 'groq'."
                )
            self._record_success()
            return {"result": result_text, "provider": self._settings.llm_provider}
        except (ServiceDisabledError, CircuitBreakerOpen, ValueError):
            raise
        except Exception as exc:
            self._record_failure()
            raise exc

    # ── Provider implementations ──────────────────────────────────────

    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude and return the response text."""
        import anthropic  # type: ignore[import]

        model = self._settings.llm_model_id or _PROVIDER_DEFAULTS["anthropic"]
        client = anthropic.AsyncAnthropic(api_key=self._settings.llm_api_key)
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except anthropic.APIStatusError as exc:
            logger.error("Anthropic API error: %s", exc)
            raise

    async def _call_groq(self, prompt: str) -> str:
        """Call Groq and return the response text."""
        import groq as groq_sdk  # type: ignore[import]

        model = self._settings.llm_model_id or _PROVIDER_DEFAULTS["groq"]
        client = groq_sdk.AsyncGroq(api_key=self._settings.llm_api_key)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    # ── Mock mode ─────────────────────────────────────────────────────

    def _load_mock_response(self, title: str) -> dict:
        """Load the appropriate fixture file based on the prompt title."""
        fixture_name = self._resolve_fixture_name(title)
        fixture_path = _FIXTURES_DIR / fixture_name

        if fixture_path.exists():
            with open(fixture_path) as f:
                data = json.load(f)
            # Fixtures already have {"result": "...", "provider": "mock"} shape
            if isinstance(data, dict) and "result" in data:
                return data
            # Legacy fixture shape — wrap in expected envelope
            return {"result": json.dumps(data), "provider": "mock"}

        # Inline fallback if fixture file is missing
        logger.warning("LLM fixture not found at %s — using inline fallback", fixture_path)
        return {
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
            "provider": "mock",
        }

    @staticmethod
    def _resolve_fixture_name(title: str) -> str:
        """Map a prompt title to the appropriate mock fixture filename."""
        title_lower = title.lower()
        if "suggestion" in title_lower:
            return "mock_llm_suggestions.json"
        if "co-plan" in title_lower or "co_plan" in title_lower or "coplan" in title_lower:
            return "mock_llm_coplan.json"
        # Default: synthesis fixture
        return "mock_llm_synthesis.json"

    # ── Guards ────────────────────────────────────────────────────────

    def _check_enabled(self) -> None:
        if not self._settings.ai_enabled:
            raise ServiceDisabledError("AI features are disabled (AI_ENABLED=false)")

    def _check_prompt_length(self, prompt: str) -> None:
        max_chars = self._settings.llm_max_context_chars
        if len(prompt) > max_chars:
            raise ValueError(
                f"Prompt length ({len(prompt)} chars) exceeds llm_max_context_chars ({max_chars}). "
                "Truncation is the PromptBuilder's responsibility — this should not happen."
            )

    # ── Circuit breaker ───────────────────────────────────────────────

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
