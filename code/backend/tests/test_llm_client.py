"""Tests for LLMClient — provider-agnostic LLM wrapper.

Covers:
- Mock mode — no API key → returns fixture
- Mock routing by title (synthesis / suggestions / coplan)
- Anthropic SDK integration (mocked)
- Groq SDK integration (mocked)
- Circuit breaker open/close behaviour
- Prompt length guard
- Config validation
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import get_settings
from app.services.llm_client import CircuitBreakerOpen, LLMClient, ServiceDisabledError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(llm_api_key: str = "", llm_provider: str = "anthropic") -> LLMClient:
    """Create an LLMClient with patched settings."""
    settings = get_settings()
    settings_copy = MagicMock()
    settings_copy.llm_api_key = llm_api_key
    settings_copy.llm_provider = llm_provider
    settings_copy.llm_model_id = "claude-3-5-haiku-latest"
    settings_copy.llm_max_context_chars = 8000
    settings_copy.ai_enabled = True

    client = LLMClient.__new__(LLMClient)
    client._settings = settings_copy
    client._consecutive_failures = 0
    client._circuit_open_until = 0.0
    return client


# ---------------------------------------------------------------------------
# Mock mode tests
# ---------------------------------------------------------------------------

def test_is_mock_mode_true_when_no_key():
    client = _make_client(llm_api_key="")
    assert client._is_mock_mode() is True


def test_is_mock_mode_false_when_key_set():
    client = _make_client(llm_api_key="sk-real-key")
    assert client._is_mock_mode() is False


@pytest.mark.asyncio
async def test_run_prompt_mock_mode_synthesis():
    """run_prompt in mock mode returns synthesis fixture for default/synthesis titles."""
    client = _make_client(llm_api_key="")
    result = await client.run_prompt("some prompt", title="Sunday Synthesis 2026-03-22")
    assert "result" in result
    assert result["provider"] == "mock"
    # result.result should be parseable JSON containing synthesis fields
    parsed = json.loads(result["result"])
    assert "summary" in parsed
    assert "commitmentScore" in parsed


@pytest.mark.asyncio
async def test_run_prompt_mock_mode_suggestions():
    """run_prompt in mock mode returns suggestions fixture for 'Task Suggestions' title."""
    client = _make_client(llm_api_key="")
    result = await client.run_prompt("some prompt", title="Task Suggestions")
    assert result["provider"] == "mock"
    parsed = json.loads(result["result"])
    assert isinstance(parsed, list)
    assert len(parsed) > 0
    assert "title" in parsed[0]


@pytest.mark.asyncio
async def test_run_prompt_mock_mode_coplan():
    """run_prompt in mock mode returns coplan fixture for 'Co-Planning Analysis' title."""
    client = _make_client(llm_api_key="")
    result = await client.run_prompt("some prompt", title="Co-Planning Analysis")
    assert result["provider"] == "mock"
    parsed = json.loads(result["result"])
    assert "hasConflict" in parsed


@pytest.mark.asyncio
async def test_run_prompt_default_fixture_fallback():
    """run_prompt with unrecognised title falls back to synthesis fixture."""
    client = _make_client(llm_api_key="")
    result = await client.run_prompt("some prompt", title="unknown title")
    assert result["provider"] == "mock"
    parsed = json.loads(result["result"])
    assert "summary" in parsed


# ---------------------------------------------------------------------------
# Fixture routing
# ---------------------------------------------------------------------------

def test_resolve_fixture_name_synthesis():
    assert LLMClient._resolve_fixture_name("Sunday Synthesis 2026-03-22") == "mock_llm_synthesis.json"


def test_resolve_fixture_name_suggestions():
    assert LLMClient._resolve_fixture_name("Task Suggestions") == "mock_llm_suggestions.json"


def test_resolve_fixture_name_coplan():
    assert LLMClient._resolve_fixture_name("Co-Planning Analysis") == "mock_llm_coplan.json"
    assert LLMClient._resolve_fixture_name("co_plan") == "mock_llm_coplan.json"


def test_resolve_fixture_name_default():
    assert LLMClient._resolve_fixture_name("something else") == "mock_llm_synthesis.json"


# ---------------------------------------------------------------------------
# Anthropic real-call path (mocked SDK)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_prompt_anthropic_real():
    """run_prompt calls Anthropic SDK and wraps response in correct shape."""
    client = _make_client(llm_api_key="sk-anthropic-fake", llm_provider="anthropic")

    mock_content = MagicMock()
    mock_content.text = '{"summary": "Test synthesis", "theme": "Testing", "commitmentScore": 8, "suggestedTasks": []}'

    mock_response = MagicMock()
    mock_response.content = [mock_content]

    mock_client_instance = AsyncMock()
    mock_client_instance.messages.create = AsyncMock(return_value=mock_response)

    mock_anthropic_module = MagicMock()
    mock_anthropic_module.AsyncAnthropic.return_value = mock_client_instance

    with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
        result = await client.run_prompt("test prompt", title="Sunday Synthesis")

    assert result["provider"] == "anthropic"
    assert "summary" in result["result"]


# ---------------------------------------------------------------------------
# Groq real-call path (mocked SDK)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_prompt_groq_real():
    """run_prompt calls Groq SDK and wraps response in correct shape."""
    client = _make_client(llm_api_key="gsk-groq-fake", llm_provider="groq")

    mock_message = MagicMock()
    mock_message.content = '{"summary": "Groq synthesis", "theme": "Testing", "commitmentScore": 6, "suggestedTasks": []}'

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_groq_client = AsyncMock()
    mock_groq_client.chat.completions.create = AsyncMock(return_value=mock_response)

    mock_groq_module = MagicMock()
    mock_groq_module.AsyncGroq.return_value = mock_groq_client

    with patch.dict("sys.modules", {"groq": mock_groq_module}):
        result = await client.run_prompt("test prompt", title="Sunday Synthesis")

    assert result["provider"] == "groq"
    assert "summary" in result["result"]


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold():
    """Circuit breaker opens after _CB_THRESHOLD consecutive failures."""
    client = _make_client(llm_api_key="sk-fake", llm_provider="anthropic")

    mock_anthropic = MagicMock()
    mock_client_instance = AsyncMock()
    mock_client_instance.messages.create = AsyncMock(side_effect=RuntimeError("API down"))
    mock_anthropic.AsyncAnthropic.return_value = mock_client_instance
    mock_anthropic.APIStatusError = RuntimeError

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        for _ in range(client._CB_THRESHOLD):
            with pytest.raises(RuntimeError):
                await client.run_prompt("test")

    assert client._consecutive_failures >= client._CB_THRESHOLD

    with pytest.raises(CircuitBreakerOpen):
        await client.run_prompt("test")


@pytest.mark.asyncio
async def test_circuit_breaker_resets_after_cooldown():
    """Circuit breaker allows a retry after the cooldown period expires."""
    client = _make_client(llm_api_key="sk-fake", llm_provider="anthropic")
    # Force circuit open
    client._consecutive_failures = client._CB_THRESHOLD
    client._circuit_open_until = time.monotonic() - 1  # expired cooldown

    mock_content = MagicMock()
    mock_content.text = '{"summary": "recovered", "theme": "Recovery", "commitmentScore": 5, "suggestedTasks": []}'
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    mock_anthropic = MagicMock()
    mock_anthropic.AsyncAnthropic.return_value = mock_client
    mock_anthropic.APIStatusError = RuntimeError

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        result = await client.run_prompt("test")

    assert result["provider"] == "anthropic"
    assert client._consecutive_failures == 0  # reset after success


# ---------------------------------------------------------------------------
# Prompt length guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prompt_guard_raises_on_oversized_prompt():
    """Raise ValueError when prompt exceeds llm_max_context_chars."""
    client = _make_client(llm_api_key="sk-fake")
    client._settings.llm_max_context_chars = 50

    with pytest.raises(ValueError, match="llm_max_context_chars"):
        await client.run_prompt("x" * 51)


# ---------------------------------------------------------------------------
# Service disabled
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_disabled_raises():
    """Raise ServiceDisabledError when AI_ENABLED=false."""
    client = _make_client(llm_api_key="")
    client._settings.ai_enabled = False

    with pytest.raises(ServiceDisabledError):
        await client.run_prompt("test")


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

def test_config_unknown_provider_raises(monkeypatch):
    """validate_llm_config raises ValueError for unknown provider."""
    monkeypatch.setenv("LLM_PROVIDER", "fakeprovider")
    get_settings.cache_clear()
    settings = get_settings()
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        settings.validate_llm_config()
    # Restore
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    get_settings.cache_clear()
