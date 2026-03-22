# Phase 4.1.2 — Pre-Deployment LLM Abstraction Summary

**Date:** 2026-03-22  
**Branch:** `phase-4/step-1-llm-client` + `phase-4/step-2-wire-and-cleanup`

---

## Scope

Replace Warp OZ (Warp cloud agent platform) inference dependency with a generic, provider-agnostic LLM abstraction layer (`LLMClient`):

1. Build `LLMClient` supporting Anthropic Claude, Groq Llama, and mock mode (dev).
2. Wire all inference calls through `LLMClient` instead of `OZClient`.
3. Migrate database schema: rename `oz_run_id` → `llm_run_id` in all tables.
4. Purge all OZ-specific code and documentation references.
5. Ensure all 170+ tests pass with zero AI inference failures.

---

## What Was Done

### 1. LLMClient Implementation (`app/services/llm_client.py`)

Created a new provider-agnostic inference client with:

| Feature | Implementation |
|---------|-----------------|
| **Mock Mode** | Returns pre-canned fixtures when `llm_api_key == ""` (dev default) |
| **Anthropic SDK** | `AsyncAnthropic.messages.create()` with `model`, `max_tokens=4096`, system+user messages |
| **Groq SDK** | `AsyncGroq.chat.completions.create()` with `model`, system+user messages |
| **Provider Switch** | `LLM_PROVIDER` env var ("anthropic", "groq", or missing → mock) |
| **Circuit Breaker** | Opens after 3 failures, cooldown 60s, log + raise `CircuitBreakerOpen` |
| **Prompt Guard** | Validates `title` param; rejects if too short or missing |
| **Mock Routing** | Reads fixture files based on `title`: "suggestion" → suggestions, "coplan/coplan" → coplan, default → synthesis |
| **Fixture Path** | `tests/fixtures/mock_llm_*.json` (replaces `mock_oz_*.json`) |
| **Response Shape** | `{"result": str, "provider": "anthropic|groq|mock"}` — normalized across all providers |

**Fixtures** (3 JSON files):
- `mock_llm_synthesis.json` — Weekly synthesis with summary, theme, commitment score, suggested tasks
- `mock_llm_suggestions.json` — Task suggestions (title, priority, rationale)
- `mock_llm_coplan.json` — Co-planning conflict detection with resolution question

### 2. Config Refactor (`app/core/config.py`)

Replaced all OZ settings with LLM settings:

| Old Setting | New Setting | Purpose |
|-------------|-------------|---------|
| `OZ_API_KEY` | `LLM_API_KEY` | API key for Anthropic/Groq (empty → mock mode) |
| `OZ_MODEL_ID` | `LLM_MODEL_ID` | Model name (default: `claude-3-5-haiku-latest`) |
| `OZ_PROVIDER` | `LLM_PROVIDER` | Provider: `anthropic`, `groq`, or omitted (default: mock) |
| `OZ_MAX_*` | `LLM_MAX_*` | Rate limits per feature (synthesis, suggestions, coplan) |

**Key changes:**
- Added `extra="ignore"` to `SettingsConfigDict` — tolerates stale OZ env vars during transition
- Renamed `validate_oz_config()` → `validate_llm_config()`
- Settings now guard against missing API keys for real providers

### 3. Service Wiring (3 files)

**`app/services/synthesis_service.py`:**
- Import: `from ..services.llm_client import LLMClient`
- Replace `OZClient` call with `LLMClient.run_prompt()`
- Store `llm_run_id = result.get("provider")` (instead of OZ run UUID)
- Pass `llm_run_id` to `record_usage()`

**`app/services/ai_service.py`:**
- Import: `from ..services.llm_client import LLMClient`
- Both `suggest_tasks()` and `co_plan()` call `LLMClient.run_prompt()`
- Store `llm_run_id = result.get("provider")`
- Pass `llm_run_id` to `record_usage()`

**`app/api/ai.py`:**
- Import: `from ..services.llm_client import CircuitBreakerOpen, ServiceDisabledError`
- Rename `_OZ_EXCEPTION_MAP` → `_LLM_EXCEPTION_MAP`
- Update exception handler to catch `LLMClient`-sourced errors

### 4. Data Model Migrations (2 models + 1 schema)

**`app/models/synthesis.py`:**
- Rename column: `oz_run_id` → `llm_run_id`

**`app/models/ai_usage.py`:**
- Rename column: `oz_run_id` → `llm_run_id`

