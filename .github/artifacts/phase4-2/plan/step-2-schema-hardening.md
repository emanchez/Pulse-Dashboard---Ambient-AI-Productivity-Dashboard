# Step 2 — Schema Hardening Migrations

## Purpose

Create Alembic migrations to add missing foreign key constraints, enforce `NOT NULL` on all `user_id` columns, add composite indexes on `ai_usage_logs`, and fix the `system_states.start_date` nullability mismatch. These changes bring the database schema into alignment with the application's invariants and prepare it for PostgreSQL (which enforces constraints more strictly than SQLite).

## Deliverables

- Alembic migration: Add `ForeignKey("users.id")` to all `user_id` columns lacking it (6 tables)
- Alembic migration: Add `ForeignKey("tasks.id")` to `action_logs.task_id` and `session_logs.task_id`
- Alembic migration: Set `NOT NULL` on `action_logs.user_id` and `system_states.user_id`
- Alembic migration: Set `NOT NULL` on `system_states.start_date`
- Alembic migration: Add composite index on `ai_usage_logs(user_id, endpoint, timestamp)`
- Updated SQLAlchemy model files to match the new constraints
- Data fixup script: backfill any NULL `user_id` / `start_date` rows before migration

## Primary files to change

- [code/backend/app/models/task.py](code/backend/app/models/task.py)
- [code/backend/app/models/action_log.py](code/backend/app/models/action_log.py)
- [code/backend/app/models/session_log.py](code/backend/app/models/session_log.py)
- [code/backend/app/models/manual_report.py](code/backend/app/models/manual_report.py)
- [code/backend/app/models/system_state.py](code/backend/app/models/system_state.py)
- [code/backend/app/models/synthesis.py](code/backend/app/models/synthesis.py)
- [code/backend/app/models/ai_usage.py](code/backend/app/models/ai_usage.py)
- [code/backend/alembic/versions/0002_schema_hardening.py](code/backend/alembic/versions/0002_schema_hardening.py) (new, generated+edited)
- [code/backend/scripts/backfill_nulls.py](code/backend/scripts/backfill_nulls.py) (new)

## Detailed implementation steps

1. **Create data backfill script** (`scripts/backfill_nulls.py`):
   - Connect to `dev.db` with raw sqlite3 or async SQLAlchemy.
   - Find the first user's `id` from the `users` table.
   - Update `action_logs SET user_id = <user_id> WHERE user_id IS NULL`.
   - Update `system_states SET user_id = <user_id> WHERE user_id IS NULL`.
   - Update `system_states SET start_date = created_at WHERE start_date IS NULL`.
   - Print counts of updated rows. Script must be **idempotent**.
   - **BEFORE RUNNING:** Back up `dev.db`:
     ```bash
     cp data/dev.db data/dev.db.pre-schema-hardening.bak
     ```

2. **Run the backfill script** against `dev.db`.

3. **Update SQLAlchemy models** to declare the intended constraints:
   - Add `ForeignKey("users.id")` to `user_id` on: `tasks`, `action_logs`, `session_logs`, `manual_reports`, `system_states`, `synthesis_reports`
   - Add `ForeignKey("tasks.id")` to: `action_logs.task_id`, `session_logs.task_id`
   - Change `nullable=True` → `nullable=False` on: `action_logs.user_id`, `system_states.user_id`, `system_states.start_date`
   - Add `__table_args__` composite index on `ai_usage_logs`: `Index("ix_ai_usage_user_endpoint_ts", "user_id", "endpoint", "timestamp")`
   - Remove redundant single-column `index=True` on `action_logs.user_id` and `session_logs.user_id` (covered by composite indexes)

4. **Generate Alembic migration:**
   ```bash
   alembic revision --autogenerate -m "schema hardening: FKs, NOT NULL, indexes"
   ```

5. **Review and edit the generated migration:**
   - Ensure `op.create_foreign_key(...)` calls are correct for each table.
   - Ensure `op.alter_column(..., nullable=False)` is paired with `existing_type` and `existing_nullable=True`.
   - Ensure `op.create_index(...)` for the new composite index on `ai_usage_logs`.
   - Ensure the `downgrade()` function reverses all changes.
   - **Important:** SQLite does not support `ALTER TABLE ... ADD CONSTRAINT`. The migration will work on PostgreSQL directly. For SQLite, Alembic's batch mode (`op.batch_alter_table`) is needed. Configure `env.py` to use `render_as_batch=True` for SQLite connections.

6. **Run migration against dev.db:**
   ```bash
   alembic upgrade head
   ```

7. **Verify schema:**
   ```bash
   sqlite3 data/dev.db "PRAGMA table_info(action_logs);"
   sqlite3 data/dev.db "PRAGMA foreign_key_list(tasks);"
   ```

