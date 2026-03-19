# Bug Report: CORS `(null)` Status Errors — Backend Crash Investigation

**Date:** 2026-03-19  
**Severity:** High (complete frontend data outage)  
**Status:** Resolved  

---

## Symptoms

Both `/reports` and `/tasks` pages showed a red banner:
> "Could not load reports: NetworkError when attempting to fetch resource."

Browser console flooded with:
> `Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource at http://localhost:8000/*. (Reason: CORS request did not succeed). Status code: (null).`

Affected endpoints: `/stats/pulse`, `/system-states`, `/ai/synthesis/latest`, `/ai/usage`, `/stats/ghost-list`.

---

## Root Cause Analysis — Candidates Considered

| # | Hypothesis | Verdict |
|---|-----------|---------|
| 1 | CORS header misconfiguration (wrong origin list) | **Ruled out** — `(null)` status means connection refused, not a header rejection |
| 2 | Pydantic-settings `List[str]` JSON parse failure on `FRONTEND_CORS_ORIGINS` | **Ruled out** — already patched; field declared as `str` with `get_cors_origins()` method |
| 3 | Wrong database path in `.env` causing startup crash | **Ruled out** — `.env` uses correct relative path `./data/dev.db` |
| 4 | **Backend process dead (connection refused)** | ✅ **PRIMARY CAUSE** |
| 5 | **Missing Python dependencies in local `.venv`** | ✅ **ROOT CAUSE of the crash** |
| 6 | Startup output silenced by `>/dev/null 2>&1` masking the failure | ✅ **Contributing cause — hid the crash** |

---

## Confirmed Root Cause

### 1. `ModuleNotFoundError: No module named 'slowapi'`

The backend's local `.venv` (`code/backend/.venv`) was **never fully populated** with all required dependencies. When `make start` ran, uvicorn attempted to import `app.main` which immediately failed:

```
ModuleNotFoundError: No module named 'slowapi'
```

Additional packages that had to be installed: `PyJWT`, `bleach`, `limits`, `deprecated`, `wrapt`, `webencodings`.

### 2. `make start` silenced all crash output

The pre-fix `start` target piped everything to `/dev/null`:
```makefile
PYTHONPATH=$(PWD) nohup $(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port $(PORT) >/dev/null 2>&1 & ...
```

This meant the `ModuleNotFoundError` was completely invisible. The PID file was written, making it appear the process was running — but the process died instantly on import.

### 3. `--reload` in the background `start` target (secondary)

The `start` target (intended for nohup background operation) incorrectly included `--reload`. This caused:
- Unnecessary file-system watching in a background process
- Risk of silent restart failures on any file change
- `--reload` should only be used in the interactive `dev` target

---

## Evidence

- `curl http://localhost:8000/health` returned `000` (connection refused) at investigation time.
- `ps aux | grep uvicorn` showed PID 7927 (watchdog alive) but `lsof -ti :8000` returned nothing — the worker had died and could not restart.
- After enabling log output, `logs/backend.log` immediately revealed the `ModuleNotFoundError`.
- Installing `slowapi` (and other missing packages) via `pip install -r requirements.txt` resolved the crash.

---

## Fixes Applied

### Fix 1 — Install missing backend dependencies
```bash
cd code/backend
.venv/bin/pip install -r requirements.txt
```
Installed: `slowapi==0.1.9`, `PyJWT==2.12.1`, `bleach`, `limits`, `deprecated`, `wrapt`, `webencodings`.

### Fix 2 — Harden `code/backend/Makefile` `start` target

**Before:**
```makefile
start:
    @if [ ! -x .venv/bin/python ]; then ...
    PYTHONPATH=$(PWD) nohup $(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port $(PORT) >/dev/null 2>&1 & echo $$! > ./.dev.pid && echo "PID saved to ./.dev.pid"
```

**After:**
```makefile
start:
    @if [ ! -x .venv/bin/python ]; then ...
    @mkdir -p logs
    @echo "Starting backend (background, no --reload) using $(PYTHON)"
    @PYTHONPATH=$(PWD) nohup $(PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port $(PORT) >logs/backend.log 2>&1 & echo $$! > ./.dev.pid
    @echo "PID saved to ./.dev.pid — logs at logs/backend.log"
    @echo "Waiting for backend to become ready..."
    @for i in 1 2 3 4 5 6 7 8 9 10; do \
        sleep 1; \
        if curl -sf http://127.0.0.1:$(PORT)/health >/dev/null 2>&1; then \
            echo "Backend is up on :$(PORT)"; exit 0; fi; \
    done; \
    echo "ERROR: Backend did not start within 10s — check logs/backend.log:"; \
    cat logs/backend.log 2>/dev/null || true; exit 1
```

Changes:
- **Removed `--reload`** from background start (hot-reload is for interactive `dev` only)
- **Redirected output to `logs/backend.log`** instead of `/dev/null` so crashes are diagnosable
- **Added startup smoke-check** (curl with 10-second retry loop) — exits non-zero and prints the log on failure, surfaces crashes immediately

### Fix 3 — Harden root repo `Makefile` `start` + `restart`

The root `Makefile` `start` target previously invoked the frontend using `make -C code/frontend start`, which runs `npm run start` (a **production** Next.js server requiring a prior build). In dev this would fail or hang silently.

- Changed `make start` to use `code/frontend/start-dev` (dev server) instead of production `start`.
- Updated `restart` to wait for ports 8000/3000 to be released instead of a fixed `sleep 1`, avoiding race conditions where the new server can't bind.

