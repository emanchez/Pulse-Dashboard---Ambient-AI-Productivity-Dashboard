# Step 1 — LLMClient Abstraction & Config Migration

**Phase:** 4.1.2  
**Branch:** `phase-4/step-1-llm-client`

---

## Purpose

Replace `oz_client.py` with a generic `llm_client.py` that supports Anthropic Claude and Groq as interchangeable backends, controlled by a single `LLM_PROVIDER` env var. Migrate all OZ-branded settings in `config.py` to provider-agnostic names. Preserve mock mode (empty API key → return fixture) for dev and CI.

---

## Deliverables

- `code/backend/app/services/llm_client.py` — new `LLMClient` class
- `code/backend/app/core/config.py` — OZ settings replaced with LLM settings (including rate-limit caps)
- `code/backend/app/services/ai_rate_limiter.py` — references to renamed config fields updated
- `code/backend/.env.prod.example` — updated ENV var names
- `code/backend/scripts/setup_llm.py` — replaces `setup_oz.py`
- `code/backend/tests/test_llm_client.py` — full test coverage of new client
- `code/backend/tests/fixtures/mock_llm_synthesis.json` — synthesis mock fixture
- `code/backend/tests/fixtures/mock_llm_suggestions.json` — suggestions mock fixture
- `code/backend/tests/fixtures/mock_llm_coplan.json` — co-planning mock fixture
- `code/backend/requirements.txt` — `anthropic` and `groq` added

---

## Primary files to change

| File | Change |
|------|--------|
| `code/backend/app/services/llm_client.py` | **Create** — new LLM client |
| `code/backend/app/services/oz_client.py` | **Delete** after step 2 is merged |
| `code/backend/app/core/config.py` | Rename 5 fields; add `llm_provider`; remove `oz_environment_id`, `oz_skill_spec`; rename 3 rate-limit cap fields |
| `code/backend/app/services/ai_rate_limiter.py` | Update references to renamed config fields; rename `oz_run_id` param |
| `code/backend/.env.prod.example` | Rename env vars |
| `code/backend/scripts/setup_llm.py` | **Create** |
| `code/backend/requirements.txt` | Add `anthropic>=0.29.0` and `groq>=0.9.0` |
| `code/backend/tests/test_llm_client.py` | **Create** |
| `code/backend/tests/fixtures/mock_llm_synthesis.json` | **Create** |
| `code/backend/tests/fixtures/mock_llm_suggestions.json` | **Create** |
| `code/backend/tests/fixtures/mock_llm_coplan.json` | **Create** |

---

## Detailed Implementation Steps

### 1. Install dependencies

```bash
cd code/backend
pip install anthropic groq
# Pin versions in requirements.txt: anthropic>=0.29.0, groq>=0.9.0
```

### 2. Config changes — `code/backend/app/core/config.py`

Remove:
```python
oz_api_key: str = ""
oz_model_id: str = "anthropic/claude-haiku-4"
oz_environment_id: str = ""
oz_skill_spec: str = ""
oz_max_wait_seconds: int = 90
oz_max_context_chars: int = 8000
oz_max_synthesis_per_week: int = 3
oz_max_suggestions_per_day: int = 5
oz_max_coplan_per_day: int = 3
```

Replace with:
```python
# LLM inference settings (provider-agnostic)
llm_provider: str = "anthropic"       # "anthropic" | "groq"
llm_api_key: str = ""                 # Empty = mock mode
llm_model_id: str = "claude-3-5-haiku-latest"  # per-provider default
llm_max_context_chars: int = 8000

# Rate limit caps (enforced by AIRateLimiter — service layer)
llm_max_synthesis_per_week: int = 3
llm_max_suggestions_per_day: int = 5
llm_max_coplan_per_day: int = 3
```

All nine ENV var aliases must be updated accordingly (e.g. `OZ_API_KEY` → `LLM_API_KEY`, `OZ_MAX_SYNTHESIS_PER_WEEK` → `LLM_MAX_SYNTHESIS_PER_WEEK`, etc.).

