# Phase 4.1 — MVP Bug-Fix Sprint (Pre-Deployment Hardening)

## Scope

Address all actionable bugs and code-quality issues identified in the [MVP Final Audit](../../MVP_FINAL_AUDIT.md) that do **not** require cloud services, database migrations, or production deployment infrastructure. This phase focuses exclusively on logic bugs, code hardening, type safety, UI responsiveness, and test reliability — everything that can be fixed in the current local-dev environment with zero schema changes to existing tables.

### Explicitly Out of Scope

The following audit items are **excluded** because they require cloud deployment, database migrations, or infra changes:

| Audit Item | Reason Excluded |
|---|---|
| JWT → httpOnly cookies (S-2) | Requires deployment + cookie auth infrastructure |
| HTTPS enforcement (S-3) | Requires reverse proxy (nginx/Caddy) |
| CSRF protection (S-8) | Depends on S-2 cookie auth |
| CORS localhost guard in prod | Deployment-time config; fail-closed guard already present |
| Missing composite indexes on `ai_usage_logs` | Requires `ALTER TABLE` migration |
| Missing `ForeignKey` constraints on `user_id` | Requires `ALTER TABLE` migration |
| Dev DB missing indexes | Requires running migration script against live DB |
| Nullable `user_id` columns → NOT NULL | Requires `ALTER TABLE` migration |
| Remove `passlib` dependency | Trivial housekeeping, not a bug |

## Phase-level Deliverables

1. **Ghost List fully functional** — ActionLog middleware writes semantic action types; GhostListService counts match.
2. **Task update can clear nullable fields** — `deadline`, `notes`, `tags`, `priority` can be set to `null`.
3. **TypeScript strict mode enabled** — all type errors resolved.
4. **Backend hardening** — `get_settings()` cached, N+1 fixed, OZ exceptions mapped to HTTP codes, AI error messages sanitized, `get_current_user()` verifies user exists in DB, ManualReport status enum includes `archived`, SQLite-specific SQL removed.
5. **OZ response parsing hardened** — greedy JSON regex replaced with safe extraction.
6. **Frontend resilience** — `Promise.all` replaced with `Promise.allSettled`, fragile 401 detection fixed, `isReEntryMode` wired through, duplicate types removed.
7. **Mobile-responsive UI** — NavBar hamburger/drawer, responsive task table and grids.
8. **Test harness fixed** — `test_stats`, `test_sessions`, `test_system_states` pass reliably.

## Steps (ordered)

1. Step 1 — [step-1-ghost-list-action-types.md](./step-1-ghost-list-action-types.md) — Fix ActionLog middleware to write semantic action types and align GhostListService
2. Step 2 — [step-2-task-update-nullable-fields.md](./step-2-task-update-nullable-fields.md) — Allow task update to clear nullable fields
3. Step 3 — [step-3-backend-hardening.md](./step-3-backend-hardening.md) — Cache `get_settings()`, fix N+1 query, add `archived` to report status enum, verify user exists in `get_current_user()`
4. Step 4 — [step-4-oz-error-handling.md](./step-4-oz-error-handling.md) — Map OZ exceptions to HTTP errors, sanitize AI error messages, harden JSON regex
5. Step 5 — [step-5-flow-state-portability.md](./step-5-flow-state-portability.md) — Replace SQLite-specific SQL in flow state service with portable expressions
6. Step 6 — [step-6-frontend-resilience.md](./step-6-frontend-resilience.md) — Fix `Promise.all`, 401 detection, `isReEntryMode`, remove duplicate types
7. Step 7 — [step-7-typescript-strict-mode.md](./step-7-typescript-strict-mode.md) — Enable TypeScript strict mode and resolve all type errors
8. Step 8 — [step-8-mobile-responsive-ui.md](./step-8-mobile-responsive-ui.md) — NavBar hamburger/drawer, responsive tables and grids
9. Step 9 — [step-9-test-harness-fix.md](./step-9-test-harness-fix.md) — Fix test fixture harness for `test_stats`, `test_sessions`, `test_system_states`

## Merge Order

Steps 1–5 are backend-only and can be merged independently (no cross-dependencies except Step 4 depends on Step 3 for cached settings). Steps 6–8 are frontend-only and can be parallelized. Step 9 (test harness) should merge last to validate all prior steps.