### Fix 4 — Harden `code/frontend/Makefile` `start-dev` target

The frontend’s `start-dev` was also silent and uncheckable:
- It ran `npm run dev > /dev/null 2>&1` with no logs.
- There was no check that `node_modules` existed (`npm ci` must run first).

Fixes applied:
- Create `logs/frontend.log` and redirect output to it.
- Add a check that `node_modules` exists (fail fast with a clear message if `make deps` wasn’t run).
- Add a 15-second startup smoke check (curl to localhost:PORT) and show logs on failure.

---

## Verification

After fixes, `make start` output:
```
Starting backend (background, no --reload) using .venv/bin/python
PID 15428 saved to ./.dev.pid — logs at logs/backend.log
Waiting for backend to become ready...
Backend is up on :8000
```

`curl http://localhost:8000/health` returns `{"status":"ok"}`.

---

## Hard-Won Lessons Referenced

This bug violated two documented hard-won lessons that were **not yet acted upon**:

> **"Silent `nohup` startup hides crashes"** — The `make start` target uses `>/dev/null 2>&1`, so any crash at startup is swallowed. Always verify the process is alive and `/health` returns 200 after starting. A startup smoke check (curl with retry) should be added to the `start` target to surface failures immediately.

> **"Status code `(null)` in a browser CORS error means 'connection refused' not a header problem"** — When the browser reports `CORS request did not succeed` with `Status code: (null)`, the backend process is not responding at all. Do not spend time debugging CORS headers; check that the server process is alive first (`curl /health`).

Both lessons are now enforced structurally in the Makefile.

---

## Follow-Up Bug: Tasks & Reports Empty After Re-Login (User ID Orphan)

**Date:** 2026-03-19  
**Symptom:** After re-logging in (fresh JWT), tasks and reports pages showed "No tasks yet" / "No reports yet" — no console errors, no 401s. Auth was working.

### Root Cause Analysis — Candidates Considered

| # | Hypothesis | Verdict |
|---|-----------|---------|
| 1 | Data was wiped by `create_all` on startup | **Ruled out** — rows confirmed present in DB via `sqlite3` |
| 2 | Frontend filter hiding completed/non-matching rows | **Ruled out** — all completion states checked |
| 3 | API calls not being made (component bug) | **Ruled out** — Network tab shows requests succeeding |
| 4 | **User ID changed: `create_dev_user.py` deleted & recreated devuser with a new UUID** | ✅ **ROOT CAUSE** |

### Confirmed Root Cause

`scripts/create_dev_user.py` previously **deleted and recreated** the devuser on every run, generating a fresh UUID each time. All existing tasks, reports, action logs, and system states retained the old `user_id`. Since the API filters every query by `user_id` from the JWT, the data was invisible — it existed in the DB but belonged to a now-orphaned ID.

```
DB user id now:   0a784806-4f2d-4bf8-b4c5-6d2ef8198443  (new, from re-run)
Tasks user_id:    0de397fe-f8d9-49f2-b389-6e3e92c70c00  (old, orphaned)
```

### Fix 5 — Migrate orphaned rows to current user

```python
# Reassigned all rows with the old user_id to the current devuser id:
tables = ['tasks', 'manual_reports', 'action_logs', 'session_logs',
          'ai_usage_logs', 'synthesis_reports', 'system_states']
# tasks: 4 rows, manual_reports: 1 row, action_logs: 37 rows, system_states: 1 row
# All migrated from 0de397fe-... → 0a784806-...
```

### Fix 6 — Make `create_dev_user.py` idempotent (upsert, not delete+recreate)

**Before:** deleted existing devuser then inserted a new one — always a new UUID.

**After:** if devuser exists, only resets their password; the `id` (UUID) is preserved. A new user is only created when none exists.

```python
if existing:
    existing.hashed_password = get_password_hash("devpass")
    await session.commit()
    print(f"devuser already exists (id={existing.id}) — password reset. ID preserved.")
else:
    user = User(...)
```

This guarantees re-running the seeding script never orphans existing data.

### New Hard-Won Lesson Added

> **`create_dev_user.py` (and any seeding script) must never delete and recreate rows with auto-generated PKs.** A delete + insert generates a new UUID; all data previously associated with the old UUID becomes orphaned and invisible to the API (which scopes all queries by `user_id`). Always use an upsert/update pattern to preserve the primary key when re-seeding.

---

## Recommended Follow-Up

- Add `make deps` as a prerequisite in `make start` (or document that `make deps` must be run first in the README).
- Consider adding a `requirements.txt` hash check to detect stale `.venv` installations automatically.
- The `dev` target (`make dev`) is also affected if the `.venv` is incomplete — document the `make deps` step prominently in onboarding docs.

## Documentation & Policy Updates

To prevent this class of issue from recurring, the following documentation was updated with explicit, enforceable rules:

- **`copilot-instructions.md`** — Added hard rules about `user_id` sanctity, idempotent seeding scripts (no delete+recreate), migration discipline, and token claim changes.
- **`architecture.md`** — Added detailed sections on data integrity, migration policy (Alembic required), seeding script safety contracts, and multi-user readiness checklist.
- **`agents.md`** — Added a strict “inference isolation” section requiring all prompt/context assembly to be scoped to the authenticated user and audited for cross-user leakage.

These updates ensure that future changes (including launching the app publicly) do not reintroduce orphaning, data loss, or privacy exposure risks.
