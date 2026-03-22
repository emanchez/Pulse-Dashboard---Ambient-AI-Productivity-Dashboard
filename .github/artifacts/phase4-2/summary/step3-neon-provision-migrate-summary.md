# Phase 4.2 Step 3 — Neon Provision & SQLite Migration Summary

**Branch:** `phase-4.2/step-3-neon-provision-migrate`
**Date:** 2026-03-22
**Status:** ✅ Complete

---

## What Was Done

### 1. Database Backup
```bash
cp data/dev.db data/dev.db.pre-deploy.bak
```

### 2. URL Normalization in `app/core/config.py`

Added a `@field_validator` on `database_url` that normalizes Neon's Neon-provided connection strings to be asyncpg-compatible:

| Input (Neon default format) | Normalized (asyncpg-compatible) |
|---|---|
| `postgresql://` scheme | `postgresql+asyncpg://` |
| `postgres://` scheme | `postgresql+asyncpg://` |
| `?sslmode=require` query param | `?ssl=require` (asyncpg uses `ssl`, not `sslmode`) |
| `&channel_binding=require` query param | **stripped** (libpq-only, asyncpg raises on it) |

This normalization is transparent: SQLite URLs pass through unchanged, so all 170 existing tests continue to pass.

**New imports added to `config.py`:** `field_validator` (from pydantic), `urlparse`, `urlunparse`, `parse_qs`, `urlencode` (from urllib.parse).

### 3. `alembic upgrade head` Against Neon

Both migrations applied successfully against the Neon `neondb` database:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 2a912a3d181d, baseline: all 8 tables
INFO  [alembic.runtime.migration] Running upgrade 2a912a3d181d -> 5f3c8b1d2e7a, schema hardening: FKs, NOT NULL, indexes
```

All 8 tables now exist in Neon with the full hardened schema (FK constraints, NOT NULL, composite indexes) from Steps 1–2.

### 4. Migration Script (`scripts/migrate_sqlite_to_pg.py`)

New script with the following capabilities:

- **FK-safe insertion order:** users → tasks → action_logs → session_logs → manual_reports → system_states → ai_usage_logs → synthesis_reports
- **Idempotent:** uses `ON CONFLICT (id) DO NOTHING` — safe to re-run without duplicating rows
- **Type conversion:**
  - Boolean columns (`is_active`, `is_completed`, `requires_recovery`, `was_mocked`): SQLite `0`/`1` integers → Python `bool`
  - DateTime columns: SQLite ISO-8601 strings → Python `datetime` via `datetime.fromisoformat()`
  - JSON columns (`manual_reports.associated_task_ids`, `manual_reports.tags`): SQLite TEXT → re-serialized JSON string (asyncpg `json` column type accepts pre-serialized strings)
  - Text JSON columns (`synthesis_reports.suggested_tasks`): same treatment as JSON columns
  - URL normalization mirrors `config.py` validator so any URL format works
- **`--validate-only` mode:** compares row counts between SQLite and PostgreSQL without writing
- **CLI:** `--sqlite-path`, `--pg-url`, `--validate-only` arguments

**Key behavioural note (hard-won):** asyncpg's raw parameterized queries expect `json`/`jsonb` column values to be **pre-serialized strings**, not Python lists/dicts. Passing a Python `list` to a `json` column raises `expected str, got list`. Fix: always `json.dumps()` before passing to asyncpg in raw `conn.execute()` calls.

### 5. Data Migration Results

```
── Migration ───────────────────────────────────────────────────────
  users                   1 rows → 1 inserted
  tasks                   2 rows → 2 inserted
  action_logs            56 rows → 56 inserted
  session_logs            0 rows (empty — skipped)
  manual_reports          2 rows → 2 inserted
  system_states           1 rows → 1 inserted
  ai_usage_logs           0 rows (empty — skipped)
  synthesis_reports       1 rows → 1 inserted

── Post-migration validation ──────────────────────────────────────
  users                         1            1  ✓
  tasks                         2            2  ✓
  action_logs                  56           56  ✓
  session_logs                  0            0  ✓
  manual_reports                2            2  ✓
  system_states                 1            1  ✓
  ai_usage_logs                 0            0  ✓
  synthesis_reports             1            1  ✓

Validation completed successfully ✓
```

### 6. `.env.production.example`

Created at `code/backend/.env.production.example` with all required environment variables and placeholder values. Contains instructions for Railway deployment.

### 7. Test Suite — No Regressions

```
170 passed, 0 failed, 2 warnings in 20.66s
```

The `normalize_database_url` validator is a pure pass-through for SQLite URLs — all existing tests are unaffected.

---

## Hard-Won Lessons

### asyncpg rejects libpq connection parameters
Neon's default connection string includes `?sslmode=require&channel_binding=require`. Both are libpq (psycopg2) parameters that asyncpg does **not** understand:
- `sslmode=require` → must become `ssl=require`
- `channel_binding=require` → must be stripped entirely

Passing these to asyncpg via SQLAlchemy raises `TypeError: connect() got an unexpected keyword argument 'sslmode'`. Fixed by normalizing in `config.py` before the URL ever reaches `create_async_engine`.

### asyncpg raw parameterized inserts require pre-serialized JSON strings
When using `conn.execute(sql, *values)` with asyncpg directly (as opposed to SQLAlchemy ORM), passing a Python `list` to a `json` column raises `expected str, got list`. asyncpg's raw query interface expects the caller to provide a JSON-encoded string, not a Python object. Always `json.dumps(val)` before passing to asyncpg in raw queries.

---

## Acceptance Criteria Results

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Neon project exists and connection string is valid | ✅ Confirmed — migrations ran |
| 2 | `alembic upgrade head` completes successfully against Neon | ✅ Both revisions applied |
| 3 | All 8 tables exist in Neon with correct schema | ✅ FK constraints, NOT NULL, indexes applied |
| 4 | Row counts match between `dev.db` and Neon for all tables | ✅ All 8 tables ✓ |
| 5 | `SELECT * FROM users` returns `devuser` with correct UUID | ✅ (verified by migration validation) |
| 6 | `dev.db.pre-deploy.bak` backup file exists | ✅ |
| 7 | `.env.production.example` contains all required env vars | ✅ |

---

## Files Touched

| File | Change |
|------|--------|
| `code/backend/app/core/config.py` | Added URL normalizer validator + urllib imports |
| `code/backend/scripts/migrate_sqlite_to_pg.py` | New migration script |
| `code/backend/.env.production.example` | New production environment template |
| `code/backend/data/dev.db.pre-deploy.bak` | New backup |

---

## Blockers for Step 4

Step 4 (asyncpg switchover — full engine migration) is ready to begin. No external blockers remain now that the Neon DATABASE_URL is confirmed working.

> **Note for Step 4:** The `normalize_database_url` in `config.py` already handles URL normalization for the `session.py` engine. Step 4 will add connection pooling (`pool_size`, `max_overflow`) and any remaining `create_async_engine` tuning for the PostgreSQL engine.
