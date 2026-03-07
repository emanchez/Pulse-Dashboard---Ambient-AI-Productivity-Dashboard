# Phase 3 Bugfix Summary

**Date:** 2026-03-06

---

## Issue 1 — Report modal could not select tasks; CORS 500 on report/task endpoints

### Root cause
Three layered problems:
1. `config.py` had `env_file = None` — `.env` was never loaded, so `FRONTEND_CORS_ORIGINS` defaulted to four hardcoded dev origins. If a developer had ever run `source .env` or `export FRONTEND_CORS_ORIGINS=http://localhost:3000`, the shell env var overrode the default with a single origin, causing CORS rejections from `http://127.0.0.1:3000`.
2. `report_service.py` had no `try/except` around DB calls — any SQLAlchemy error produced an unhandled 500, whose response was sent without a CORS header (CORSMiddleware had already decided the origin was not in the list).
3. `reports/page.tsx` used `Promise.all` with a single catch block — if `/tasks/` failed for any reason, the whole batch rejected, `handleAuthError` swallowed the non-401 error silently, and `tasks` stayed `[]`. The form opened showing "No tasks available" with no user feedback.

### Fixes applied
- `config.py`: switched to `SettingsConfigDict` with absolute path env file; changed `frontend_cors_origins` field type to `str` with `get_cors_origins()` splitter to bypass pydantic-settings JSON pre-parsing on list fields.
- `.env`: updated `FRONTEND_CORS_ORIGINS` to all four localhost/127.0.0.1 origins as a comma-separated string.
- `report_service.py`: added `_validate_task_ids` helper and wrapped all `db.commit/refresh/delete` calls in `try/except SQLAlchemyError` with rollback and re-raise as `HTTPException(500)`.
- `reports/page.tsx`: replaced `Promise.all` with `Promise.allSettled`; added `fetchError` state and inline red banner; improved auth-error handling to allow non-fatal task fetch failure without clearing the reports view.
- `ReportForm.tsx`: filtered `task.id != null` before rendering checkboxes to guard against `string | null | undefined` type unsafety.
- Added `test_create_report_db_commit_error` — unit test asserting structured 500 response shape.

### Verification
- `pytest -q` — 76 passed.
- `npm run build` — 0 TypeScript errors, 7/7 pages compiled.

---

## Issue 2 — All endpoints blocked with CORS error, status code (null)

### Root cause
Status code `(null)` in browser CORS errors means **no response was received at all** — the backend process was not running. After CORS fix #1 enabled `.env` loading, the backend crashed at startup with `sqlite3.OperationalError: unable to open database file`.

The cause: `.env` contained `DATABASE_URL=sqlite+aiosqlite:///./code/backend/data/dev.db`. This path was written to be used from the project root (`/project/`). Previously this was harmless because `env_file = None` meant `.env` was never read — the backend fell back to the pydantic default `sqlite+aiosqlite:///./data/dev.db`, which resolves correctly when uvicorn runs from `code/backend/`.

Once `env_file` was enabled, that wrong path was loaded. Relative to uvicorn's cwd (`code/backend/`), `./code/backend/data/dev.db` resolved to the non-existent path `code/backend/code/backend/data/dev.db`. The server crashed during lifespan startup, `nohup` swallowed the error (start target uses `>/dev/null 2>&1`), and every frontend request hit "connection refused" — reported by the browser as a CORS error with null status code.

### Fix applied
Updated `code/backend/.env`:
```
# Before
DATABASE_URL=sqlite+aiosqlite:///./code/backend/data/dev.db

# After
DATABASE_URL=sqlite+aiosqlite:///./data/dev.db
```

### Verification
- Backend starts cleanly; `curl http://localhost:8000/health` → `{"status":"ok"}`.
- `access-control-allow-origin: http://localhost:3000` and `http://127.0.0.1:3000` confirmed via curl.
- `pytest -q` — 76 passed, 0 failures.

---

## Issue 3 — `GET /reports` returns HTTP 500 with missing CORS header

### Root cause
The `manual_reports` table in `data/dev.db` was missing three columns that were added to the SQLAlchemy model after the table was first created:

| Column    | DB | Model |
|-----------|-----|-------|
| `status`  | ✗   | ✓     |
| `tags`    | ✗   | ✓     |
| `user_id` | ✗   | ✓     |

When SQLAlchemy executed `SELECT * FROM manual_reports WHERE user_id = ...`, the `user_id` column reference in the WHERE clause caused an `OperationalError: table manual_reports has no column named user_id`. This exception was unhandled — `list_reports` in `report_service.py` has no `try/except` wrapper — so it propagated as a raw 500 text response past CORSMiddleware, which never attached the `Access-Control-Allow-Origin` header.

This occurred because the project uses `create_all` on startup (not Alembic migrations), and the live dev database predated the model additions. `create_all` does not modify existing tables.

### Fix applied
Added the missing columns via `ALTER TABLE`:

```sql
ALTER TABLE manual_reports ADD COLUMN status TEXT NOT NULL DEFAULT 'published';
ALTER TABLE manual_reports ADD COLUMN tags TEXT;
ALTER TABLE manual_reports ADD COLUMN user_id TEXT;
```

### Verification
- `curl -si -H "Authorization: Bearer $TOKEN" -H "Origin: http://localhost:3000" "http://localhost:8000/reports?offset=0&limit=20"` → `HTTP/1.1 200 OK` with `access-control-allow-origin: http://localhost:3000`.
- `pytest -q` — 76 passed.

---

## How to avoid in the future

1. **Never use project-root-relative paths in `.env` files that live in a subdirectory.** All paths in `code/backend/.env` must be relative to `code/backend/` (the uvicorn cwd). Alternatively, use absolute paths derived from a known anchor (e.g. `Path(__file__)`).

2. **The `start` Makefile target redirects stderr to `/dev/null`.** Any crash at startup is silently discarded, making the "CORS error / null status code" pattern the only symptom. Add a brief startup-smoke check (e.g. a `curl /health` with a retry loop) after `nohup` in the `start` target to surface silent failures immediately. Optionally redirect stderr to a log file (`>>/tmp/backend.log 2>&1`) during development.

3. **When enabling a previously disabled config mechanism, audit all values it will now load.** Switching from `env_file = None` to `env_file = ".env"` is a behaviour change that activates every key in the file — review each value for path correctness and side effects before deploying.

4. **Test the server startup explicitly in CI.** A smoke test that starts the server and hits `/health` would have caught this immediately and independently of the browser CORS error.

5. **`create_all` does not alter existing tables.** Whenever a SQLAlchemy model gains a new column, write and run an explicit `ALTER TABLE ... ADD COLUMN` script (or use Alembic) against the live DB. Confirm the live schema matches the model with `PRAGMA table_info(<table>)` before restarting the server. Missing columns cause an unhandled `OperationalError` that strips the CORS header from the 500 response, making the root cause invisible in the browser.

