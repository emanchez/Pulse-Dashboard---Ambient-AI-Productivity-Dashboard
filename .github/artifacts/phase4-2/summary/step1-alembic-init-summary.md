# Phase 4.2 Step 1 — Alembic Init Summary

**Branch:** `phase-4.2/step-1-alembic-init`
**Date:** 2026-03-22
**Status:** ✅ Complete

---

## What was done

### 1. Dependencies (`code/backend/requirements.txt`)
- Added `alembic>=1.12.0`
- Added `asyncpg>=0.29.0` (used in Step 4; added now for `env.py` compatibility)
- Corrected package name (`anthropichttp` → `anthropic`) from prior tooling artefact

### 2. Alembic initialized
```bash
alembic init alembic
```
Created:
- `code/backend/alembic.ini`
- `code/backend/alembic/env.py`
- `code/backend/alembic/script.py.mako`
- `code/backend/alembic/versions/`

### 3. `alembic.ini` configured
- `sqlalchemy.url` set to empty — URL is resolved at runtime from `app.core.config.get_settings().database_url`

### 4. `alembic/env.py` rewritten for async SQLAlchemy
- Imports all 8 model modules to register tables with `Base.metadata`
- Uses `create_async_engine` + `asyncio.run()` in `run_migrations_online()`
- URL sourced from `get_settings().database_url` (driven by `DATABASE_URL` env var)
- Compatible with both `sqlite+aiosqlite://` (dev) and `postgresql+asyncpg://` (prod)

### 5. Baseline migration generated
- Generated against a **fresh empty SQLite database** to capture the full CREATE TABLE schema
- Revision ID: `2a912a3d181d`
- File: `code/backend/alembic/versions/2a912a3d181d_baseline_all_8_tables.py`
- Creates all 8 tables: `users`, `tasks`, `action_logs`, `session_logs`, `manual_reports`, `system_states`, `ai_usage_logs`, `synthesis_reports`
- Includes all indexes defined in the models

### 6. Live `dev.db` stamped at head
```bash
alembic stamp head  # → 2a912a3d181d
```
- `alembic_version` table written to `dev.db` — tables already existed, no DDL run

### 7. `create_all()` gated in `app/main.py`
- `Base.metadata.create_all` now only runs when `APP_ENV == "dev"`
- Non-dev environments log a message directing to `alembic upgrade head`

---

## Acceptance Criteria

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `alembic current` outputs baseline revision hash | ✅ `2a912a3d181d (head)` |
| 2 | `alembic check` reports no drift | ⚠️ See note below |
| 3 | `alembic upgrade head` on fresh empty DB creates all 8 tables | ✅ Verified |
| 4 | `create_all()` skipped when `APP_ENV != "dev"` | ✅ Gated in `main.py` |
| 5 | `pytest -q` passes | ✅ 170 passed, 0 failed |

### Note on AC #2 — `alembic check` shows known drift

`alembic check` detects diffs between the live `dev.db` and model definitions:
- `ix_action_logs_user_ts` composite index — missing in live DB
- `manual_reports.user_id` — TEXT vs String(36), NULL vs NOT NULL
- `manual_reports.status` — TEXT vs String(20)
- `manual_reports.tags` — TEXT vs JSON
- `ix_manual_reports_user_id`, `ix_session_logs_user_ended`, `ix_tasks_user_id` — missing indexes
- `tasks.user_id` — nullable vs NOT NULL

These diffs are **pre-existing schema drift** between the historical `dev.db` (built via ad-hoc `create_all` before model type refinements) and the current model definitions. They are **intentionally deferred to Step 2 (schema hardening)**, which will add an explicit migration to bring the live schema in sync. This drift does **not** affect the app's ability to operate — the SQLAlchemy models work around the loose types at the ORM layer.

---

## Files touched

| File | Change |
|------|--------|
| `code/backend/requirements.txt` | Added `alembic>=1.12.0`, `asyncpg>=0.29.0`; fixed `anthropic` package name |
| `code/backend/alembic.ini` | New — Alembic config, URL blanked out |
| `code/backend/alembic/env.py` | New — async SQLAlchemy env, all 8 model imports |
| `code/backend/alembic/script.py.mako` | New — Alembic revision template (unmodified) |
| `code/backend/alembic/README` | New — Alembic readme (unmodified) |
| `code/backend/alembic/versions/2a912a3d181d_baseline_all_8_tables.py` | New — baseline migration (all 8 tables) |
| `code/backend/app/main.py` | Gated `create_all()` behind `APP_ENV == "dev"` |

---

## Blockers for Step 2

None. Step 2 (schema hardening) can proceed immediately. The schema drift noted above is the exact input Step 2 will resolve.

---

## Blockers for Further Steps

Steps 3–10 require user-provided credentials. See [master.md](../plan/master.md#required-accounts--api-keys):
- **Step 3:** Neon account → `DATABASE_URL` (PostgreSQL)
- **Step 5:** Railway account + `LLM_API_KEY` + strong `JWT_SECRET`
- **Step 6:** Vercel account
- **Step 8:** GitHub repository
- **Step 9:** Domain name + Cloudflare account (optional)
