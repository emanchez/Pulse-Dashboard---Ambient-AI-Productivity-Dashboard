# Phase 4 Step 1 — OZ Integration Layer Summary

## What was implemented

✅ **OZ integration (Warp agent platform)**
- Added `OZ_API_KEY` config + startup guard (`AI_ENABLED` must be false or key set in prod).
- Added `oz_model_id`, `oz_max_context_chars`, `oz_max_wait_seconds`, and hard caps (synthesis/week, suggest/day, coplan/day).

✅ **Mock mode (dev/tests)**
- `oz_api_key == ""` triggers mock mode.
- Mock mode uses a fixture `tests/fixtures/mock_oz_synthesis.json` and never makes real HTTP calls.
- Tests verify `httpx.AsyncClient` is never invoked in mock mode.

✅ **OZ client with cost protections**
- `app/services/oz_client.py` wraps OZ Agent API (submit/run/poll).
- Circuit breaker: 3 consecutive failures → 60s cooldown.
- Prompt length guard: enforces `oz_max_context_chars` and fails fast.

✅ **Rate limiting & usage logging**
- Added `AIUsageLog` model + `ai_usage_logs` table.
- Added `AIRateLimiter` service with per-user caps (synthesis/week, suggest/day, coplan/day).
- Added `GET /ai/usage` endpoint (JWT protected) returning `used/limit/resetsIn` for each endpoint.

✅ **Developer experience**
- Added `scripts/setup_oz.py` to prompt for API key and write `.env`.
- `.env` is already in `.gitignore`.

✅ **Tests**
- Added `tests/test_oz_client.py` with 32 tests covering all requirements.
- Ran full backend suite: **121 tests passing** (0 fail).

## Files Added / Updated

### New files
- `app/services/oz_client.py`
- `app/services/prompt_builder.py`
- `app/services/ai_rate_limiter.py`
- `app/models/ai_usage.py`
- `app/api/ai.py`
- `scripts/setup_oz.py`
- `tests/fixtures/mock_oz_synthesis.json`
- `tests/test_oz_client.py`

### Updated files
- `app/core/config.py`
- `app/main.py`
- `code/backend/requirements.txt`
- `tests/conftest.py`

---

## How to run

1. Run tests:
   ```bash
   cd code/backend
   python -m pytest tests/ -q
   ```
2. For real OZ usage, run:
   ```bash
   cd code/backend
   python scripts/setup_oz.py
   ```

---

## Notes

- No real OZ API calls are made unless `OZ_API_KEY` is set.
- Rate limiting is enforced at the service layer; endpoints return 429 with reset info when caps are exceeded.
