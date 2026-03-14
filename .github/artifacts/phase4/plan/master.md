# Phase 4 — Sunday Synthesis & Co-Planning (OZ Edition)

## Scope

Phase 4 delivers the intelligence layer of the Ambient AI Productivity Dashboard. This phase implements the three agentic features defined in the PDD — **Sunday Synthesis**, **Task Suggester**, and **Co-Planning (Ambiguity Guard)** — plus the supporting UI surfaces (Sunday Modal, Reasoning Sidebar, Ghost List visualization).

**Key architectural change:** The original PDD specified Ollama for local-first LLM inference. This phase replaces Ollama with **OZ (Warp's cloud agent platform)** as the inference backend. OZ provides a multi-model cloud agent API with Python/TypeScript SDKs, scheduled triggers, and zero-data-retention LLM policies. This decision is recorded as **ADR-003** in Step 1.

**Implications of Ollama → OZ:**
- **Privacy:** Warp is SOC 2 compliant with zero data retention from LLM providers. Acceptable for a personal dashboard.
- **Cost (CRITICAL — NO FREE TIER):** OZ uses a credit-based billing model — every `POST /agent/run` call consumes credits based on tokens, model, and tool calls. **There is no free unlimited tier.** All implementation choices in Steps 1–7 must minimise credit consumption. Rate limiting is mandatory and non-negotiable. See the [Rate Limiting & Cost Control Architecture](#rate-limiting--cost-control-architecture-mandatory) section for enforcement rules.
- **Latency:** Cloud inference replaces local inference. Expected 10–60s per synthesis run depending on context size and model. Asynchronous execution pattern mitigates UX impact.
- **Infrastructure:** Eliminates the requirement for local GPU/CPU resources for LLM inference.
- **MCP Extensibility:** OZ supports MCP servers, opening a future path where the agent autonomously queries our API. Phase 4 uses a simpler "context-in-prompt" pattern for MVP.

**Pre-existing technical debt addressed in this phase:**
- M-1/M-2: Missing composite indexes on `action_logs` and `session_logs` (Step 5)
- M-3: In-memory flow calculation moved to SQL aggregation (Step 5)

## Phase-level Deliverables

- **ADR-003:** Ollama → OZ migration decision record
- **OZ Client Service:** Async wrapper around the OZ Agent API (Python SDK) with config, error handling, result parsing, and mock mode (zero real API calls in dev/tests)
- **Rate Limiting Infrastructure (Step 1 — foundation for all AI endpoints):** `AIRateLimiter` service, `AIUsageLog` model (`ai_usage_logs` table), and `GET /ai/usage` endpoint. All Steps 2–7 depend on this; no AI endpoint may call OZ without first passing through `AIRateLimiter.check_limit()`.
- **Inference Context Builder:** Service that collects and formats all ambient data (tasks, action logs, reports, system states, silence gaps) into structured JSON for prompt injection. Enforces the `oz_max_context_chars` hard cap before any token ever reaches OZ.
- **Sunday Synthesis Backend:** `POST /ai/synthesis`, `GET /ai/synthesis/latest`, `GET /ai/synthesis/{id}` — trigger, retrieve, and list AI-generated weekly narratives stored in a new `SynthesisReport` model
- **Task Suggester Backend:** `POST /ai/suggest-tasks` — AI-generated task recommendations with re-entry mode awareness
- **Co-Planning Backend:** `POST /ai/co-plan` — ambiguity detection in manual reports with resolution questions
- **Ghost List Endpoint:** `GET /stats/ghost-list` — tasks showing signs of wheel-spinning (edits without progress, stale open tasks)
- **Sunday Synthesis Modal UI:** Full-page or modal view displaying weekly narrative, theme, commitment score, and suggested tasks with accept/reject
- **Reasoning Sidebar UI:** Zone C of the Bento Grid — inference cards, ghost list visualization, and re-entry mode banner
- **Type Sync:** Regenerated TypeScript client covering all new endpoints
- **Backend tests:** Comprehensive test coverage for all new endpoints and services
- **E2E smoke test:** Full synthesis trigger → result display flow

## Rate Limiting & Cost Control Architecture (Mandatory)

> **This section is required reading before implementing any step in Phase 4.** Implementing agents must understand and strictly follow these rules. Violations will cause real credit charges on a personal billing account.

### Why This Exists
OZ has no free tier for API-triggered agent runs. Every `POST /agent/run` call bills the account. This is a personal project — unchecked calls would result in an unexpected bill. The rate limiting infrastructure in Step 1 is the cost safety net for the entire phase.

### Hard Caps (defined in `core/config.py`)

| Endpoint | Cap | Window | Config Key |
|---|---|---|---|
| `POST /ai/synthesis` | 3 runs | per week | `oz_max_synthesis_per_week` |
| `POST /ai/suggest-tasks` | 5 runs | per day | `oz_max_suggestions_per_day` |
| `POST /ai/co-plan` | 3 runs | per day | `oz_max_coplan_per_day` |
| `POST /ai/accept-tasks` | No limit | N/A | No OZ call — exempt |
| Context size | 8,000 chars | per call | `oz_max_context_chars` |
| Default model | `anthropic/claude-haiku-4` | — | `oz_model_id` |

### Non-Negotiable Order of Operations

Every AI service method that calls OZ **must** follow this exact sequence. No exceptions:

```
1. check_limit()   ← FIRST. Before context build, before DB writes, before OZ.
2. build_context() ← Only runs when a slot is available.
3. build_prompt()  ← Enforces oz_max_context_chars hard cap.
4. oz_client.run() ← Real or mock depending on oz_api_key.
5. parse_response() ← Extract JSON from OZ session transcript.
6. persist_result() ← Save to DB only on success.
7. record_usage()  ← LAST. Only after a real, successful OZ parse.
                      NEVER for errors. NEVER for mock-mode calls.
```

**Exception — Co-plan short-circuit:** In `co_plan()`, a report-length check (`< 20 words`) runs before step 1. Bad input must NOT consume a daily slot.

### Mock Mode Rule (Tests & Development)

When `oz_api_key == ""` (default in dev/CI):
- `OZClient.run_prompt()` returns a deterministic JSON fixture from `tests/fixtures/mock_oz_synthesis.json`.
- **No HTTP call is made. No credits are consumed.**
- `record_usage()` is NOT called — mock runs are not recorded against caps.
- Tests MUST always run in mock mode. Failing to patch `OZClient` in a test that exercises a 429 or error path is a bug — tests must assert `OZClient.run_prompt` was **never called** in those paths.

### Frontend Surfacing

- `GET /ai/usage` returns `{ synthesis: {used, limit, resetsIn}, suggest: {...}, coplan: {...} }` — fetched on mount by `ReasoningSidebar` and the `/synthesis` page.
- The co-plan "Analyze" button in `ReportCard` is `disabled` when `coplan.used >= coplan.limit`.
- AI usage summary line at the bottom of `ReasoningSidebar` (e.g. "Synthesis: 1/3 this week · Tasks: 2/5 today").
- 429 responses must be surfaced as user-readable messages (e.g. `InferenceCard` type `warning`), not raw HTTP errors.

### Reviewing Agent Checklist (before approving any Phase 4 PR)

- [ ] Does every AI service method that calls OZ call `check_limit()` as its **first** statement?
- [ ] Does `record_usage()` only appear **after** a successful OZ parse — and never in error handlers or mock paths?
- [ ] Does the `co_plan()` short-circuit check precede the `check_limit()` call?
- [ ] Are all tests patching `OZClient.run_prompt` and asserting it was **not called** in 429/short-circuit scenarios?
- [ ] Is `POST /ai/accept-tasks` confirmed exempt (no rate limit, no OZ call)?
- [ ] Do all frontend AI trigger surfaces fetch and display `GET /ai/usage` data?

## Steps (ordered)

1. Step 1 — [step-1-oz-integration-layer.md](./step-1-oz-integration-layer.md)
2. Step 2 — [step-2-inference-context-builder.md](./step-2-inference-context-builder.md)
3. Step 3 — [step-3-sunday-synthesis.md](./step-3-sunday-synthesis.md)
4. Step 4 — [step-4-task-suggester-co-planning.md](./step-4-task-suggester-co-planning.md)
5. Step 5 — [step-5-ghost-list-analytics.md](./step-5-ghost-list-analytics.md)
6. Step 6 — [step-6-synthesis-ui.md](./step-6-synthesis-ui.md)
7. Step 7 — [step-7-reasoning-sidebar-type-sync.md](./step-7-reasoning-sidebar-type-sync.md)

## Merge Order

1. `.github/artifacts/phase4/plan/step-1-oz-integration-layer.md` — branch: `phase-4/step-1-oz-integration-layer`
2. `.github/artifacts/phase4/plan/step-2-inference-context-builder.md` — branch: `phase-4/step-2-inference-context-builder`
3. `.github/artifacts/phase4/plan/step-3-sunday-synthesis.md` — branch: `phase-4/step-3-sunday-synthesis`
4. `.github/artifacts/phase4/plan/step-4-task-suggester-co-planning.md` — branch: `phase-4/step-4-task-suggester-co-planning`
5. `.github/artifacts/phase4/plan/step-5-ghost-list-analytics.md` — branch: `phase-4/step-5-ghost-list-analytics`
6. `.github/artifacts/phase4/plan/step-6-synthesis-ui.md` — branch: `phase-4/step-6-synthesis-ui`
7. `.github/artifacts/phase4/plan/step-7-reasoning-sidebar-type-sync.md` — branch: `phase-4/step-7-reasoning-sidebar-type-sync`

## Phase Acceptance Criteria

### Functional
1. `POST /ai/synthesis` returns 202 with a `runId` and triggers an OZ agent run.
2. `GET /ai/synthesis/latest` returns the most recent completed `SynthesisReport` with JSON shape `{ id, summary, theme, commitmentScore, suggestedTasks, createdAt }`.
3. `POST /ai/suggest-tasks` returns 200 with a JSON array of 3–5 task suggestions.
4. `POST /ai/co-plan` with a report containing conflicting goals returns 200 with a resolution question.
5. `GET /stats/ghost-list` returns 200 with a list of stale/wheel-spinning tasks.
6. Sunday Synthesis modal displays narrative, theme, and commitment score. Suggested tasks have Accept/Dismiss actions.
7. Reasoning Sidebar (Zone C) renders inference cards and ghost list on the tasks page.
8. Re-entry mode: when an active `SystemState` with `requiresRecovery=True` ends, the Task Suggester returns low-friction tasks.
9. All new AI endpoints are JWT-guarded and user-scoped.
10. `pytest code/backend/tests/ -q` exits 0 with ≥100 tests (currently 89).
11. TypeScript client regenerated and frontend compiles with `npm run build` exit 0.
12. `grep -r "ollama" code/` returns zero results (no references to the deprecated local inference approach).
13. OZ API key is loaded from config with a startup guard in non-dev environments (no hardcoded keys).
14. Manual QA: trigger synthesis from the UI, see narrative appear within 90 seconds.

### Rate Limiting (Non-Negotiable — every criterion below must pass before phase is considered complete)
15. `POST /ai/synthesis` returns **429** (with reset date in response body) after 3 runs in the current calendar week.
16. `POST /ai/suggest-tasks` returns **429** (with reset time in response body) after 5 runs in the current calendar day.
17. `POST /ai/co-plan` returns **429** (with reset time in response body) after 3 runs in the current calendar day.
18. `POST /ai/accept-tasks` **never** returns 429 — it has no OZ call and no rate limit.
19. `POST /ai/co-plan` with a report body < 20 words returns `{ "hasConflict": false }` **without** consuming a daily co-plan slot (assert `ai_usage_logs` table has no new entry).
20. `GET /ai/usage` returns `{ synthesis: {used, limit, resetsIn}, suggest: {...}, coplan: {...} }` with correct counts reflecting real usage.
21. A failed OZ run (timeout, malformed JSON, OZ 5xx) does **not** increment `ai_usage_logs` — the cap slot is preserved.
22. All tests exercise mock mode only (`OZClient.run_prompt` is patched — never calls real OZ API during `pytest`).
23. Tests verifying 429 behavior explicitly assert that `OZClient.run_prompt` was **not called** (zero invocations).
24. `GET /ai/usage` is fetched on mount by `ReasoningSidebar` and the `/synthesis` page; usage summary is visible in the UI.
25. The co-plan "Analyze" button in `ReportCard` is `disabled` (with tooltip) when `coplan.used >= coplan.limit`.

## Concurrency groups & PR strategy

**Group A (Backend Foundation) — Sequential:**
- Step 1 → Step 2 → Step 3 → Step 4 (strict dependency chain: client → context → synthesis → suggester)

**Group B (Analytics) — Parallelizable after Step 2:**
- Step 5 can be developed in parallel with Steps 3–4 since it only depends on Step 2's context builder

**Group C (Frontend) — Parallelizable after Step 3:**
- Step 6 (Synthesis UI) can start after Step 3 merges (needs synthesis endpoints)
- Step 7 (Reasoning Sidebar) can start after Steps 4 and 5 merge (needs all backend endpoints + type sync)

**Merge order:**
```
Step 1 ──► Step 2 ──┬──► Step 3 ──► Step 4 ──┬──► Step 7
                     │                         │
                     └──► Step 5 ──────────────┘
                     │
                     └──► Step 6 (after Step 3) ┘
```

All frontend steps (6, 7) must merge after their backend dependencies. Step 7 is the final integration step that includes type sync and E2E tests.

## Verification Plan

### Automated Tests
```bash
# Full backend test suite
cd code/backend && python -m pytest tests/ -q --tb=short

# AI-specific tests
cd code/backend && python -m pytest tests/test_ai.py tests/test_ghost_list.py -v

# E2E synthesis flow
cd code/backend && python -m pytest tests/e2e/test_synthesis_flow.py -v

# Frontend build
cd code/frontend && npm run build
```

### Smoke Test Checklist
1. Start backend (`make dev`), verify `/health` returns 200.
2. Login → navigate to Tasks page → confirm Reasoning Sidebar placeholder renders.
3. Navigate to Synthesis page → click "Generate Synthesis" → confirm 202 accepted.
4. Wait ≤90s → confirm synthesis result populates (narrative, theme, score).
5. Confirm suggested tasks appear → Accept one → verify it appears in task list.
6. Dismiss remaining suggestions → verify they are removed.
7. Navigate to Tasks page → confirm Ghost List section shows stale tasks (or empty state).
8. Set a SystemState with `requiresRecovery=True`, end date = today → trigger task suggestions → verify low-friction suggestions.
9. Confirm all AI endpoints return 401 without a valid JWT.

### Rate Limit Smoke Tests (run after the functional smoke tests above)
10. `curl -X GET /ai/usage` → verify `synthesis.used`, `suggest.used`, `coplan.used` reflect the runs from steps 3–8 above.
11. Check that the `/synthesis` page shows a usage line (e.g. "1/3 synthesis runs used this week").
12. With `sqlite3 data/dev.db "SELECT * FROM ai_usage_logs;"` → verify rows are present only for completed real OZ calls (not for mock mode or failed calls).
13. In dev with `OZ_API_KEY=""` (mock mode): run `pytest tests/test_ai.py -v` → confirm all tests pass and no HTTP calls were made to OZ (check logs for "OZ mock mode active").
14. Manually exhaust the synthesis weekly cap (3 runs) → confirm the 4th request returns 429 with a readable reset date, and the `ReasoningSidebar` displays the updated count.

### Coverage Expectations
- Backend: ≥100 tests total, ≥15 new tests covering AI endpoints, context builder, ghost list
- Frontend: Manual QA only (consistent with Phase 1–3 pattern; frontend testing debt noted)

## Risks, Rollbacks & Migration Notes

| Risk | Severity | Mitigation |
|---|---|---|
| OZ API unavailability or rate limiting | HIGH | Implement circuit breaker in `oz_client.py`. All AI endpoints return graceful 503 with retry-after. Synthesis results are cached — last successful result remains available. |
| OZ credit exhaustion | HIGH | `AIRateLimiter` enforces hard caps per endpoint before any OZ call is made (3 synthesis/week, 5 suggest/day, 3 coplan/day). `record_usage()` only fires after a real successful OZ parse — errors and mock-mode calls never count. `AI_ENABLED=false` disables all AI endpoints instantly. Default model is `claude-haiku-4` (~10× cheaper than Sonnet). Context capped at 8,000 chars. No scheduled or background OZ calls — all runs are strictly on-demand. |
| Rate limit check bypassed by a careless implementation | HIGH | Enforced by the [Rate Limiting & Cost Control Architecture](#rate-limiting--cost-control-architecture-mandatory) section in this document. Every PR touching an AI service method must pass the Reviewing Agent Checklist above. `check_limit()` must appear as the first statement; `record_usage()` only after successful parse. |
| Prompt token overflow (large context windows) | MEDIUM | `InferenceContextBuilder` is the last line of defence before tokens reach OZ. Context hard-capped at `oz_max_context_chars = 8000`. `PromptBuilder` enforces this cap — truncation is visible in logs. Prioritize recency: last 7 days, max 50 action logs, max 5 reports, 200-char report preview only. |
| OZ response format changes | LOW | Parse OZ responses defensively with Pydantic validation. Log raw responses for debugging. Version-pin the OZ Python SDK. |
| New `SynthesisReport` table requires migration | LOW | Use `create_all` for dev (new table, not a column addition). Document Alembic migration path for prod. Pre-merge: backup `dev.db`. |
| Privacy concern — sending user data to cloud LLM | LOW | Document in ADR-003. OZ/Warp has zero-data-retention policy. Context is limited to task names, timestamps, and report text — no PII beyond what the user writes. User controls what reports contain. |

### Rollback Procedure
1. If OZ integration fails post-merge: set `AI_ENABLED=false` in `.env` to disable all `/ai/*` endpoints. The existing dashboard remains fully functional.
2. If the `synthesis_reports` table causes issues: drop the table (`DROP TABLE IF EXISTS synthesis_reports;`) — no other tables reference it.
3. Pre-merge backup: `cp data/dev.db data/dev.db.pre-phase4.bak`

## References

- [PDD.md](../../PDD.md) — Phase 4 roadmap, Sunday Synthesis, Co-Planning, Ghost List specifications
- [agents.md](../../agents.md) — Prompt engineering: Prompt A (Synthesis), Prompt B (Task Suggester), Prompt C (Co-Planning)
- [architecture.md](../../architecture.md) — Data schemas, API design, Type Sync workflow
- [product.md](../../product.md) — Feature overview, UI zones, state-aware styling
- [final-report-3-2.md](../../final-report-3-2.md) — Phase 3.2 completion audit, pre-existing issues inventory
- [OZ Platform Docs](https://docs.warp.dev/agent-platform/cloud-agents/platform) — Orchestrator, SDK, API, environments
- [OZ Agent API](https://docs.warp.dev/reference/api-and-sdk/agent) — `POST /agent/run`, `GET /agent/runs`, `GET /agent/runs/{runId}`
- [OZ Python SDK](https://github.com/warpdotdev/oz-sdk-python) — Typed client for agent task lifecycle
- [OZ Triggers](https://docs.warp.dev/agent-platform/cloud-agents/triggers) — Scheduled agents, cron, integrations

## Author Checklist (master)

- [x] All step files created and linked
- [x] Phase-level acceptance criteria are measurable
- [x] PR/merge order documented
- [x] Concurrency groups defined with dependency arrows
- [x] ADR-003 (Ollama → OZ) scoped in Step 1
- [x] Pre-existing tech debt items (M-1, M-2, M-3) assigned to Step 5
- [x] Rollback strategy documented
- [x] Feature flag (`AI_ENABLED`) included for safe degradation
- [x] Rate Limiting & Cost Control Architecture section added — mandatory reading for all implementing agents
- [x] Rate limit hard caps documented with config keys (`oz_max_synthesis_per_week`, `oz_max_suggestions_per_day`, `oz_max_coplan_per_day`)
- [x] Non-negotiable order of operations documented (check_limit first, record_usage last)
- [x] Mock mode rule documented (tests NEVER call real OZ API)
- [x] `accept_tasks` exemption documented (no OZ call, no rate limit)
- [x] `co_plan` short-circuit ordering documented (length check before rate limit)
- [x] Reviewing Agent Checklist included for PR reviewers
- [x] Phase Acceptance Criteria include a dedicated Rate Limiting section (criteria 15–25)
- [x] Rate Limit Smoke Tests added to Verification Plan
- [x] Rate limit risk elevated to HIGH with `AIRateLimiter` bypass risk added as separate row
