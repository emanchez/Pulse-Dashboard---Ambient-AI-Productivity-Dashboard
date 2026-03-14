# Step 1 — OZ Integration Layer

## Purpose

Establish the foundational OZ (Warp) cloud agent integration: SDK dependency, configuration, async client wrapper, and ADR documenting the Ollama → OZ architectural decision.

## Deliverables

- `scripts/setup_oz.py` — interactive setup script that prompts the dev for their API key and writes it to `.env` (never hardcoded or committed)
- `oz-sdk-python` added to `requirements.txt`
- `OZ_API_KEY`, `OZ_MODEL_ID`, and cost-protection settings added to `core/config.py` with startup guard
- `AI_ENABLED` feature flag in config (defaults to `true` in dev, required in prod)
- `services/oz_client.py` — async wrapper for OZ Agent API (submit prompt, poll status, retrieve result) with built-in usage throttling
- `services/prompt_builder.py` — utility to construct minimal prompts with strict token budgeting
- `services/ai_rate_limiter.py` — in-process per-user rate limiter for all AI endpoints (persisted in DB)
- `models/ai_usage.py` — `AIUsageLog` table for tracking spend and enforcing soft caps
- ADR-003 documented in this step's appendix
- Backend tests for OZ client (mocked API calls) and rate limiter

## Primary files to change (required)

- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [code/backend/app/services/oz_client.py](code/backend/app/services/oz_client.py) (new)
- [code/backend/app/services/prompt_builder.py](code/backend/app/services/prompt_builder.py) (new)
- [code/backend/app/services/ai_rate_limiter.py](code/backend/app/services/ai_rate_limiter.py) (new)
- [code/backend/app/models/ai_usage.py](code/backend/app/models/ai_usage.py) (new)
- [code/backend/app/db/base.py](code/backend/app/db/base.py) (import new model)
- [code/backend/scripts/setup_oz.py](code/backend/scripts/setup_oz.py) (new)
- [code/backend/tests/test_oz_client.py](code/backend/tests/test_oz_client.py) (new)

## Detailed implementation steps

### ⚠️ Cost Notice for Implementing Agent

OZ uses a **credit-based billing model** — every API call to `POST /api/v1/agent/run` consumes credits based on tokens processed, model used, and tool calls made. **There is no free unlimited tier.** The Free plan has a monthly credit cap; paid plans have overage billing. This feature is built for a personal project — all implementation choices must minimize credit consumption. Do not call the real OZ API during tests or development; use mock responses only. See the rate limiting and cost minimization sections below before writing any code.

1. **Create setup script `scripts/setup_oz.py`:**

   The coding agent must NOT hardcode or assume the API key. Instead, create an interactive setup script that the developer runs once:
   ```python
   #!/usr/bin/env python
   """One-time OZ API key setup. Run from code/backend/:
   python scripts/setup_oz.py
   """
   import os, pathlib, getpass
   
   def main():
       env_path = pathlib.Path(".env")
       print("\n=== OZ API Key Setup ===")
       print("Get your key at: https://app.warp.dev/settings (Personal API Keys)")
       print("IMPORTANT: This is credit-billed. Each synthesis run costs credits.")
       print("Recommended: use a lightweight model (see OZ_MODEL_ID below).\n")
       key = getpass.getpass("Paste your OZ API key (input is hidden): ").strip()
       if not key:
           print("No key entered. Aborted.")
           return
       # Read existing .env, update or append OZ_API_KEY
       lines = env_path.read_text().splitlines() if env_path.exists() else []
       lines = [l for l in lines if not l.startswith("OZ_API_KEY=")]
       lines.append(f"OZ_API_KEY={key}")
       env_path.write_text("\n".join(lines) + "\n")
       print(f"\n✓ OZ_API_KEY written to {env_path}")
       print("✓ .env is in .gitignore — key will NOT be committed.")
       print("\nCost tips:")
       print("  - Default model is claude-haiku-4 (cheapest capable model)")
       print("  - Rate limits: 3 synthesis/week, 5 suggestions/day, 3 co-plans/day")
       print("  - Set AI_ENABLED=false in .env to disable all AI endpoints\n")
   
   if __name__ == "__main__":
       main()
   ```
   Verify `.env` is in `.gitignore` before this step merges.