Update `validate_oz_config()` → rename to `validate_llm_config()`:
```python
def validate_llm_config(self) -> None:
    if not self.llm_api_key:
        logger.warning("LLM_API_KEY is not set — running in mock mode.")
    if self.llm_provider not in ("anthropic", "groq"):
        raise ValueError(f"Unknown LLM_PROVIDER: {self.llm_provider!r}. Use 'anthropic' or 'groq'.")
```

### 2a. Update `ai_rate_limiter.py` — renamed config fields

`AIRateLimiter._get_usage()` references `self._settings.oz_max_synthesis_per_week`, `oz_max_suggestions_per_day`, and `oz_max_coplan_per_day`. Update all three references to the new `llm_max_*` names. Also rename the `oz_run_id` parameter in `record_usage()` to `llm_run_id` and update the log statement that prints `oz_run_id=`:

```python
# Before
async def record_usage(self, ..., oz_run_id: str | None, ...):
    logger.info("... oz_run_id=%s ...", ..., oz_run_id, ...)

# After
async def record_usage(self, ..., llm_run_id: str | None, ...):
    logger.info("... llm_run_id=%s ...", ..., llm_run_id, ...)
```

All callers (`synthesis_service.py`, `ai_service.py`) will be updated in step 2.

### 3. Create `code/backend/app/services/llm_client.py`

Interface contract (must match current `OZClient` return shape so services need no changes in this step):

```python
async def run_prompt(self, prompt: str, *, title: str = "inference") -> dict:
    """Returns {"result": "<json_string>", "provider": "anthropic|groq|mock"}"""
```

Key design points:
- Constructor reads `settings.llm_provider` and `settings.llm_api_key`
- **`_is_mock_mode()`:** public-ish helper (`_is_mock_mode(self) -> bool`) — returns `True` when `llm_api_key == ""`. Called by `synthesis_service.py` and `ai_service.py` to decide whether to record usage. Must be preserved on `LLMClient`.
- **Mock mode routing:** if `llm_api_key == ""`, load and return the fixture file that matches the `title` parameter:
  - title contains `"Synthesis"` → `tests/fixtures/mock_llm_synthesis.json`
  - title contains `"Suggestion"` → `tests/fixtures/mock_llm_suggestions.json`
  - title contains `"Co-Plan"` → `tests/fixtures/mock_llm_coplan.json`
  - default (no match) → `mock_llm_synthesis.json`
- **Anthropic path:** `anthropic.AsyncAnthropic(api_key=...).messages.create(...)` with `system=""` and user `prompt`
- **Groq path:** `groq.AsyncGroq(api_key=...).chat.completions.create(...)` — same interface pattern
- **Circuit breaker:** preserve `_CB_THRESHOLD=3` / `_CB_COOLDOWN=60` pattern from `oz_client.py`
- **Drop polling:** Anthropic and Groq return synchronously — remove `submit_run()` / `wait_for_completion()` entirely
- **Prompt guard:** preserve max_context_chars truncation guard
- **Return format:** wrap response text in `{"result": text, "provider": ...}` to match what `synthesis_service.py` and `ai_service.py` expect

Model defaults by provider:
- `anthropic`: `claude-3-5-haiku-latest`
- `groq`: `llama-3.1-8b-instant`

### 4. Create/rename fixture files

All three OZ fixtures have LLM counterparts. Copy each (the originals are deleted in step 2):
```bash
cd code/backend/tests/fixtures
cp mock_oz_synthesis.json mock_llm_synthesis.json
cp mock_oz_suggestions.json mock_llm_suggestions.json
cp mock_oz_coplan.json mock_llm_coplan.json
```

