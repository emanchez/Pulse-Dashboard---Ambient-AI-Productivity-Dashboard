# Phase 3.2 — Project Status & Code Audit Report

**Date:** 2026-03-11
**Scope:** Full project status assessment against PDD roadmap, comprehensive bug/issue inventory, security audit, and pre-Phase-4 readiness evaluation.

---

## Executive Summary

The Ambient AI Productivity Dashboard has completed Phases 1–3 of its PDD roadmap. The backend delivers a complete REST API covering Authentication, Tasks CRUD, Session Management, Flow State analytics, Manual Reports with pagination, and System State (Vacation/Leave) orchestration — all JWT-guarded and user-scoped. The frontend implements a dark Bento Grid dashboard with silence-aware navbar, productivity pulse visualization, session management, task CRUD with inline editing, a full reports page with create/edit/archive/delete, and a system state manager with overlap validation.

The codebase is well-structured with consistent patterns (CamelModel aliasing, TimestampedBase, event sourcing via ActionLog middleware). Backend test coverage is solid across all resource endpoints, including happy-path, validation, authorization, and user-scoping tests. Frontend has zero automated test coverage.

**Phase 4 (Sunday Synthesis, Co-Planning, Ollama/OZ integration)** is the remaining major milestone. This report catalogs every known issue, latent bug risk, and security concern to address before proceeding.

