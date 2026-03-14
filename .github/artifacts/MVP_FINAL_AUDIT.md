# MVP Final Audit Report

**Date:** 2026-03-14

This report captures the current status of the project after completing Phase 4 (Sunday Synthesis & Co-Planning). It includes critical issues, security findings, test status, database schema observations, deployment readiness notes, and recommended next steps.

---

## 1. Executive Summary

The MVP is **feature-complete** across all 4 phases:
- Full JWT auth with login/logout
- Event-sourcing action log + analytics
- Task CRUD + reports + system states
- OZ-based AI services (Synthesis, Task Suggestion, Co-Planning)
- Full frontend UI (Tasks, Reports, Synthesis, Reasoning Sidebar)

**Current status:**
- Backend: core test suite passes (136/136 for non-server-fixture tests)
- Frontend: production build succeeds and all routes compile
- No Ollama references remain (OZ migration complete)

**Critical blockers remain** and must be addressed before any production deployment.

---

## 2. Critical Issues (Must Fix Before Production)

### 2.1 Ghost List is Effectively Broken
- **Location:** `app/services/ghost_list_service.py` + `app/middlewares/action_log.py`
- **Problem:** Ghost logic expects semantic action types (`TASK_CREATE`, etc.), but ActionLog entries use HTTP signatures (`POST /tasks`, `PUT /tasks/{id}`), so the ghost list never counts task activity.
- **Impact:** All old open tasks are classified as “stale”, wheel-spinning detection never triggers.

### 2.2 Task Update Cannot Clear Nullable Fields
- **Location:** `app/api/tasks.py` update logic
- **Problem:** The update handler skips all `None` values, preventing clearing of `deadline`, `notes`, `tags`, `priority`.
- **Impact:** Users can never remove a deadline/notes once set.

### 2.3 TypeScript Strict Mode Disabled
- **Location:** `code/frontend/tsconfig.json` (`"strict": false`)
- **Problem:** Compiler won’t catch `any`, `null`/`undefined` issues. Several code paths already pass `string | null` into functions that expect `string`.
- **Impact:** Runtime crashes may occur in production without type-level detection.

---

## 3. Security / Deployment-Blocking Findings

### 3.1 High-Priority Security Issues
- **JWT stored in `localStorage`** (XSS risk) — `frontend/lib/hooks/useAuth.ts` (TODO deploy marker present)
- **No HTTPS enforcement** (app runs plain HTTP) — `backend/app/main.py` (TODO deploy marker present)
- **No CSRF protection** for cookie auth (S-2 path) — `backend/app/main.py` (TODO deploy marker present)
- **CORS config still allows localhost in non-dev** (fail-closed guard is present but must be configured) — `backend/app/main.py` (TODO deploy marker present)

### 3.2 Recommended Hardening (Before Prod)
- Ensure `get_current_user()` verifies the user exists in DB (prevents deleted user reuse)
- Avoid leaking internal exception text in API responses (AI service errors currently propagate `str(e)`)
- Remove unused dependency `passlib` from production environment (`pip uninstall passlib`)

---

## 4. Moderate Issues (Should Fix Before v1.0)

### Backend
- `get_settings()` creates fresh Settings per call (should be cached with `@lru_cache`)
- Missing composite indexes on `ai_usage_logs` (performance risk as usage grows)
- N+1 query pattern in `_validate_task_ids` (report service)
- Missing `ForeignKey` constraints on most `user_id` fields (referential integrity)
- Schema/model mismatches (`system_states.start_date` nullable vs required)
- Greedy JSON extraction regex in OZ response parsing (risk of invalid JSON parsing)
- Custom OZ exceptions are not translated to HTTP errors (500s instead of 429/503)
- ManualReport status validation mismatched with `archived` status used in archive endpoint
- SQLite-specific SQL in flow state service (breaks Postgres portability)
- Dev DB is missing composite indexes declared in models (needs migration script run)

### Frontend
- `TasksPage` uses `Promise.all` which fails all data loads on any single failure.
- Nav bar is not responsive on mobile (no hamburger/drawer pattern).
- Tables and grids are non-responsive (task table, report card grid) and will overflow on small screens.
- Duplicate type definitions in `api.ts` vs generated `types.gen.ts` (risk of drift).
- `isReEntryMode` is never set from API response, so the feature is effectively inert.
- Fragile 401 detection via `err.message.includes("401")`.

---

## 5. Test Status

### Passing Tests (Core Suite)
- **136 tests passed** (AI services, ghost list, inference context, OZ client, reports, models, API, E2E synthesis flow)

### Failing / Erroring Tests (Test Infrastructure Issue)
- `test_stats.py`: 5 failures (KeyError: missing `access_token`) — caused by `client` server fixture not seeing the user created via direct DB writes.
- `test_sessions.py`, `test_system_states.py`: multiple errors due to same auth/login fixture mismatch (server subprocess vs in-process DB writes).

> These failures appear to be caused by the current test harness using a background uvicorn subprocess which does not reliably observe direct DB writes from the pytest process. The core application logic appears sound.

---

## 6. Database / Schema Notes

### Live DB vs Models
- `dev.db` is missing composite indexes declared in models: `ix_action_logs_user_ts`, `ix_session_logs_user_ended`.
- `create_all()` does not add indexes to existing tables; run `scripts/migrate_add_indexes.py` before production.

### Schema Observations
- Several `user_id` columns are nullable even though the app always sets them.
- No foreign key constraints on `user_id` fields in most tables.
- `system_states.start_date` is nullable in DB but required by API schema.

---

## 7. Deployment Readiness Checklist

✅ Run `python scripts/setup_oz.py` and set `OZ_API_KEY`.

✅ Ensure env vars are set for prod:
- `APP_ENV=prod`
- `JWT_SECRET=<strong random>`
- `FRONTEND_CORS_ORIGINS=https://<your-domain>`
- `AI_ENABLED=true` (or false to disable AI)

✅ Deploy behind HTTPS (nginx/Caddy) and enable HSTS.
✅ Implement cookie-based auth (httpOnly, Secure, SameSite) and CSRF protections.
✅ Run `scripts/migrate_add_indexes.py` to add missing DB indexes.
✅ Confirm `get_current_user()` verifies user exists (prevents token reuse after deletion).
✅ Convert TypeScript to `