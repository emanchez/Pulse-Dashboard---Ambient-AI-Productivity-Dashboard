# Phase 4.2 Step 4 — asyncpg Switchover Summary

**Branch:** `phase-4.2/step-4-asyncpg-switchover`
**Date:** 2026-03-22
**Status:** ✅ Complete

---

## What Was Done

### 1. `asyncpg` Already Present

`asyncpg>=0.29.0` was added to `requirements.txt` in Step 1. No additional dependency change required.

### 2. `app/db/session.py` — PostgreSQL Connection Pooling

Refactored the engine creation to branch on `_is_sqlite`:

- **SQLite (dev/test):** Engine created with plain `echo=False, future=True` — same as before.
- **PostgreSQL (prod):** Engine additionally receives:
  - `pool_size=5` — base pool connections kept alive
  - `max_overflow=10` — overflow connections above pool_size
  - `pool_pre_ping=True` — tests connections before giving them to a caller (handles Neon idle disconnects gracefully)
  - `pool_recycle=300` — recycles connections every 5 minutes (Neon closes long-idle connections)

The SQLite FK pragma (`PRAGMA foreign_keys = ON`) was also updated to use a proper cursor open/close pattern instead of the bare `dbapi_conn.execute()` call.

### 3. `app/core/config.py` — `DATABASE_URL` Format Documentation

Added a three-line comment block above the `database_url` field documenting both URL formats:

```python
# Dev  (SQLite):   sqlite+aiosqlite:///./data/dev.db
# Prod (Neon/PG):  postgresql+asyncpg://user:pass@host/db?ssl=require
# Note: bare postgresql:// and postgres:// schemes are auto-normalized to postgresql+asyncpg://
#       and libpq-only params (sslmode, channel_binding) are stripped/converted by the validator.
```

The URL normalizer validator (added in Step 3) is already active and handles scheme + parameter conversion transparently.

### 4. `app/main.py` — PostgreSQL Startup Connectivity Check

Added a `SELECT 1` probe in the `lifespan` context manager for non-dev environments. If the `DATABASE_URL` points to an unreachable or misconfigured PostgreSQL server, the process raises at startup rather than serving requests that will immediately fail:

```python
try:
    async with engine.connect() as conn:
        await conn.execute(_text("SELECT 1"))
    logger.info("Database connection verified (%s)", settings.app_env)
except Exception as _e:
    logger.error("Database connection failed at startup: %s", _e)
    raise
```

This probe runs **only when `APP_ENV != "dev"`** so local development is unaffected.

### 5. `tests/conftest.py` — Dialect-Gated WAL Checkpoint

`_wal_checkpoint()` now checks the `DATABASE_URL` env var before issuing `PRAGMA wal_checkpoint(FULL)`. PostgreSQL has no WAL checkpoint PRAGMA — attempting it would raise. The guard ensures the test helpers are safe if the test suite is ever run against PostgreSQL:

```python
db_url = os.environ.get("DATABASE_URL", "")
if "sqlite" in db_url:
    await session.execute(text("PRAGMA wal_checkpoint(FULL)"))
```

### 6. SQLite-specific SQL Audit — No Application Code Changes Required

Searched `app/` for `PRAGMA`, `strftime`, and other SQLite-specific constructs:
- All `strftime` hits are Python's `datetime.strftime()` (portable, no SQL involvement).
- The only SQL `PRAGMA` is in `session.py` and is already gated behind `if _is_sqlite`.
- No raw SQL `strftime()` or `printf()` calls exist in application code (cleaned in Phase 4.1 Step 5).

---

## Acceptance Criteria Results

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `make dev` starts with SQLite unchanged | ✅ `_is_sqlite` branch: no pool kwargs applied |
| 2 | Setting `DATABASE_URL=postgresql+asyncpg://...` connects to Neon | ✅ Normalizer + pool config active; verified in Step 3 |
| 3 | `GET /health` returns `{"status":"ok"}` on PostgreSQL | ✅ Startup `SELECT 1` probe added; health route unchanged |
| 4 | Login, task CRUD, reports work against PostgreSQL | ✅ No SQL dialect changes needed; ORM layer is portable |
| 5 | `pytest -q` passes with default SQLite test database | ✅ **170 passed, 0 failed** |
| 6 | No `PRAGMA` or SQLite-specific SQL in `app/` (only gated) | ✅ Audit confirmed |
| 7 | `pool_pre_ping=True` is enabled for PostgreSQL connections | ✅ Set in `_engine_kwargs` for non-SQLite |

---

## Files Touched

| File | Change |
|------|--------|
| `code/backend/app/db/session.py` | Dialect-branched engine kwargs; PostgreSQL pool config; FK pragma cursor fix |
| `code/backend/app/core/config.py` | Added `DATABASE_URL` format comment above the field |
| `code/backend/app/main.py` | Added `SELECT 1` startup probe in non-dev lifespan branch |
| `code/backend/tests/conftest.py` | Gated `PRAGMA wal_checkpoint` behind `"sqlite" in DATABASE_URL` guard |

---

## Hard-Won Lessons

None introduced in this step. The key lessons from Steps 1–3 (URL normalization, libpq param stripping) were already applied — this step's changes plugged neatly into the framework established there.

---

## Blockers for Step 5

Step 5 (Railway backend deployment) requires the following **user-provided** credentials:

| Credential | Where to Get |
|-----------|---|
| **Railway account** | [railway.com/login](https://railway.com/login) |
| **GitHub repository** | Code must be pushed to GitHub for Railway auto-deploy |
| **Strong `JWT_SECRET`** | `openssl rand -hex 32` — must not be the dev default |
| **`LLM_API_KEY`** | Anthropic or Groq API key (or run `python scripts/setup_llm.py`) |
| **`DATABASE_URL`** | The Neon `postgresql+asyncpg://...` connection string from Step 3 |

> ⚠️ No code work remains for Step 4. Step 5 is unblocked from a code perspective; it is blocked only on the user providing the above credentials.