Each `mock_llm_*.json` must have a `"result"` key wrapping a JSON string (the shape the services parse):
```json
{ "result": "{\"summary\":\"...\", ...}", "provider": "mock" }
```
Verify the existing `mock_oz_*.json` files already have this shape (they do post phase 4.2). If the `result` key is missing, add it as a wrapper.

### 5. Create `code/backend/scripts/setup_llm.py`

Interactive script that:
1. Prompts for `LLM_PROVIDER` (default: `anthropic`)
2. Prompts for `LLM_API_KEY` (masked input)
3. Prompts for `LLM_MODEL_ID` (optional override, shows per-provider default)
4. Appends/overwrites the three keys in `code/backend/.env`
5. Prints confirmation and example test command

### 6. Update `.env.prod.example`

Remove `OZ_API_KEY`, `OZ_MODEL_ID`, `OZ_ENVIRONMENT_ID`, `OZ_SKILL_SPEC`, `OZ_MAX_WAIT_SECONDS`, `OZ_MAX_SYNTHESIS_PER_WEEK`, `OZ_MAX_SUGGESTIONS_PER_DAY`, `OZ_MAX_COPLAN_PER_DAY`.

Add:
```
LLM_PROVIDER=anthropic
LLM_API_KEY=your-api-key-here
LLM_MODEL_ID=claude-3-5-haiku-latest
LLM_MAX_CONTEXT_CHARS=8000
LLM_MAX_SYNTHESIS_PER_WEEK=3
LLM_MAX_SUGGESTIONS_PER_DAY=5
LLM_MAX_COPLAN_PER_DAY=3
```

### 7. Write `code/backend/tests/test_llm_client.py`

Tests to cover:
- Mock mode (`_is_mock_mode()` returns `True` when `llm_api_key=""`)
- `run_prompt(title="Sunday Synthesis ...")` loads `mock_llm_synthesis.json`
- `run_prompt(title="Task Suggestions")` loads `mock_llm_suggestions.json`
- `run_prompt(title="Co-Planning Analysis")` loads `mock_llm_coplan.json`
- `run_prompt()` with mocked Anthropic SDK returns `{"result": "...", "provider": "anthropic"}`
- `run_prompt()` with mocked Groq SDK returns `{"result": "...", "provider": "groq"}`
- Circuit breaker opens after `_CB_THRESHOLD` consecutive failures
- Circuit breaker resets after `_CB_COOLDOWN` seconds
- Prompt guard truncates input exceeding `llm_max_context_chars`
- Unknown `LLM_PROVIDER` raises `ValueError` in config validation

---

## Integration & Edge Cases

- Services (`synthesis_service.py`, `ai_service.py`) still import `OZClient` at this step — that's fine; they are updated in step 2. No circular dependency risk.
- The mock fixture must remain JSON-parseable by `synthesis_service.py` (`json.loads(result["result"])`).
- **`_is_mock_mode()` is required on `LLMClient`** — both services call `self._oz_client._is_mock_mode()` to decide whether to record usage. If this method is absent, services will raise `AttributeError`. It should simply return `self._settings.llm_api_key == ""`.
- Anthropic SDK raises `anthropic.APIStatusError` on auth failure — must be caught and mapped to a consistent `LLMError` exception (same the circuit breaker increments on).
- If `LLM_MODEL_ID` is set in env, override the per-provider default.
- `LLMClient` must re-export `CircuitBreakerOpen` and `ServiceDisabledError` so `api/ai.py` can import them from one location in step 2 (or they stay in a shared exceptions module).

---

## Acceptance Criteria

