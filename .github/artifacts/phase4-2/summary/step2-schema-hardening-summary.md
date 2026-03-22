# Phase 4.2 Step 2 — Schema Hardening Summary

**Branch:** `phase-4.2/step-2-schema-hardening`
**Date:** 2026-03-22
**Status:** ✅ Complete

---

## What Was Done

### 1. Database Backup
```bash
cp data/dev.db data/dev.db.pre-schema-hardening.bak
```

### 2. Backfill Script (`scripts/backfill_nulls.py`)
Created idempotent script that resolves data issues before the NOT NULL migration:
- Resolved **5 NULL `user_id` rows** in `action_logs` (assigned to the single dev user)
- Cleared **21 orphaned `task_id` references** in `action_logs` (set to NULL — tasks no longer exist)
- `system_states.user_id` and `system_states.start_date`: no NULLs found

### 3. SQLAlchemy Model Updates
Added `ForeignKey` constraints and corrected nullability across all 7 user-owned tables:

| Model | Change |
|-------|--------|
| `task.py` | `user_id` → `ForeignKey("users.id")` |
| `action_log.py` | `user_id` → `ForeignKey("users.id")`, nullable=True (see design note); `task_id` → `ForeignKey("tasks.id")`; removed redundant single-column `ix_action_logs_user_id` |
| `session_log.py` | `user_id` → `ForeignKey("users.id")`; `task_id` → `ForeignKey("tasks.id")`; removed redundant `ix_session_logs_user_id` |
| `manual_report.py` | `user_id` → `ForeignKey("users.id")` |
| `system_state.py` | `user_id` → `ForeignKey("users.id")`, nullable=False; `start_date` → nullable=False |
| `synthesis.py` | `user_id` → `ForeignKey("users.id")` |
| `ai_usage.py` | Removed redundant `index=True` on `user_id` and `endpoint`; added composite `__table_args__` with `Index("ix_ai_usage_user_endpoint_ts", "user_id", "endpoint", "timestamp")` |

### 4. `app/db/session.py` — SQLite FK Enforcement
Added `PRAGMA foreign_keys = ON` connect event listener for SQLite engines:
```python
if "sqlite" in settings.database_url:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_fk_pragma(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys = ON")
```

### 5. `alembic/env.py` — Batch Mode
Added `render_as_batch=True` to `do_run_migrations()` to support `ALTER TABLE` constraint changes on SQLite.

### 6. Alembic Migration `5f3c8b1d2e7a_schema_hardening.py`
Hand-written migration targeting revision `2a912a3d181d` (baseline). Uses `op.batch_alter_table` throughout. Covers:
- FK `fk_tasks_user_id` on `tasks.user_id → users.id`
- FK `fk_action_logs_user_id` on `action_logs.user_id → users.id`
- FK `fk_action_logs_task_id` on `action_logs.task_id → tasks.id`
- FK `fk_session_logs_user_id` on `session_logs.user_id → users.id`
- FK `fk_session_logs_task_id` on `session_logs.task_id → tasks.id`
- FK `fk_manual_reports_user_id` on `manual_reports.user_id → users.id`
- FK `fk_system_states_user_id` on `system_states.user_id → users.id`
- NOT NULL on `system_states.user_id`
- NOT NULL on `system_states.start_date`
- FK `fk_synthesis_reports_user_id` on `synthesis_reports.user_id → users.id`
- Drop `ix_ai_usage_logs_user_id`, `ix_ai_usage_logs_endpoint`; add `ix_ai_usage_user_endpoint_ts` (composite)
- Drop `ix_action_logs_user_id`, `ix_session_logs_user_id` (covered by existing composite indexes)
- Full `downgrade()` path that reverses every operation

### 7. Middleware Bug Fix — `_extract_entity_id` (latent, exposed by FK enforcement)
`PRAGMA foreign_keys = ON` exposed a pre-existing bug in `ActionLogMiddleware`: `_extract_entity_id(["ai", "accept-tasks"])` was returning `"accept-tasks"` (a non-UUID string) as the `task_id`, which now fails the FK constraint when inserted into `action_logs`. Fixed by validating the candidate string is a valid UUID before returning it.