## Integration & Edge Cases

- **SQLite FK enforcement:** SQLite does not enforce FKs by default. Add `PRAGMA foreign_keys = ON` to the engine connect event in `session.py`:
  ```python
  from sqlalchemy import event
  if "sqlite" in settings.database_url:
      @event.listens_for(engine.sync_engine, "connect")
      def _set_sqlite_fk_pragma(dbapi_conn, _):
          dbapi_conn.execute("PRAGMA foreign_keys = ON")
  ```
- **Alembic batch mode for SQLite:** `ALTER TABLE` with constraint changes requires batch mode on SQLite. Add to `env.py`:
  ```python
  context.configure(
      ...,
      render_as_batch=True,  # required for SQLite ALTER TABLE
  )
  ```
- **Existing orphaned rows:** The backfill script handles NULL `user_id` rows. If there are orphaned `task_id` references (pointing to deleted tasks), set them to `NULL` before adding the FK.

## Acceptance Criteria

1. `scripts/backfill_nulls.py` runs idempotently and reports zero NULL `user_id` rows after completion.
2. `alembic upgrade head` succeeds on `dev.db` without errors.
3. All `user_id` columns are `NOT NULL` (verify with `PRAGMA table_info`).
4. Foreign key constraints are declared in the models (verify with `PRAGMA foreign_key_list` on PostgreSQL; SQLite may not show them without `PRAGMA foreign_keys=ON`).
5. New composite index `ix_ai_usage_user_endpoint_ts` exists on `ai_usage_logs`.
6. `system_states.start_date` is `NOT NULL`.
7. `pytest -q` passes with no regressions.
8. `alembic downgrade -1` successfully reverses the migration.

## Testing / QA

### Automated
```bash
cd code/backend
# Backup
cp data/dev.db data/dev.db.pre-schema-hardening.bak

# Backfill
python scripts/backfill_nulls.py

# Migrate
alembic upgrade head

# Verify
python -c "
import sqlite3
conn = sqlite3.connect('data/dev.db')
for table in ['action_logs', 'system_states']:
    nulls = conn.execute(f'SELECT COUNT(*) FROM {table} WHERE user_id IS NULL').fetchone()[0]
    print(f'{table}.user_id NULLs: {nulls}')
    assert nulls == 0, f'{table} still has NULL user_id rows'
print('All checks passed')
"

# Test suite
python -m pytest -q --tb=short
```

### Manual
1. Inspect `dev.db` schema with a DB browser after migration.
2. Attempt to insert a row with NULL `user_id` into `tasks` — should fail.
3. Attempt to insert a row with a non-existent `user_id` into `tasks` — should fail (FK violation) when `PRAGMA foreign_keys=ON`.

## Files touched

- [code/backend/app/models/task.py](code/backend/app/models/task.py)
- [code/backend/app/models/action_log.py](code/backend/app/models/action_log.py)
- [code/backend/app/models/session_log.py](code/backend/app/models/session_log.py)
- [code/backend/app/models/manual_report.py](code/backend/app/models/manual_report.py)
- [code/backend/app/models/system_state.py](code/backend/app/models/system_state.py)
- [code/backend/app/models/synthesis.py](code/backend/app/models/synthesis.py)
- [code/backend/app/models/ai_usage.py](code/backend/app/models/ai_usage.py)
- [code/backend/app/db/session.py](code/backend/app/db/session.py)
- [code/backend/alembic/env.py](code/backend/alembic/env.py)
- [code/backend/alembic/versions/0002_schema_hardening.py](code/backend/alembic/versions/0002_schema_hardening.py)
- [code/backend/scripts/backfill_nulls.py](code/backend/scripts/backfill_nulls.py)

## Estimated effort

1–2 dev days

## Concurrency & PR strategy

- Branch: `phase-4.2/step-2-schema-hardening`
- Blocking steps: `Blocked until: .github/artifacts/phase4-2/plan/step-1-alembic-init.md`
- Merge Readiness: false

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Backfill assigns wrong user_id to orphaned rows | Single-user app — only one user exists. Script validates exactly one user before proceeding. |
| SQLite batch mode migration corrupts data | Test on a copy of `dev.db` first. Keep `.bak` file. |
| FK constraints break test fixtures | Update `conftest.py` fixtures to always set `user_id` on all models. |
| Orphaned `task_id` references block FK creation | Backfill script sets orphaned `task_id` to NULL first. |

## References

- [architecture.md §5.1](../../architecture.md) — Foreign Key Discipline
- [architecture.md §5.2](../../architecture.md) — Migration Discipline
- [MVP_FINAL_AUDIT.md §4](../../MVP_FINAL_AUDIT.md) — Missing FK constraints, nullable user_id
- Schema research from agent analysis (8 tables, nullability matrix)

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