**`app/schemas/synthesis.py`:**
- Rename response field: `oz_run_id` → `llm_run_id`

**Database Migration** (`scripts/migrate_oz_run_id.py`):
- Idempotent SQLite `ALTER TABLE {table} RENAME COLUMN oz_run_id TO llm_run_id`
- Guards: column existence check, SQLite version >= 3.26
- Applied to: `synthesis_reports`, `ai_usage_logs`
- Status: ✅ **Migration executed successfully** against `code/backend/data/dev.db`

### 5. Configuration & Setup

**`scripts/setup_llm.py`:**
- Interactive setup prompting for `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL_ID` (optional)
- Uses idempotent `_upsert_env()` helper
- Writes to `.env`

**`.env.dev`:**
- `LLM_PROVIDER=anthropic`
- `LLM_API_KEY=` (empty → mock mode)
- `LLM_MODEL_ID=claude-3-5-haiku-latest`

**`.env.prod.example`:**
- Updated with `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL_ID`, and rate limit vars

### 6. Test Suite Refactor (17 new + 23 updated)

**New tests** (`tests/test_llm_client.py` — 17 tests):
- Mock mode fixture routing (synthesis/suggestions/coplan)
- Anthropic SDK mocked call + response parsing
- Groq SDK mocked call + response parsing
- Circuit breaker open/reset logic
- Prompt guard validation
- Service disabled error
- Config validation

**Updated tests** (`tests/test_ai.py` — 23 tests):
- Patch targets: `app.services.oz_client.OZClient` → `app.services.llm_client.LLMClient`
- Mock settings: `oz_api_key` → `llm_api_key`
- Test data: `oz_run_id=` → `llm_run_id=`
- E2E test (`tests/e2e/test_synthesis_flow.py`): `oz_run_id` → `llm_run_id` in AIUsageLog constructor

**Test suite status:**
```
170 passed, 2 warnings in 20.83s
✅ All tests green (includes 17 new LLMClient tests)
⚠️  2 warnings: InsecureKeyLengthWarning (pre-existing JWT key issue, not in scope for this phase)
```

### 7. Code Cleanup

**Deleted files:**
- `app/services/oz_client.py` (replaced by `llm_client.py`)
- `scripts/setup_oz.py` (replaced by `setup_llm.py`)
- `tests/test_oz_client.py` (covered by `test_llm_client.py`)
- `tests/fixtures/mock_oz_synthesis.json`, `mock_oz_suggestions.json`, `mock_oz_coplan.json`

**OZ References** (Active code sweep):
- ✅ 0 remaining references to `OZClient`, `oz_run_id`, `oz_api_key`, `oz_max_*` in `app/`, `tests/`, `scripts/`
- Only intentional references: `migrate_oz_run_id.py` (script to reference old column by necessity)

### 8. Documentation Updates (5 core + 1 schema)

| File | Changes |
|------|---------|
| `copilot-instructions.md` | Updated AI/LLM stack line, "LLM provider via LLMClient abstraction" rule, added Phase 4.1.2 migration note |
| `agents.md` | Rewrote §1 "Inference Engine" section (LLMClient, mock/Anthropic/Groq, 8k context window), updated code examples |
| `PDD.md` | Updated tech stack table, ADR-001 (Local-First with LLM Abstraction), Phase 4 roadmap |
| `architecture.md` | Updated `/ai/synthesize` endpoint to call LLMClient inference |
| `product.md` | Updated Phase 4 roadmap line |
| `inference_context.py` + `prompt_builder.py` | Module docstrings updated (oz_max_context_chars → llm_max_context_chars) |

---

## Acceptance Criteria — All Met ✅

| Criterion | Status | Evidence |
|-----------|--------|----------|
| OZ client replaced with generic `LLMClient` | ✅ | `app/services/llm_client.py` with mock/Anthropic/Groq providers |
| All inference routed through `LLMClient` | ✅ | `synthesis_service.py`, `ai_service.py`, `api/ai.py` updated; 0 OZClient calls remain |
| Mock mode functional (~dev default~) | ✅ | `llm_client.py` routes to fixtures; 3 mock JSON files created |
| Anthropic SDK integrated | ✅ | `AsyncAnthropic.messages.create()` with full error handling |
| Groq SDK integrated | ✅ | `AsyncGroq.chat.completions.create()` with full error handling |
| Circuit breaker implemented | ✅ | `CircuitBreakerOpen` exception; 3-failure threshold, 60s cooldown |
| DB migrated: `oz_run_id` → `llm_run_id` | ✅ | Both `synthesis_reports` and `ai_usage_logs` columns renamed in dev.db |
| Zero OZ references in active code | ✅ | grep sweep: 0 matches in `app/`, `tests/`, `scripts/` |
| All 170+ tests pass | ✅ | `pytest tests/ -v` → **170 passed, 0 failures** |
| Config supports provider switching | ✅ | `LLM_PROVIDER=anthropic|groq` via `.env`, mock mode on empty `LLM_API_KEY` |
| Setup script (`setup_llm.py`) | ✅ | Interactive prompt, idempotent `.env` upsert |
| Rate limits enforced per AI feature | ✅ | `llm_max_synthesis_per_week`, `llm_max_suggestions_per_day`, `llm_max_coplan_per_day` |