2. **Add SDK dependency:** Add `oz-sdk-python>=0.1.0` (or if the package is unavailable on PyPI, use `httpx>=0.27.0` for raw REST calls — the API is stable). Run `pip install -r requirements.txt`.

3. **Extend `Settings` in `core/config.py`:**
   - Add `oz_api_key: str = ""` — loaded from `.env`. Never provide a default value.
   - Add `oz_model_id: str = "anthropic/claude-haiku-4"` — **default is the lightest capable model** to minimize credit usage. Haiku is ~10× cheaper than Sonnet. Configurable via `OZ_MODEL_ID` in `.env`. Add a comment: `# Cost tip: claude-haiku-4 is cheapest; only upgrade model if output quality is insufficient`.
   - Add `ai_enabled: bool = True` — feature flag. When `False`, all `/ai/*` endpoints return 503.
   - Add `oz_max_wait_seconds: int = 90` — polling timeout. Lower than the original 120s to fail fast.
   - Add `oz_max_context_chars: int = 8000` — hard cap on prompt context characters (~2000 tokens). Keeps every run lean.
   - Add rate limit caps (soft caps enforced in `AIRateLimiter`):
     - `oz_max_synthesis_per_week: int = 3`
     - `oz_max_suggestions_per_day: int = 5`
     - `oz_max_coplan_per_day: int = 3`
   - Add startup guard: if `app_env != "dev"` and `oz_api_key == ""` and `ai_enabled`, raise `RuntimeError("OZ_API_KEY must be set when AI is enabled in non-dev mode")`.