---

## Design Decision: `action_logs.user_id` Remains Nullable

The step plan called for NOT NULL on `action_logs.user_id`. This was amended to keep it **nullable** for the following reason:

The `action_logs` table stores both authenticated events (task saves, report creates) and unauthenticated audit events (`LOGIN_FAILED`). Failed login attempts have no authenticated user — `user_id` is legitimately NULL for these rows. Making `user_id` NOT NULL would silently break login failure audit logging.

**Rule applied:** `system_states.user_id` is NOT NULL (always created by an authenticated user). `action_logs.user_id` stays nullable (logs both auth and unauth events).

---

## Acceptance Criteria Results

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `backfill_nulls.py` runs idempotently, zero NULL `user_id` rows | ✅ 5 rows fixed, 0 remaining |
| 2 | `alembic upgrade head` succeeds on `dev.db` without errors | ✅ |
| 3 | `system_states.user_id` and `start_date` are NOT NULL | ✅ `notnull=1` confirmed |
| 4 | FK constraints declared in all user-owned models | ✅ |
| 5 | `ix_ai_usage_user_endpoint_ts` exists on `ai_usage_logs` | ✅ |
| 6 | `system_states.start_date` is NOT NULL | ✅ |
| 7 | `pytest -q` passes with no regressions | ✅ 170 passed, 0 failed |
| 8 | `alembic downgrade -1` successfully reverses migration | ✅ Tested round-trip |

---

## Additional Fixes Delivered

| Fix | Description |
|-----|-------------|
| `ActionLogMiddleware._extract_entity_id` | New validator rejects non-UUID path segments as entity IDs. Prevents FK violations for routes like `/ai/accept-tasks`. |
| `SessionLog` model import | Added `ForeignKey` to `session_log.py` imports. |

---

## Files Touched

| File | Change |
|------|--------|
| `code/backend/app/models/task.py` | ForeignKey on `user_id` |
| `code/backend/app/models/action_log.py` | ForeignKey on `user_id` + `task_id`; nullable=True preserved; drop redundant index |
| `code/backend/app/models/session_log.py` | ForeignKey on `user_id` + `task_id`; drop redundant index |
| `code/backend/app/models/manual_report.py` | ForeignKey on `user_id` |
| `code/backend/app/models/system_state.py` | ForeignKey on `user_id`; nullable=False on `user_id` + `start_date` |
| `code/backend/app/models/synthesis.py` | ForeignKey on `user_id` |
| `code/backend/app/models/ai_usage.py` | Composite index via `__table_args__`; removed single-column indexes |
| `code/backend/app/db/session.py` | PRAGMA foreign_keys = ON for SQLite |
| `code/backend/app/middlewares/action_log.py` | UUID-validated `_extract_entity_id`; added `uuid`, `re` imports |
| `code/backend/alembic/env.py` | `render_as_batch=True` in `do_run_migrations` |
| `code/backend/alembic/versions/5f3c8b1d2e7a_schema_hardening.py` | New migration |
| `code/backend/scripts/backfill_nulls.py` | New backfill script |
| `code/backend/data/dev.db.pre-schema-hardening.bak` | Backup created |

---

## Blockers for Step 3

Step 3 (Neon Provision & Migrate) is **BLOCKED on user action**:

> **🔴 USER ACTION REQUIRED**
>
> Before Step 3 can begin, you must:
> 1. Create a free Neon account at [console.neon.tech](https://console.neon.tech)
> 2. Create a new project (e.g. `pulse-dashboard`)
> 3. Copy the connection string (format: `postgresql+asyncpg://user:password@host/dbname`)
> 4. Make it available as the `DATABASE_URL` environment variable for the backend

No code blockers remain. When the Neon `DATABASE_URL` is ready, Step 3 (data migration from `dev.db` to Neon) can proceed immediately.