**Key decision pending:** The LLM inference layer — currently designed around local Ollama — may be outsourced to OZ (Warp's cloud agent platform). This has significant architectural implications documented in §7.

---

## 1. PDD Roadmap Progress

### Phase 1: Skeleton & Agentic Prototyping — COMPLETE

| Deliverable | Status | Notes |
|---|---|---|
| FastAPI + JWT authentication | **Done** | `/login`, `/me`, `get_current_user` dependency |
| SQLAlchemy async models | **Done** | `User`, `Task`, `ActionLog`, `SessionLog`, `ManualReport`, `SystemState` |
| Pydantic v2 schemas with camelCase aliasing | **Done** | `CamelModel` base with `alias_generator` + `populate_by_name` |
| Type Sync tooling (`@hey-api/openapi-ts`) | **Done** | `generate-client.sh`, committed `types.gen.ts` |
| Basic Bento shell + Next.js scaffold | **Done** | App Router, Tailwind, Lucide, dark theme |
| Dev user creation script | **Done** | `scripts/create_dev_user.py` |

### Phase 2: Ambient Sensing & Tactical CRUD — COMPLETE

| Deliverable | Status | Notes |
|---|---|---|
| ActionLog middleware (event sourcing) | **Done** | Logs POST/PUT/DELETE/PATCH on `/tasks`, `/reports`, `/system-states` |
| Task CRUD with user scoping | **Done** | Create, update, delete + 403 on cross-user access |
| `GET /stats/pulse` (silence indicator) | **Done** | `silenceState`, `gapMinutes`, `lastActionAt`, `pausedUntil` |
| `GET /stats/flow-state` (6h rolling window) | **Done** | 30-min bucket aggregation with percent/change metrics |
| Session management (`start`/`stop`/`active`) | **Done** | Idempotent start, elapsed minutes computed property |
| Silence-aware navbar badges | **Done** | Engaged/Stagnant/Paused with color-coded indicators |
| Bento Grid tasks dashboard | **Done** | FocusHeader, ProductivityPulseCard, CurrentSessionCard, DailyGoalsCard, TaskQueueTable |
| Regenerated TypeScript client | **Done** | `types.gen.ts` includes all schemas |
| `SilenceStateProvider` context | **Done** | 30s polling, `data-state` attribute on `<html>` |

### Phase 3: Qualitative Inputs & System Pauses — COMPLETE

| Deliverable | Status | Notes |
|---|---|---|
| Manual Report CRUD (`/reports`) | **Done** | Create, list (paginated), get, update, archive, delete |
| Report validation (title, body, status, tags) | **Done** | Field validators for empty/length/allowed values |
| Task linking (`associatedTaskIds`) | **Done** | Validated against existing tasks on create |
| Report status filter (`?status=`) | **Done** | Query param filtering on list endpoint |
| SystemState CRUD (`/system-states`) | **Done** | Create, list, get active, update, delete |
| Overlap detection for SystemState | **Done** | 409 Conflict on overlapping date ranges |
| Mode type validation (`vacation`/`leave`) | **Done** | Case-insensitive normalization |
| `end_date > start_date` validation | **Done** | Model validator on create and update |
| Pulse integrates SystemState (paused state) | **Done** | Active vacation/leave overrides stagnant |
| Reports page UI | **Done** | ReportList, ReportForm, ReportCard components |
| SystemStateManager UI | **Done** | Create/list/delete system states from reports page |
| Frontend API wrappers for all new endpoints | **Done** | `lib/api.ts` covers reports + system states |
| DB migration via `create_all` | **Partial** | Works for dev (creates new tables), not for column additions |

### Phase 4: Sunday Synthesis & Co-Planning — NOT STARTED

| Deliverable | Status | Notes |
|---|---|---|
| Ollama/OZ orchestration for Sunday Synthesis | **Not started** | Prompt A defined in `agents.md`; no backend service |
| Task Suggester agent | **Not started** | Prompt B defined; no implementation |
| Co-Planning / Ambiguity Guard | **Not started** | Prompt C defined; no implementation |
| Sunday Modal UI | **Not started** | No frontend component |
| Reasoning Sidebar / Inference Cards | **Not started** | No frontend component |
| Ghost List (wheel-spinning visualization) | **Not started** | No backend query or frontend component |
| Re-entry Mode (post-vacation low-friction) | **Not started** | Concept defined in PDD |

---

## 2. Current Architecture Inventory

### Backend Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | Health check |
| POST | `/login` | No | JWT token issuance |
| GET | `/me` | Yes | Current user profile |
| GET | `/tasks/` | Yes | List tasks (user-scoped) |
| POST | `/tasks/` | Yes | Create task |
| PUT | `/tasks/{id}` | Yes | Update task |
| DELETE | `/tasks/{id}` | Yes | Delete task |
| GET | `/stats/pulse` | Yes | Silence state telemetry |
| GET | `/stats/flow-state` | Yes | 6h rolling flow state |
| POST | `/sessions/start` | Yes | Start focus session |
| POST | `/sessions/stop` | Yes | Stop active session |
| GET | `/sessions/active` | Yes | Get active session |
| POST | `/reports` | Yes | Create report |
| GET | `/reports` | Yes | List reports (paginated) |
| GET | `/reports/{id}` | Yes | Get single report |
| PUT | `/reports/{id}` | Yes | Update report |
| PATCH | `/reports/{id}/archive` | Yes | Archive report |
| DELETE | `/reports/{id}` | Yes | Delete report |
| POST | `/system-states` | Yes | Create system state |
| GET | `/system-states` | Yes | List system states |
| GET | `/system-states/active` | Yes | Get active system state |
| PUT | `/system-states/{id}` | Yes | Update system state |
| DELETE | `/system-states/{id}` | Yes | Delete system state |

**Total: 22 endpoints (20 JWT-guarded, 2 public)**

### SQLAlchemy Models

| Model | Table | `user_id` | Indexes |
|---|---|---|---|
| `User` | `users` | N/A (is the user) | `username` UNIQUE |
| `Task` | `tasks` | Yes (NOT NULL) | `user_id` |
| `ActionLog` | `action_logs` | Yes (nullable) | `user_id` |
| `SessionLog` | `session_logs` | Yes (NOT NULL) | `user_id` |
| `ManualReport` | `manual_reports` | Yes (NOT NULL) | `user_id` |
| `SystemState` | `system_states` | Yes (nullable) | `user_id` |

### Frontend Pages

| Route | Component | Status |
|---|---|---|
| `/` | Redirect to `/tasks` | Done |
| `/login` | Login form | Done |
| `/tasks` | Full Bento Grid dashboard | Done |
| `/reports` | Reports + System State management | Done |

### Test Coverage Summary

| Test File | Test Count | Coverage Area |
|---|---|---|
| `test_api.py` | ~12 | Auth, Tasks CRUD, validation, user scoping |
| `test_sessions.py` | ~10 | Session start/stop/active, idempotency, auth |
| `test_reports.py` | ~20+ | Report CRUD, validation, pagination, archive, action log |
| `test_system_states.py` | ~20+ | SystemState CRUD, overlap, active, user scoping, pulse |
| `test_stats.py` | ~8 | Pulse engaged/stagnant/paused, gap calc |
| `test_models.py` | 1 | CamelCase schema serialization |
| `e2e/test_smoke.py` | 1 | Full login → task create → ActionLog flow |
| **Frontend** | **0** | **No automated tests** |

---

## 3. Bugs & Correctness Issues

### 3.1 — CRITICAL

| # | Issue | Location | Impact | Fix |
|---|---|---|---|---|
| C-1 | **Race condition on concurrent session starts** | `session_service.py:start_session` | SELECT then INSERT with no DB-level constraint. Two concurrent requests can both pass `get_active_session` and create duplicate active sessions. | Add partial unique index `ON session_logs(user_id) WHERE ended_at IS NULL` or use `SELECT ... FOR UPDATE`. |
| C-2 | **`SystemState.user_id` is nullable** | `system_state.py` model | A system state created without a `user_id` would be invisible to all user-scoped queries but pollute the DB. The endpoint always sets it, but no DB constraint prevents `NULL`. | Change to `nullable=False`. |
| C-3 | **`ActionLog.user_id` is nullable** | `action_log.py` model | Action logs without a `user_id` are orphaned — they don't appear in any user-scoped pulse/flow queries but still occupy storage. The middleware may fail to extract the JWT in edge cases. | Add fallback handling; consider `nullable=False` with a `"system"` sentinel for unauthenticated writes. |

### 3.2 — HIGH

| # | Issue | Location | Impact | Fix |
|---|---|---|---|---|
| H-1 | **`sessions/start` returns 201 for existing sessions** | `sessions.py:sessions_start` | When the idempotent path returns an already-active session, HTTP 201 CREATED is semantically incorrect. Should return 200 OK. | Return `200` when `existing is not None` in `start_session`, or split the return code in the route handler. |
| H-2 | **No `from_attributes=True` on `TaskSchema`** | `task.py:TaskSchema` | Currently uses `task.__dict__` for `model_validate`, which works but bypasses Pydantic's `from_attributes` path. If ORM model attributes diverge from `__dict__` keys (e.g., hybrid properties), this will break silently. | Add `model_config = ConfigDict(from_attributes=True)`. |
| H-3 | **Update task silently ignores `None` fields** | `tasks.py:update_task` | The `if v is None: continue` logic means a client cannot explicitly set a nullable field (e.g., `deadline`, `notes`) back to `None`. | Differentiate between "field not sent" and "field sent as null". Use `model_dump(exclude_unset=True)` instead. |
| H-4 | **`ManualReportSchema` / `SystemStateSchema` redundant alias config** | Both schemas | They inherit `CamelModel` (which sets `alias_generator`) but also re-declare `alias_generator=_to_camel` in their own `model_config`. Functionally equivalent now but creates maintenance risk — a change to `CamelModel` won't propagate. | Remove the redundant `alias_generator` from child schemas. |
| H-5 | **`PulseStatsSchema` mixes explicit `Field(alias=...)` with inherited `alias_generator`** | `schemas/stats.py` | `PulseStatsSchema` extends `CamelModel` (which has `alias_generator`) but also declares explicit `Field(alias="silenceState")`. This double-aliasing works by coincidence because the generated alias and explicit alias match. Any rename of the Python field will cause a silent conflict. | Remove explicit `alias` from `Field()` and rely solely on the `alias_generator`. |
| H-6 | **`elapsed_minutes` uses `datetime.now(timezone.utc)` at read time** | `session_log.py:SessionLog.elapsed_minutes` | This computed property calculates elapsed time on every access. If `started_at` is stored without timezone info (naive UTC) but a consumer somehow injects a tz-aware datetime, subtraction will raise `TypeError`. | Ensure strict consistency: always compare naive-to-naive. Add a guard. |
| H-7 | **`create_all` does not migrate existing tables** | `main.py:lifespan` | Adding new columns to a model won't alter existing tables. Known issue from Phase 2.2, still not addressed. Will cause `OperationalError: no such column` on live databases. | Introduce Alembic for schema migrations before deployment. |

### 3.3 — MEDIUM

| # | Issue | Location | Impact | Fix |
|---|---|---|---|---|
| M-1 | **No composite index on `action_logs(user_id, timestamp)`** | `action_log.py` | The flow-state query and pulse query both filter by `user_id` and sort/filter by `timestamp`. Without a composite index, these degrade as the table grows. | Add `Index('ix_action_logs_user_ts', 'user_id', 'timestamp')`. |
| M-2 | **No composite index on `session_logs(user_id, ended_at)`** | `session_log.py` | `get_active_session` filters by `user_id` and `ended_at IS NULL`. | Add `Index('ix_session_logs_user_ended', 'user_id', 'ended_at')`. |
| M-3 | **Flow calculation materializes all timestamps in Python** | `flow_state.py:calculate_flow_state` | Fetches all `ActionLog.timestamp` values into memory, then buckets in a Python loop. With high activity this becomes slow and memory-intensive. | Use SQL `GROUP BY` with `date_trunc` or equivalent to aggregate at the DB level. |
| M-4 | **`test_stats.py` uses deprecated `datetime.utcnow()`** | `tests/test_stats.py` | `datetime.utcnow()` is deprecated in Python 3.12+. Tests will emit deprecation warnings and may behave incorrectly in tz-aware environments. | Migrate to `datetime.now(timezone.utc).replace(tzinfo=None)` to match production code pattern. |
| M-5 | **ActionLog middleware reads response body for POST entity ID** | `action_log.py:ActionLogMiddleware` | Accessing `response.body` on a `StreamingResponse` will fail silently (caught by broad `except`). The `task_id` field in ActionLog conflates task IDs with generic entity IDs (e.g., report IDs) — semantically misleading for non-task resources. | Rename column to `entity_id` or add a `resource_type` column. Handle streaming responses. |
| M-6 | **`conftest.py` uses deprecated `asyncio.get_event_loop()`** | `tests/conftest.py`, `test_stats.py` | Deprecated since Python 3.10. Will raise `DeprecationWarning` and eventually break. | Use `asyncio.run()` or `pytest-asyncio` fixtures. |
| M-7 | **Word count is naive `split()` count** | `report_service.py:create_report` | `len(data.body.split())` doesn't handle edge cases (multiple spaces, newlines, markdown). Minor inaccuracy. | Acceptable for MVP; consider a more robust tokenizer post-MVP. |
| M-8 | **Frontend polling creates N+1 interval problem** | `tasks/page.tsx`, `SilenceStateProvider` | Tasks page polls sessions (30s), flow (60s), tasks (60s), and `SilenceStateProvider` polls pulse (30s). That's 4 independent intervals. On the reports page, there's a separate pulse poll. These stack and can cause unnecessary re-renders. | Consolidate into a single polling manager or use WebSockets. |

### 3.4 — LOW

| # | Issue | Location | Impact | Fix |
|---|---|---|---|---|
| L-1 | **No frontend error boundary** | All pages | An unhandled JS error crashes the entire React tree with a white screen. | Add a root `ErrorBoundary` component. |
| L-2 | **Token stored in `localStorage` (XSS risk)** | `useAuth.ts` | A successful XSS attack can steal the JWT. | Migrate to `httpOnly` cookies in production. See §5. |
| L-3 | **No loading states on individual API calls** | Various frontend | Deleting/archiving a report has no loading indicator; user might double-click. | Add per-action loading states and optimistic UI. |
| L-4 | **`generated/types.gen.ts` hardcodes `baseUrl: 'http://127.0.0.1:8001'`** | `types.gen.ts` | The generated client has a hardcoded dev URL. This is overridden by `lib/api.ts` which uses `NEXT_PUBLIC_API_BASE`, but it's confusing. | Regenerate with correct base URL or remove the default. |
| L-5 | **Service worker unregistration script in layout** | `layout.tsx` | Inline `<script>` runs on every page load to clean up stale service workers from "earlier next-pwa experiments." This is tech debt. | Remove once confirmed no SWs exist in user browsers. |

---

## 4. Artifacts & Patterns That Could Lead to Future Bugs

| # | Pattern | Risk | Location |
|---|---|---|---|
| F-1 | **Naive UTC everywhere** — All datetimes stored as timezone-unaware UTC via `.replace(tzinfo=None)`. | If any code path introduces tz-aware datetimes (e.g., a new dependency, OZ API responses), subtraction/comparison will raise `TypeError` with no graceful fallback. | All models, services |
| F-2 | **UUID as string(36)** — Primary keys are `String(36)` UUIDs generated by `uuid4()`. | No DB-level UUID type constraint. Any 36-char string is accepted. Postgres migration should use native `UUID` type. | `db/base.py` |
| F-3 | **No DB-level foreign key constraints** — `task_id` in `ActionLog`/`SessionLog` is a plain `String(36)` with no FK relation. `associated_task_ids` in `ManualReport` is stored as JSON with no referential integrity. | Orphaned references after task deletion. | All models |
| F-4 | **Broad `except Exception` in middleware** — ActionLog middleware catches and suppresses all exceptions. | Masks bugs in the logging pipeline. A corrupt JWT, malformed response, or DB connection failure in the middleware is invisible unless you check logs. | `middlewares/action_log.py` |
| F-5 | **CamelModel inheritance inconsistency** — Some schemas inherit `CamelModel` cleanly, others redeclare `alias_generator` and `model_config`. | Divergent behavior when `CamelModel` is modified. | `ManualReportSchema`, `SystemStateSchema`, `PulseStatsSchema` |
| F-6 | **No database migration tool** — Schema changes require manual `ALTER TABLE` or DB wipe. | Any column addition/rename in production will cause `OperationalError`. | Project-wide |
| F-7 | **Hand-written `pulseClient.ts` alongside generated types** — The pulse client is manually maintained because the TS generator doesn't emit service functions. | Type drift if `PulseStatsSchema` changes on the backend but `pulseClient.ts` isn't updated. | `lib/generated/pulseClient.ts` |
| F-8 | **No request timeout on frontend fetches** — `lib/api.ts` uses raw `fetch()` with no `AbortController` or timeout. | A hung backend causes the UI to wait indefinitely (indefinite loading spinner). | `lib/api.ts` |
| F-9 | **Stale closure risk in polling callbacks** — `tokenRef` pattern mitigates this, but `logout` callback is captured at mount time in some effects. | Edge case: if `logout` identity changes (React re-render), the interval callback references the stale closure. | `tasks/page.tsx`, `reports/page.tsx` |

---

## 5. Security Audit (Pre-Deployment)

### 5.1 — CRITICAL (Must-Fix Before Deployment)

| # | Issue | Severity | Detail |
|---|---|---|---|
| S-1 | **Default JWT secret is insecure** | CRITICAL | `config.py` defaults to `"dev-secret-change-me"`. There is no startup check that rejects this value in non-dev environments. A production deployment with the default secret allows anyone to forge tokens. **Fix:** Add a startup assertion that fails if `JWT_SECRET` equals the default and `ENV` != `"dev"`. |
| S-2 | **JWT token in `localStorage`** | HIGH | Tokens stored in `localStorage` are accessible to any JavaScript running on the page. An XSS vulnerability (even from a third-party script or browser extension) can exfiltrate the token. **Fix:** Migrate to `httpOnly` + `Secure` + `SameSite=Strict` cookies for production. Keep localStorage for dev convenience if needed. |
| S-3 | **No HTTPS enforcement** | HIGH | The application has no mechanism to enforce HTTPS. In production, all traffic (including JWT tokens) would traverse the network in plaintext. **Fix:** Deploy behind a reverse proxy (nginx/Caddy) with TLS termination. Set `Secure` flag on cookies. |
| S-4 | **`python-jose` is unmaintained** | HIGH | `python-jose[cryptography]==3.3.0` has no releases since 2022 and has known CVEs. The `cryptography` backend pins may also lag. **Fix:** Migrate to `PyJWT` (actively maintained) or `joserfc`. |
| S-5 | **No CORS origin restriction for production** | HIGH | `get_cors_origins()` defaults to `localhost:3000,3001`. Production CORS must be set to the actual deployment domain. A misconfigured `FRONTEND_CORS_ORIGINS` env var in production could allow credential-bearing requests from any origin. **Fix:** Require explicit CORS origins in production config, fail-closed. |

### 5.2 — HIGH

| # | Issue | Detail |
|---|---|---|
| S-6 | **No rate limiting on `/login`** | The login endpoint has no throttling. An attacker can brute-force credentials at network speed. **Fix:** Add `slowapi` or similar rate-limiter (e.g., 5 attempts per minute per IP). |
| S-7 | **No rate limiting on any endpoint** | Authenticated endpoints are also unthrottled. A compromised token can flood the API. **Fix:** Add global rate limiting middleware. |
| S-8 | **No CSRF protection** | The frontend uses `credentials: "omit"` which mitigates cookie-based CSRF, but if migrated to `httpOnly` cookies (per S-2), CSRF tokens will be needed. **Fix:** Plan CSRF token implementation alongside cookie-based auth migration. |
| S-9 | **JWT has no audience/issuer claims** | Tokens lack `aud` and `iss` claims. If this JWT secret is accidentally shared with another service, tokens are interchangeable. **Fix:** Add `iss` and `aud` claims and validate them on decode. |
| S-10 | **No token revocation mechanism** | There is no logout on the server side — the client simply deletes the token. A stolen token remains valid until expiry (7 days). **Fix:** Implement a token denylist (Redis/DB) or reduce token TTL + add refresh tokens. |
| S-11 | **Password hashing uses `pbkdf2_sha256`** | While secure, `pbkdf2_sha256` is weaker against GPU cracking than `bcrypt` or `argon2`. The `passlib[bcrypt]` dependency is already installed but not used. **Fix:** Switch to `bcrypt` or `argon2` in `CryptContext`. |

### 5.3 — MEDIUM

| # | Issue | Detail |
|---|---|---|
| S-12 | **No input sanitization for XSS** | Report `body` and `title` fields accept arbitrary HTML/JS content. While they're rendered via React (which escapes by default), any future raw HTML rendering (e.g., markdown-to-HTML) would be vulnerable. **Fix:** Sanitize on input or use a safe markdown renderer with allowlisting. |
| S-13 | **No request body size limits** | Report body allows up to 50,000 characters, but there's no global request body size limit. An attacker could send large payloads to consume memory. **Fix:** Configure `uvicorn` or a reverse proxy to limit max request body size. |
| S-14 | **Verbose error messages in production** | FastAPI returns detailed validation errors (422 responses) that include field names and internal schema structure. **Fix:** Add exception handlers that sanitize error details in production. |
| S-15 | **No audit log for auth events** | Login attempts (successful and failed) are not logged in `ActionLog` or any audit trail. **Fix:** Log auth events for security monitoring. |

---

## 6. Test Gaps & Quality Concerns

| # | Gap | Priority |
|---|---|---|
| T-1 | **Zero frontend automated tests** | HIGH — No component tests, integration tests, or E2E tests for the React layer. |
| T-2 | **No test for concurrent session creation** (race condition C-1) | HIGH |
| T-3 | **No test for flow-state with real ActionLog data** | MEDIUM — Current stats tests cover pulse but not flow-state bucket aggregation. |
| T-4 | **No test for report `update_report` service error paths** | MEDIUM — The `try/except SQLAlchemyError` in `update_report` is untested. |
| T-5 | **No cross-user isolation test for reports** | MEDIUM — Tasks have user-scoping tests; reports and system states do not. |
| T-6 | **No test for `ManualReport` with valid `associatedTaskIds`** | MEDIUM — Only the invalid case is tested. |
| T-7 | **No test for `SystemState` update with overlap** | MEDIUM — Create overlap is tested; update that introduces overlap is not. |
| T-8 | **No load/performance tests** | LOW — Acceptable for single-user MVP. |
| T-9 | **`conftest.py` uses session-scoped server** | LOW — Tests share server state, which can cause order-dependent failures. |

---

## 7. OZ (Warp) Integration Assessment: Ollama vs. OZ Cloud Agents

### Current Design (Ollama)

Per ADR-001 and `agents.md`, the project was designed around local-first LLM inference:
- **Model:** Llama 3 (8B) or Mistral (7B) via Ollama
- **Context window:** 8k tokens
- **Prompts:** Sunday Synthesis (Narrator), Task Suggester (Architect), Co-Planning (Ambiguity Guard)
- **Integration:** Direct HTTP calls from FastAPI to local Ollama API (`http://localhost:11434`)

### OZ Cloud Agents — What It Offers

Based on [Warp/OZ documentation](https://docs.warp.dev/):

| Capability | Relevance to Our Project |
|---|---|
| **Triggers** (cron, webhook, Slack, GitHub) | High — Sunday Synthesis could be a weekly cron trigger instead of a manual button |
| **Multi-model** (choose LLM per task) | High — Different prompts (synthesis vs. suggestion) could use different models optimized for each |
| **Python & TypeScript SDKs** | High — Direct integration with our FastAPI backend via `oz-sdk-python` |
| **Task lifecycle tracking** | Medium — Built-in state machine (`QUEUED → INPROGRESS → SUCCEEDED/FAILED`) |
| **MCP server support** | Medium — Could expose our backend as an MCP server for OZ agents to query |
| **Secrets management** | Medium — API keys managed centrally, not in `.env` |
| **Session sharing / observability** | Low — Single user, but useful for debugging |
| **Self-hosted execution** | High — Enterprise plan allows agents on our infrastructure (privacy compliance) |

### Architectural Impact of Switching to OZ

| Area | Change Required |
|---|---|
| **Backend `services/` layer** | Replace planned `ollama_service.py` with `oz_service.py` wrapping the OZ Python SDK. The service abstraction (prompt in → structured response out) remains the same. |
| **ADR-001 (Local-First AI)** | Needs revision. OZ is cloud-based. If privacy is paramount, self-hosted OZ execution preserves the spirit. Standard OZ cloud execution violates the "no external AI APIs" rule. |
| **New dependency** | `oz-sdk-python` (or raw REST calls to OZ API). Credit-based billing model. |
| **Prompt engineering** | Same prompts work — OZ executes them via the selected model. Minor adaptation for OZ's prompt format (base prompt + task prompt). |
| **Sunday Synthesis trigger** | Could become an OZ scheduled trigger (cron) instead of a manual `/ai/synthesize` endpoint. The endpoint would still exist but could optionally delegate to OZ. |
| **Error handling** | OZ tasks have their own failure modes (credit exhaustion, queue timeout, model errors). Need retry logic and graceful degradation. |
| **Environment setup** | OZ environments need our backend accessible (for data queries). Options: (a) OZ agent calls our API, (b) we package data into the prompt context. |

### Recommended Hybrid Approach

Design the `services/ai/` layer with a **provider abstraction**:

```
services/
  ai/
    __init__.py
    base.py          # Abstract AIProvider protocol
    ollama_provider.py   # Local Ollama implementation
    oz_provider.py       # OZ Cloud Agent implementation
    prompts.py           # Shared prompt templates (from agents.md)
```

- `AIProvider` defines `async def synthesize(context: SynthesisInput) -> SynthesisOutput`
- Config flag `AI_PROVIDER=ollama|oz` selects the implementation
- Ollama remains the default for dev/offline use
- OZ used for production/scheduled tasks where cloud execution is acceptable
- Both providers consume the same prompt templates from `agents.md`

This preserves the "no external AI APIs" rule for dev/privacy-sensitive use while enabling OZ for production scale.

### Key OZ Considerations

1. **Cost:** OZ uses credit-based billing. Sunday Synthesis (weekly, ~1 run) is cheap. Task Suggester (per-session, possibly daily) could accumulate. Budget accordingly.
2. **Latency:** Cloud agents have queue time + execution time. Not suitable for real-time UI interactions — fine for Sunday Synthesis (background) and task suggestions (async notification).
3. **Privacy:** Standard OZ sends prompts to Warp's infrastructure. Self-hosted execution (Enterprise) keeps data on your infra. Evaluate based on sensitivity of ActionLog/Report data.
4. **BYOK Not Supported for Cloud Agents:** Per OZ docs, Bring Your Own Key doesn't work with cloud agents. All runs consume Warp credits.

---

## 8. Pre-Phase-4 Hardening Checklist

Priority items to address in Phase 3.2 bug-fix work before starting Phase 4:

### Must-Do (Blocking Phase 4)

- [ ] **Introduce Alembic** for schema migrations (H-7, F-6) — Phase 4 will add new tables/columns for AI results
- [ ] **Fix JWT secret startup check** (S-1) — Cannot deploy without this
- [ ] **Replace `python-jose` with `PyJWT`** (S-4) — Security vulnerability
- [ ] **Design AI provider abstraction** for Ollama/OZ dual support (§7)
- [ ] **Add rate limiting** on `/login` at minimum (S-6)

### Should-Do (Reduces Risk)

- [ ] Fix concurrent session race condition (C-1)
- [ ] Fix `SystemState.user_id` nullable (C-2)
- [ ] Fix `sessions/start` returning 201 for existing sessions (H-1)
- [ ] Fix update task null-field handling (H-3)
- [ ] Remove redundant alias configs in schemas (H-4, H-5)
- [ ] Add composite indexes (M-1, M-2)
- [ ] Add frontend error boundary (L-1)
- [ ] Consolidate deprecated `datetime.utcnow()` in tests (M-4)
- [ ] Add cross-user isolation tests for reports and system states (T-5)

### Nice-to-Have (Post-Phase-4)

- [ ] Migrate to `httpOnly` cookies (S-2)
- [ ] Add CSRF protection (S-8)
- [ ] Add JWT audience/issuer claims (S-9)
- [ ] Implement token revocation (S-10)
- [ ] Switch to `bcrypt`/`argon2` hashing (S-11)
- [ ] Add frontend automated tests (T-1)
- [ ] Consolidate polling into WebSocket or SSE (M-8)
- [ ] Rename ActionLog `task_id` to `entity_id` (M-5)
- [ ] Add frontend request timeouts (F-8)

---

## 9. Dependency Health

| Package | Version | Status | Action |
|---|---|---|---|
| `fastapi` | >=0.100,<0.110 | Outdated — current is 0.115+ | Update after Phase 4 |
| `uvicorn` | 0.22.0 | Outdated — current is 0.32+ | Update (pinned exact) |
| `SQLAlchemy` | 2.0.20 | Slightly behind 2.0.36 | Minor update safe |
| `pydantic` | >=2.12.5 | Current | OK |
| `python-jose` | 3.3.0 | **Unmaintained, CVEs** | **Replace with PyJWT** |
| `passlib` | 1.7.4 | Last release 2020 | Consider `argon2-cffi` directly |
| `aiosqlite` | 0.18.0 | Slightly behind 0.20 | Minor update safe |
| `next` | 14.0.0 | Behind — current is 15.x | Update after stabilization |
| `react` | 18.2.0 | Behind — React 19 is stable | Update after Next.js update |
| `recharts` | ^2.12.0 | Current | OK |
| `@hey-api/openapi-ts` | ^0.93.1 | Dev dep, current | OK |

---

## 10. Summary & Recommendations

**The project is feature-complete through Phase 3 of the PDD roadmap.** All CRUD operations, ambient sensing, silence detection, and qualitative input features are implemented and tested on the backend. The frontend delivers a functional dark-themed Bento Grid dashboard across two pages (Tasks, Reports) with real-time polling.

**Phase 4 (AI/LLM integration) is the final major milestone** and the most architecturally complex. The Ollama-vs-OZ decision should be made before starting implementation, as it affects the service layer design, deployment architecture, and cost model.

**Critical pre-deployment issues** center around authentication security (JWT secret, token storage, `python-jose`), schema migration tooling (Alembic), and the absence of rate limiting. These should be addressed in the current Phase 3.2 stabilization window.

**The codebase is healthy for a single-user dev tool** but has identifiable gaps (race conditions, nullable user_id columns, no foreign keys, no frontend tests) that would become hard bugs at scale. The hardening checklist in §8 prioritizes these by deployment urgency.