1. `from app.services.llm_client import LLMClient` succeeds without errors.
2. `LLMClient(settings).run_prompt("test", title="Sunday Synthesis")` returns `{"result": ..., "provider": "mock"}` when `llm_api_key=""`.
3. Mock routing: `run_prompt(title="Task Suggestions")` returns the suggestions fixture; `run_prompt(title="Co-Planning Analysis")` returns the coplan fixture.
4. `pytest tests/test_llm_client.py -v` — all tests pass.
5. `config.py` contains no `oz_api_key`, `oz_model_id`, `oz_environment_id`, `oz_skill_spec`, `oz_max_wait_seconds`, `oz_max_synthesis_per_week`, `oz_max_suggestions_per_day`, or `oz_max_coplan_per_day` fields.
6. `ai_rate_limiter.py` references `llm_max_synthesis_per_week`, `llm_max_suggestions_per_day`, `llm_max_coplan_per_day` and uses `llm_run_id` in the function signature and log statements.
7. `python scripts/setup_llm.py` writes `LLM_PROVIDER` and `LLM_API_KEY` to `.env`.
8. `requirements.txt` includes `anthropic` and `groq` with pinned minimum versions.

---

## Testing / QA

**Automated:**
```bash
cd code/backend
pytest tests/test_llm_client.py -v
pytest tests/ -v --ignore=tests/test_oz_client.py  # Full suite minus old file still present
```

**Manual verification:**
1. Delete or empty `LLM_API_KEY` in `.env` → start server → `POST /ai/synthesis` → confirm mock response completes.
2. Set `LLM_PROVIDER=groq`, `LLM_API_KEY=<groq_free_key>` → `POST /ai/synthesis` → confirm real Groq response.
3. Set `LLM_PROVIDER=anthropic`, `LLM_API_KEY=<claude_key>` → `POST /ai/synthesis` → confirm real Claude response.

---

## Files touched

**Created:**
- `code/backend/app/services/llm_client.py`
- `code/backend/scripts/setup_llm.py`
- `code/backend/tests/test_llm_client.py`
- `code/backend/tests/fixtures/mock_llm_synthesis.json`
- `code/backend/tests/fixtures/mock_llm_suggestions.json`
- `code/backend/tests/fixtures/mock_llm_coplan.json`

**Modified:**
- `code/backend/app/core/config.py`
- `code/backend/app/services/ai_rate_limiter.py` (renamed config refs + `oz_run_id` param → `llm_run_id`)
- `code/backend/.env.prod.example`
- `code/backend/requirements.txt`

**Not yet touched (step 2):**
- `code/backend/app/services/oz_client.py` — still present, will be deleted in step 2
- `code/backend/app/services/synthesis_service.py`
- `code/backend/app/services/ai_service.py`
- `code/backend/tests/test_oz_client.py`
- `code/backend/tests/fixtures/mock_oz_*.json` (originals kept until step 2)

---

## Estimated effort

~2–3 hours (new client + tests + config migration)

---

## Concurrency & PR strategy

**Blocking steps:** None — this is the first step.  
**Merge Readiness:** false (pending implementation)  
**Branch:** `phase-4/step-1-llm-client`  
**Depends-On:** N/A

This PR must merge before step 2 begins.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Anthropic SDK breaking change | Pin `anthropic>=0.29.0,<1.0` until tested |
| Groq model name changes | Parameterize model via `LLM_MODEL_ID`; document known-good values |
| Tests import old `oz_client` | Step 2 handles; test runner skips `test_oz_client.py` until then |
| Fixture format mismatch | `mock_llm_synthesis.json` must have `"result"` key wrapping JSON string, matching existing synthesis service parsing |

---

## References

- [master.md](./master.md)
- [step-2-wire-and-cleanup.md](./step-2-wire-and-cleanup.md)
- [code/backend/app/services/oz_client.py](../../../../code/backend/app/services/oz_client.py) — source to adapt
- [code/backend/app/core/config.py](../../../../code/backend/app/core/config.py)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Groq Python SDK](https://github.com/groq/groq-python)

---

## Author Checklist

- [x] Purpose clearly stated
- [x] All deliverables listed
- [x] Primary files identified
- [x] Acceptance criteria are numbered and testable
- [x] Testing/QA includes automated + manual steps
- [x] Blocking steps and Merge Readiness declared
- [x] Risks documented
