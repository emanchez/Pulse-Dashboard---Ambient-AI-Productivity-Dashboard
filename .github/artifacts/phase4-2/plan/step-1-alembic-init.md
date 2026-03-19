# Step 1 — Initialize Alembic Migration Framework

## Purpose

Set up Alembic as the project's schema migration tool and create a baseline migration that captures the current SQLAlchemy model state, replacing the ad-hoc `scripts/migrate_*.py` approach. This is a prerequisite for all subsequent schema changes (FK constraints, NOT NULL enforcement) and for the SQLite → PostgreSQL migration.

## Deliverables

- `alembic` added to `requirements.txt`
- `alembic.ini` configuration file at `code/backend/alembic.ini`
- `code/backend/alembic/` directory with `env.py` configured for async SQLAlchemy
- Baseline migration file representing the full current schema (all 8 tables)
- Updated `code/backend/app/main.py` — remove or gate `create_all()` behind `APP_ENV=dev`

## Primary files to change

- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/alembic.ini](code/backend/alembic.ini) (new)
- [code/backend/alembic/env.py](code/backend/alembic/env.py) (new)
- [code/backend/alembic/versions/0001_baseline.py](code/backend/alembic/versions/0001_baseline.py) (new, auto-generated)
- [code/backend/app/main.py](code/backend/app/main.py)

## Detailed implementation steps

1. **Add `alembic` to `requirements.txt`:**
   ```
   alembic>=1.12.0
   asyncpg>=0.29.0  # needed later in Step 4, but add now for env.py compatibility
   ```

2. **Initialize Alembic:**
   ```bash
   cd code/backend
   alembic init alembic
   ```

3. **Configure `alembic.ini`:**
   - Set `sqlalchemy.url` to empty string (will be overridden by `env.py` at runtime)
   - Set `script_location = alembic`

4. **Configure `alembic/env.py` for async SQLAlchemy:**
   - Import `Base` from `app.db.base`
   - Import `get_settings` from `app.core.config`
   - Set `target_metadata = Base.metadata`
   - Override `sqlalchemy.url` from `get_settings().database_url`
   - Use `run_async_migrations()` with `create_async_engine` for the `run_migrations_online()` function
   - Ensure all model modules are imported (so their tables register with `Base.metadata`):
     ```python
     import app.models.user
     import app.models.task
     import app.models.action_log
     import app.models.session_log
     import app.models.manual_report
     import app.models.system_state
     import app.models.ai_usage
     import app.models.synthesis
     ```

5. **Generate baseline migration:**
   ```bash
   alembic revision --autogenerate -m "baseline: all 8 tables"
   ```
   - Review the generated file carefully: it should create all 8 tables (`users`, `tasks`, `action_logs`, `session_logs`, `manual_reports`, `system_states`, `ai_usage_logs`, `synthesis_reports`) with their current column definitions and indexes.
   - **Do NOT run `alembic upgrade head` against the live `dev.db` yet** — the tables already exist. Stamp the current state instead:
     ```bash
     alembic stamp head
     ```

6. **Gate `create_all()` in `main.py`:**
   - Change the lifespan `create_all()` to only run when `APP_ENV == "dev"`:
     ```python
     if settings.app_env == "dev":
         async with engine.begin() as conn:
             await conn.run_sync(Base.metadata.create_all)
         logger.info("DB tables verified/created via create_all (dev mode)")
     else:
         logger.info("Skipping create_all in %s mode — use Alembic migrations", settings.app_env)
     ```

7. **Add `alembic/versions/` to `.gitignore` exclusion** (alembic versions should be committed — ensure they're NOT gitignored).

## Integration & Edge Cases

- The baseline migration must exactly match the current `dev.db` schema. After `alembic stamp head`, running `alembic check` should report no differences.
- The existing `scripts/migrate_*.py` files should be preserved as-is (they're idempotent and serve as documentation of past migrations). Add a comment at the top noting they are superseded by Alembic.
- `aiosqlite` must remain as a dependency for dev mode. `asyncpg` is added now but only used starting in Step 4.

## Acceptance Criteria

1. `alembic current` outputs the baseline revision hash when run from `code/backend/`.
2. `alembic check` reports "No new upgrade operations detected" (models match the migration).
3. `alembic upgrade head` on a **fresh empty database** creates all 8 tables with correct columns.
4. `create_all()` is skipped when `APP_ENV != "dev"`.
5. `pytest -q` passes (no test regressions).

## Testing / QA

### Automated
```bash
cd code/backend
# Stamp current dev.db
alembic stamp head
# Verify no drift
alembic check
# Run full test suite
python -m pytest -q --tb=short
```

### Manual
1. Delete a local test copy of the database, run `alembic upgrade head`, verify all tables exist via `sqlite3 data/test-alembic.db ".tables"`.
2. Run `make dev` and verify the app starts normally with the gated `create_all()`.

## Files touched

- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/alembic.ini](code/backend/alembic.ini)
- [code/backend/alembic/env.py](code/backend/alembic/env.py)
- [code/backend/alembic/script.mako](code/backend/alembic/script.mako)
- [code/backend/alembic/versions/0001_baseline.py](code/backend/alembic/versions/0001_baseline.py)
- [code/backend/app/main.py](code/backend/app/main.py)

## Estimated effort

1 dev day

## Concurrency & PR strategy

- Branch: `phase-4.2/step-1-alembic-init`
- Blocking steps: None — this is the first step.
- Merge Readiness: false (set to true after implementation and verification)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Autogenerate produces incorrect migration (e.g. missing indexes) | Manually review the generated file diff; compare against the model research in step9 summary |
| `alembic stamp head` accidentally runs `upgrade` | Double-check command; `stamp` only writes to `alembic_version` table, never modifies schema |
| Breaking existing `make dev` workflow | `create_all()` is only gated, not removed; dev mode retains current behavior |

## References

- [architecture.md §5](../../architecture.md) — Migration Discipline
- [MVP_FINAL_AUDIT.md §6](../../MVP_FINAL_AUDIT.md) — Database/Schema Notes
- [step9-test-harness-summary.md](../summary/step9-test-harness-summary.md) — Schema model details

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