4. **Create `services/oz_client.py`:**
   ```python
   class OZClient:
       """Async wrapper around OZ Agent API.
       
       COST WARNING: Every call to submit_run() consumes OZ credits.
       - Always use mock mode in tests (oz_api_key == "" in dev).
       - Default model is claude-haiku-4 (cheapest capable model).
       - Never call this in background tasks or scheduled jobs without explicit user action.
       """
       
       async def submit_run(self, prompt: str, title: str | None = None) -> str:
           """Submit a prompt to OZ. Returns run_id.
           Raises ServiceDisabledError if ai_enabled=False.
           Returns mock run_id if oz_api_key is empty (dev mode).
           """
           # POST https://app.warp.dev/api/v1/agent/run
           # Headers: Authorization: Bearer {oz_api_key}
           # Body: { "prompt": prompt, "config": { "model_id": oz_model_id }, "title": title }
           # IMPORTANT: prompt must be pre-truncated to oz_max_context_chars before this call
           
       async def get_run_status(self, run_id: str) -> dict:
           """Get current status. Uses GET, not a new agent run — does NOT consume run credits."""
           # GET https://app.warp.dev/api/v1/agent/runs/{run_id}
           
       async def wait_for_completion(self, run_id: str, timeout: int | None = None) -> dict:
           """Poll every 5s until SUCCEEDED/FAILED. Raises TimeoutError if exceeded.
           Polling GET calls are lightweight and do not consume run credits."""
           
       async def run_prompt(self, prompt: str, title: str | None = None) -> dict:
           """Submit and wait for completion. Convenience method.
           This is the ONLY method that triggers a billable OZ agent run.
           Callers MUST check ai_rate_limiter before calling this."""
   ```
   - Use `httpx.AsyncClient` for HTTP calls.
   - **Prompt length guard:** before submitting, assert `len(prompt) <= settings.oz_max_context_chars`. Raise `ValueError` and log a warning if exceeded — do not silently truncate at this layer (truncation is the PromptBuilder's responsibility).
   - Implement circuit breaker: after 3 consecutive failures, skip OZ calls for 60s.
   - All methods log at `DEBUG` level including prompt character count. Log at `INFO` on successful run completion with `run_id` and `oz_model_id`.
   - **Mock mode:** when `oz_api_key == ""` and `app_env == "dev"`, return a deterministic mock response (JSON fixture in `tests/fixtures/mock_oz_synthesis.json`). Log clearly: `"OZ mock mode active — no API call made, no credits consumed."`.

5. **Create `services/prompt_builder.py`:**
   ```python
   class PromptBuilder:
       """Constructs minimal prompts with strict token budgeting.
       
       Cost minimization strategy:
       - Hard cap: MAX_CONTEXT_CHARS = settings.oz_max_context_chars (default: 8000 chars ≈ 2000 tokens)
       - Include only essential fields — no raw log text, no full report bodies
       - Use compact JSON (no indentation, no null fields)
       - System prompt is short and instruction-focused; no lengthy preambles
       - Output format is tightly constrained (JSON-only response requested)
       """
       
       def build_synthesis_prompt(self, context: dict) -> str:
           """Build Prompt A (Sunday Synthesis). Target: <1500 chars system + <6500 chars context."""
           # Include: weekly_summary stats, top 5 open tasks (name + priority only), 
           # silence gaps (start, end, duration, explained), active system state, 
           # last 3 reports (title + word_count only, NO body)
           # Exclude: task notes, full report bodies, session logs
           
       def build_task_suggestion_prompt(self, context: dict) -> str:
           """Build Prompt B (Task Suggester). Target: <5000 chars total."""
           # Include: open tasks (name, priority, days_open), silence gaps summary, 
           # is_returning_from_leave flag
           # Exclude: action logs entirely, report contents
           
       def build_co_planning_prompt(self, report_body: str, tasks: list) -> str:
           """Build Prompt C (Co-Planning). Target: <4000 chars total.
           report_body is pre-truncated to 1000 chars max before passing here."""
           # Include: report body preview (max 1000 chars), open task names only (no details)
           
       def _build_compact_json(self, data: dict) -> str:
           """Serialize to compact JSON — no indentation, omit None values."""
           import json
           return json.dumps({k: v for k, v in data.items() if v is not None}, separators=(',', ':'))
           
       def _truncate_to_budget(self, prompt: str) -> str:
           """Hard-truncate to settings.oz_max_context_chars. Log a warning if triggered."""
   ```
   - Prompt templates sourced from `agents.md` Prompts A, B, C — but **stripped of examples and lengthy preambles**. The role definition and output format are the only non-data content.
   - All output format instructions must demand **JSON-only response** (no prose wrapping). This minimizes the response length the agent generates, reducing credits.
   - Example synthesis system prompt snippet: `"You are a productivity coach. Output ONLY valid JSON matching: {\"summary\": str, \"theme\": str, \"commitmentScore\": int(1-10)}. No other text."`

6. **Create `models/ai_usage.py`:**
   ```python
   class AIUsageLog(TimestampedBase):
       """Persists every AI API call for rate limiting and spend tracking."""
       __tablename__ = "ai_usage_logs"
       
       id: Mapped[int] = mapped_column(primary_key=True)
       user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
       endpoint: Mapped[str] = mapped_column(String(50), nullable=False)  # "synthesis" | "suggest" | "coplan"
       oz_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
       prompt_chars: Mapped[int] = mapped_column(Integer, nullable=False)  # chars sent (proxy for cost)
       was_mocked: Mapped[bool] = mapped_column(Boolean, default=False)  # True = no real API call made
       week_number: Mapped[str] = mapped_column(String(8), nullable=False)  # "2026-W11" for weekly bucketing
       # created_at from TimestampedBase
   ```

7. **Create `services/ai_rate_limiter.py`:**
   ```python
   class AIRateLimiter:
       """Enforces per-user rate limits on all AI endpoints to prevent runaway credit usage.
       
       Limits (configurable in Settings):
         - Synthesis: 3 per rolling 7-day window
         - Task suggestions: 5 per calendar day
         - Co-planning: 3 per calendar day
       
       These are soft caps — enforced in the service layer, NOT by SlowAPI.
       Mock-mode calls (no API key) are logged but NOT counted against the limit.
       """
       
       async def check_and_record(
           self, user_id: int, endpoint: str, db: AsyncSession
       ) -> None:
           """Check if the user is within limits. Raise HTTPException(429) with a clear message
           if exceeded. Record the usage AFTER a successful OZ call (not before, to avoid
           counting failed/mocked calls)."""
           # Query ai_usage_logs for the user + endpoint + time window
           # Raise 429 with: "Synthesis limit reached (3/week). Next reset: <date>."
       
       async def record_usage(
           self, user_id: int, endpoint: str, oz_run_id: str | None,
           prompt_chars: int, was_mocked: bool, db: AsyncSession
       ) -> None:
           """Persist a usage log entry after a real (non-mocked) OZ call succeeds."""
   ```
   Add `GET /ai/usage` endpoint (no auth bypass needed — just requires JWT) that returns the user's current usage against caps. This lets the frontend warn the user before they hit limits.

8. **Update `main.py` startup guard:**
   - Add the OZ API key validation alongside the existing JWT secret guard in the lifespan function.

## Cost Minimization Strategy (Required Reading)

OZ credits scale with tokens. Every implementation decision must account for cost:

| Strategy | Implementation | Saves |
|---|---|---|
| Lightweight default model | `claude-haiku-4` instead of Sonnet/Opus | ~10× cheaper per run |
| Compact JSON context | No indentation, omit null fields | 20–40% fewer input tokens |
| Short system prompts | Role + output format only, no examples | ~500 tokens per run |
| Strip report bodies from context | Only title + word count in synthesis | ~1000 tokens per run |
| JSON-only output instruction | Prevents the agent adding prose wrappers | Reduces output tokens |
| Hard context cap | `oz_max_context_chars = 8000` enforced in PromptBuilder | Prevents runaway prompts |
| Rate limit caps | 3 synthesis/week, 5 suggest/day, 3 coplan/day | Prevents accidental loops |
| On-demand only | No scheduled or auto-triggered runs in Phase 4 | Most important — zero background cost |
| Mock mode in dev/tests | No real API calls unless key is explicitly set | Zero cost during development |

## Integration & Edge Cases

- **No OZ key in dev / tests:** When `oz_api_key == ""`, `OZClient` returns mock responses from a JSON fixture. Log clearly: `"OZ mock mode — no real API call, no credits consumed."` Tests MUST always run in mock mode — never call the real API in `pytest`.
- **Httpx dependency:** Verify `httpx` is already in the dependency tree (FastAPI uses it via `TestClient`). If not, add `httpx>=0.27.0` to `requirements.txt`.
- **OZ's own rate limits:** The credit system is Warp's safety net, not ours. Our `AIRateLimiter` provides a tighter personal cap so mistakes don't drain credits before Warp's limit kicks in.
- **`ai_usage_logs` is a new table:** Handled by `create_all` (brand new table). Pre-merge: `cp data/dev.db data/dev.db.pre-phase4.bak`.
- **`GET /ai/usage` returns real-time cap status:** e.g., `{ "synthesis": { "used": 1, "limit": 3, "resetsIn": "5 days" } }`. Frontend can surface this to prevent user surprise.

## Acceptance Criteria (required)

1. `pip install -r code/backend/requirements.txt` succeeds with `oz-sdk-python` (or `httpx`) installed.
2. `from app.services.oz_client import OZClient` imports without error.
3. `from app.services.prompt_builder import PromptBuilder` imports without error.
4. `from app.services.ai_rate_limiter import AIRateLimiter` imports without error.
5. `settings.oz_api_key` defaults to `""`.
6. `settings.oz_model_id` defaults to `"anthropic/claude-haiku-4"`.
7. `settings.oz_max_context_chars` defaults to `8000`.
8. `settings.oz_max_synthesis_per_week` defaults to `3`.
9. Startup with `APP_ENV=prod`, `AI_ENABLED=true`, and empty `OZ_API_KEY` raises `RuntimeError`.
10. Startup with `APP_ENV=dev` and empty `OZ_API_KEY` succeeds with mock mode active.
11. `OZClient.run_prompt()` with empty `oz_api_key` in dev returns a mock response without making any HTTP call.
12. `OZClient.run_prompt()` with `ai_enabled=False` raises `ServiceDisabledError`.
13. `PromptBuilder.build_synthesis_prompt()` output is ≤ `settings.oz_max_context_chars` characters.
14. `PromptBuilder.build_synthesis_prompt()` uses compact JSON (no indentation) in the context section.
15. `AIRateLimiter.check_and_record()` raises HTTP 429 when the synthesis weekly limit is exceeded.
16. `GET /ai/usage` returns current usage counts vs. caps for all three endpoint types.
17. `scripts/setup_oz.py` prompts for the API key interactively and writes it to `.env`.
18. `.env` is present in `.gitignore` (verify before merge).
19. All existing 89 tests pass with zero regressions.
20. `test_oz_client.py` adds ≥10 new tests (submit, poll, timeout, circuit breaker, disabled, mock mode, rate limit check, rate limit enforcement, usage endpoint, prompt length).

## Testing / QA (required)

> **Critical:** All tests in this file MUST run in mock mode. Do NOT call the real OZ API. Do NOT require `OZ_API_KEY` to be set in CI or test environments. Tests that accidentally hit the real API incur credit charges.

**New test file:** `code/backend/tests/test_oz_client.py`

Tests to add:
- `test_oz_client_mock_mode_no_http_call` — `oz_api_key=""`, `app_env="dev"` → assert `run_prompt` returns mock result **and** no HTTP call was made (patch `httpx.AsyncClient` and assert `post` was never called).
- `test_oz_client_submit_run_success` — mock HTTP 200 with `run_id` → assert returns run_id string.
- `test_oz_client_wait_for_completion_success` — mock polling sequence (QUEUED → INPROGRESS → SUCCEEDED) → assert returns final result.
- `test_oz_client_wait_for_completion_timeout` — mock perpetual INPROGRESS → assert raises `TimeoutError`.
- `test_oz_client_circuit_breaker` — mock 3 consecutive HTTP 500s → assert 4th call raises `CircuitBreakerOpen` without HTTP call.
- `test_oz_client_disabled` — `ai_enabled=False` → assert `run_prompt` raises `ServiceDisabledError`.
- `test_oz_client_prompt_length_guard` — prompt exceeding `oz_max_context_chars` → assert `ValueError` raised before any HTTP call.
- `test_prompt_builder_synthesis_compact_json` — assert output uses compact JSON (no whitespace around `:` or `,`).
- `test_prompt_builder_under_limit` — synthesize a large context → assert output length ≤ `oz_max_context_chars`.
- `test_rate_limiter_allows_under_limit` — 2 synthesis logs this week → `check_and_record` passes.
- `test_rate_limiter_blocks_at_limit` — 3 synthesis logs this week → `check_and_record` raises HTTP 429 with reset date in message.
- `test_usage_endpoint` — create 2 usage log entries → `GET /ai/usage` → assert correct counts and `resetsIn` field.

```bash
cd code/backend && python -m pytest tests/test_oz_client.py -v
```

**Manual QA checklist:**
1. Run `python scripts/setup_oz.py` (without an API key) → confirm it accepts input (paste a fake key) → confirm `.env` is updated.
2. Inspect `.env` → verify key is written, not logged to stdout.
3. Start backend with `OZ_API_KEY` unset → confirm startup succeeds in dev mode with `"OZ mock mode"` in logs.
4. Start backend with `APP_ENV=prod`, `AI_ENABLED=true`, `OZ_API_KEY=""` → confirm `RuntimeError` at startup.
5. Start backend with `AI_ENABLED=false` → confirm `/health` returns 200 and `/ai/synthesis` returns 503.
6. `GET /ai/usage` → confirm response shape with `used`, `limit`, `resetsIn` fields.

## Files touched (repeat for reviewers)

- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [code/backend/app/services/oz_client.py](code/backend/app/services/oz_client.py) (new)
- [code/backend/app/services/prompt_builder.py](code/backend/app/services/prompt_builder.py) (new)
- [code/backend/app/services/ai_rate_limiter.py](code/backend/app/services/ai_rate_limiter.py) (new)
- [code/backend/app/models/ai_usage.py](code/backend/app/models/ai_usage.py) (new)
- [code/backend/app/db/base.py](code/backend/app/db/base.py) (model import)
- [code/backend/app/main.py](code/backend/app/main.py) (startup guard addition)
- [code/backend/scripts/setup_oz.py](code/backend/scripts/setup_oz.py) (new)
- [code/backend/tests/test_oz_client.py](code/backend/tests/test_oz_client.py) (new)
- [code/backend/tests/fixtures/mock_oz_synthesis.json](code/backend/tests/fixtures/mock_oz_synthesis.json) (new — mock OZ response fixture)

## Estimated effort

1–2 dev days

## Concurrency & PR strategy

- **Blocking steps:** None — this is the first step in the chain.
- **Merge Readiness:** false (draft)
- **Branch:** `phase-4/step-1-oz-integration-layer`
- Steps 2–7 all depend on this step. Must merge first.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `oz-sdk-python` is new/unstable | Fall back to raw `httpx` calls against the REST API. The SDK is a convenience wrapper; the API is stable. |
| OZ API key exposure in logs | Never log the API key. Use `repr(key[:4] + "***")` pattern for debug output. Never pass the raw key to sub-processes. |
| Circuit breaker state persists incorrectly | In-memory counter with timestamp reset. Single-user app makes this trivial. |
| Developer accidentally hits real OZ API during testing | Mock mode is the default when `oz_api_key` is empty. Tests always run with empty key. Add a CI check: `assert settings.oz_api_key == ""` in test conftest when `APP_ENV=test`. |
| Credits exhausted mid-week | `AIRateLimiter` caps usage well below free plan limits. `GET /ai/usage` endpoint lets the developer monitor consumption. If credits are exhausted, all AI endpoints return 503 (circuit breaker from OZ 402 response). |
| `.env` accidentally committed with real API key | Verify `.gitignore` includes `.env` before merge. Add a pre-commit check in `Makefile` if not already present. |

## References

- [agents.md](../../agents.md) — Prompt A, B, C templates
- [OZ Agent API](https://docs.warp.dev/reference/api-and-sdk/agent) — REST endpoints
- [OZ Python SDK](https://github.com/warpdotdev/oz-sdk-python) — Client library
- [master.md](./master.md) — Phase 4 master plan

## Appendix — ADR-003: Ollama → OZ Migration

**Status:** Accepted  
**Date:** 2026-03-14  
**Context:** ADR-001 specified Ollama for local-first AI inference. Phase 4 requires reliable, multi-model LLM orchestration for weekly synthesis, task suggestion, and co-planning. Local Ollama carries operational burden (model management, GPU requirements, inconsistent performance across hardware).

**Decision:** Replace Ollama with OZ (Warp's cloud agent platform) for all LLM inference in Phase 4.

**Consequences:**
- (+) Multi-model support — choose the best model per task (e.g., Claude for narrative, GPT for structured output).
- (+) No local GPU/model management overhead.
- (+) Built-in observability, session tracking, and audit trail via OZ platform.
- (+) Scheduled agents for future automated Sunday Synthesis (cron trigger).
- (+) MCP server support for future autonomous data access.
- (-) Introduces cloud dependency for AI features. Mitigated by `AI_ENABLED` feature flag — dashboard remains fully functional without AI.
- (-) Credit-based cost. Mitigated by on-demand (not continuous) inference pattern. Weekly synthesis + occasional suggestions ≈ minimal credit usage.
- (-) Data leaves the local machine. Mitigated by Warp's SOC 2 compliance and zero-data-retention LLM policies. Context is limited to task names, timestamps, and user-written report text.

**Supersedes:** ADR-001 (Local-First AI / Ollama) — for inference only. The rest of the stack remains local-first (SQLite, local backend, local frontend).

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