1. `.github/artifacts/phase4-1/plan/step-1-ghost-list-action-types.md` — branch: `phase-4.1/step-1-ghost-list-action-types`
2. `.github/artifacts/phase4-1/plan/step-2-task-update-nullable-fields.md` — branch: `phase-4.1/step-2-task-update-nullable-fields`
3. `.github/artifacts/phase4-1/plan/step-3-backend-hardening.md` — branch: `phase-4.1/step-3-backend-hardening`
4. `.github/artifacts/phase4-1/plan/step-4-oz-error-handling.md` — branch: `phase-4.1/step-4-oz-error-handling` (after step 3)
5. `.github/artifacts/phase4-1/plan/step-5-flow-state-portability.md` — branch: `phase-4.1/step-5-flow-state-portability`
6. `.github/artifacts/phase4-1/plan/step-6-frontend-resilience.md` — branch: `phase-4.1/step-6-frontend-resilience`
7. `.github/artifacts/phase4-1/plan/step-7-typescript-strict-mode.md` — branch: `phase-4.1/step-7-typescript-strict-mode` (after step 6)
8. `.github/artifacts/phase4-1/plan/step-8-mobile-responsive-ui.md` — branch: `phase-4.1/step-8-mobile-responsive-ui`
9. `.github/artifacts/phase4-1/plan/step-9-test-harness-fix.md` — branch: `phase-4.1/step-9-test-harness-fix` (last)

## Phase Acceptance Criteria

1. `pytest -q` passes all tests including previously-failing `test_stats`, `test_sessions`, `test_system_states`.
2. `npm run build` succeeds with `"strict": true` in `tsconfig.json` and zero TypeScript errors.
3. Ghost list correctly categorizes tasks as "stale" or "wheel-spinning" based on action counts.
4. Task PUT endpoint successfully clears `deadline`, `notes`, `tags`, `priority` when sent as explicit `null`.
5. AI service errors return structured HTTP 429/503 instead of raw 500 with stack traces.
6. NavBar collapses to hamburger menu on viewports < 768px.
7. Task table is horizontally scrollable or stacked on mobile.
8. `Promise.allSettled` degradation allows partial dashboard load on single API failure.
9. No SQLite-specific SQL functions remain in production code paths.

## Concurrency Groups & PR Strategy

### Group A — Backend Logic (Steps 1–5)
- **Parallelizable:** Steps 1, 2, 3, 5 (no cross-file conflicts)
- **Sequential:** Step 4 depends on Step 3 (`get_settings` cache must exist before OZ client changes reference it)
- Branch naming: `phase-4.1/step-<N>-<short-desc>`

### Group B — Frontend (Steps 6–8)
- **Parallelizable:** Steps 6 and 8 (different files)
- **Sequential:** Step 7 depends on Step 6 (strict mode will surface errors that Step 6 fixes must address first)
- Branch naming: `phase-4.1/step-<N>-<short-desc>`

### Group C — Test Infrastructure (Step 9)
- **Merge last:** Validates all prior backend changes against the full test suite.
- Depends on: Steps 1–5 merged.

## Verification Plan

### Automated

```bash
# Backend — run full test suite from code/backend/
cd code/backend && python -m pytest -q --tb=short

# Frontend — production build with strict mode
cd code/frontend && npm run build

# Specific ghost list test
cd code/backend && python -m pytest tests/test_ghost_list.py -v

# Specific stats/sessions/system_states tests (previously failing)
cd code/backend && python -m pytest tests/test_stats.py tests/test_sessions.py tests/test_system_states.py -v
```

### Manual Smoke Tests

1. **Ghost List:** Create a task, wait (or backdate `created_at`), hit `GET /stats/ghost-list` — verify task appears with correct `ghostReason`.
2. **Task Null Clear:** Create task with deadline, then PUT with `{"deadline": null}` — verify deadline is cleared.
3. **AI Errors:** Temporarily set `OZ_API_KEY=invalid`, call `POST /ai/suggest` — verify 503 (not 500 with stack trace).
4. **Mobile NavBar:** Resize browser to 375px width — verify hamburger icon appears and tabs are in drawer.
5. **Partial Dashboard Load:** Stop backend, start only frontend, navigate to `/tasks` — verify graceful degradation (no full-page crash).

## Risks, Rollbacks & Migration Notes

| Risk | Likelihood | Mitigation |
|---|---|---|
| Changing ActionLog `action_type` format breaks existing Ghost List counts for old data | Medium | Ghost service already handles 0-action-count as "stale" — old logs simply won't match new types, which is functionally correct (old data appears stale, not miscounted) |
| TypeScript strict mode reveals many errors | High | Step 7 is dedicated solely to resolving strict-mode errors; Step 6 fixes the most common patterns first |
| `Promise.allSettled` changes observable behavior | Low | Each settled result is checked; rejected results fall back to null/empty defaults |
| `get_current_user()` DB lookup adds latency per request | Low | Single primary-key lookup by `user_id`; negligible on SQLite. Can add in-memory cache later if needed |

**No database migrations required.** No persistence changes. No backup steps needed.

## References

- [MVP Final Audit](../../MVP_FINAL_AUDIT.md)
- [PDD](../../PDD.md)
- [Architecture](../../architecture.md)
- [PLANNING.md](../../PLANNING.md)
- [Copilot Instructions](../../copilot-instructions.md)

## Author Checklist (master)

- [x] All step files created and linked
- [x] Phase-level acceptance criteria are measurable
- [x] PR/merge order documented
- [x] Concurrency groups defined
- [x] Out-of-scope items explicitly listed
- [x] Verification plan includes automated + manual checks
- [x] Risks enumerated with mitigations