---

## Pre-Deployment Status

This phase **does not** deploy LLM inference to production (that requires Phase 4.2+). Instead, it:

- ✅ Establishes the abstraction layer (`LLMClient`) that will survive any future LLM provider changes
- ✅ Validates provider integration paths (Anthropic/Groq SDKs tested with mocked HTTP)
- ✅ Ensures all tests pass with mock mode (dev) active
- ✅ Prepares schemas, configs, and database for real inference

**Ready for deployment** when Phase 4.2 (activation phase) lands real API keys and enables non-mock mode.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Breaking `oz_run_id` → `llm_run_id` in external tooling | Pre-migration backup at `data/dev.db.pre-phase4-1-2.bak`; migration is idempotent (safe re-run) |
| Stale `.env.dev` OZ vars causing config errors | `extra="ignore"` in `SettingsConfigDict` — pydantic silently ignores unknown keys |
| Provider SDK unavailable in dev | Mock mode (empty API key) always works; fixtures + circuit breaker provide fallback |
| Test flakiness due to async refactor | All 170 tests green with pytest asyncio strict mode; circuit breaker tests validate timeout logic |

---

## Files Changed Summary

### New Files (5)
- `app/services/llm_client.py`
- `scripts/setup_llm.py`
- `scripts/migrate_oz_run_id.py`
- `tests/test_llm_client.py`
- `tests/fixtures/mock_llm_synthesis.json`, `mock_llm_suggestions.json`, `mock_llm_coplan.json`

### Modified Files (14)
- `app/core/config.py`
- `app/services/synthesis_service.py`
- `app/services/ai_service.py`
- `app/services/prompt_builder.py`
- `app/services/inference_context.py`
- `app/api/ai.py`
- `app/models/synthesis.py`
- `app/models/ai_usage.py`
- `app/schemas/synthesis.py`
- `app/main.py`
- `requirements.txt`
- `.env.dev`
- `.env.prod.example`
- `tests/test_ai.py`
- `tests/e2e/test_synthesis_flow.py`

### Deleted Files (6)
- `app/services/oz_client.py`
- `scripts/setup_oz.py`
- `tests/test_oz_client.py`
- `tests/fixtures/mock_oz_synthesis.json`, `mock_oz_suggestions.json`, `mock_oz_coplan.json`

### Documentation Updated (5)
- `copilot-instructions.md`
- `agents.md`
- `PDD.md`
- `architecture.md`
- `product.md`

### Database
- Migration script: `scripts/migrate_oz_run_id.py` (executed)
- Schema: `synthesis_reports.oz_run_id` → `llm_run_id` ✅, `ai_usage_logs.oz_run_id` → `llm_run_id` ✅

---

## Verification Checklist

- [x] `pytest tests/ -v` passes (170/170 tests)
- [x] No remaining OZ references in active code
- [x] DB migration applied: `PRAGMA table_info()` shows `llm_run_id` in both tables
- [x] Mock mode works (empty `LLM_API_KEY`)
- [x] Config validation passes (`validate_llm_config()`)
- [x] `setup_llm.py` interactive prompts work
- [x] All service layers wired to `LLMClient`
- [x] Documentation consistent across all context files

---

## Next Steps

**Phase 4.2** (Inference Activation):
1. Set real `LLM_API_KEY` + `LLM_MODEL_ID` in prod `.env`
2. Switch `LLM_PROVIDER` to `anthropic` (or `groq`)
3. Monitor circuit breaker and rate limiter metrics
4. Deploy to staging with real inference enabled

**Phase 4.3+** (Usage Analytics & Optimization):
- Track token usage per feature
- Refine prompt engineering based on synthesis quality feedback
- Cost optimization (model selection, context truncation)
