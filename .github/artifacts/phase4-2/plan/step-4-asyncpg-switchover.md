# Step 4 — Switch SQLAlchemy Engine from aiosqlite to asyncpg

## Purpose

Reconfigure the backend's database layer to use `asyncpg` (PostgreSQL async driver) instead of `aiosqlite` as the primary production driver. Retain `aiosqlite` as a fallback for local dev/test with SQLite. This enables the app to run against the Neon PostgreSQL database provisioned in Step 3.

## 🔴 ABSOLUTE BLOCKER

> **This step cannot begin until:**
> 1. Step 3 is complete (Neon database provisioned and migrated)
> 2. User has provided the production `DATABASE_URL` in the format:
>    `postgresql+asyncpg://<user>:<pass>@<host>/<db>?sslmode=require`

## Deliverables

- `asyncpg` added to `requirements.txt` (may already be added in Step 1)
- `code/backend/app/db/session.py` updated with connection pool settings for PostgreSQL
- `code/backend/app/core/config.py` documented with production `DATABASE_URL` format
- SQLite-specific `PRAGMA` calls gated behind a `"sqlite" in url` check
- Test suite verified passing against both SQLite (dev) and PostgreSQL (CI/prod)

## Primary files to change

- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/app/db/session.py](code/backend/app/db/session.py)
- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [code/backend/app/main.py](code/backend/app/main.py)
- [code/backend/tests/conftest.py](code/backend/tests/conftest.py)

## Detailed implementation steps

1. **Ensure `asyncpg` is in `requirements.txt`:**
   ```
   asyncpg>=0.29.0
   ```
   (May already exist from Step 1.)

2. **Update `session.py` with connection pool configuration:**
   ```python
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
   from sqlalchemy import event
   from ..core.config import get_settings

   settings = get_settings()

   _is_sqlite = "sqlite" in settings.database_url

   engine_kwargs = {
       "echo": False,
       "future": True,
   }

   if not _is_sqlite:
       # PostgreSQL connection pool settings
       engine_kwargs.update({
           "pool_size": 5,          # Base pool connections
           "max_overflow": 10,      # Extra connections above pool_size
           "pool_pre_ping": True,   # Verify connections before use (handles Neon idle disconnects)
           "pool_recycle": 300,     # Recycle connections every 5 min (Neon may close idle connections)
       })

   engine = create_async_engine(settings.database_url, **engine_kwargs)

   # SQLite: enable foreign key enforcement
   if _is_sqlite:
       @event.listens_for(engine.sync_engine, "connect")
       def _set_sqlite_pragma(dbapi_conn, _):
           cursor = dbapi_conn.cursor()
           cursor.execute("PRAGMA foreign_keys = ON")
           cursor.close()

   async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
   ```

3. **Update `config.py` documentation:**
   - Add a comment above `database_url` explaining the format for PostgreSQL:
     ```python
     # Dev (SQLite):  sqlite+aiosqlite:///./data/dev.db
     # Prod (Neon):   postgresql+asyncpg://user:pass@host/db?sslmode=require
     database_url: str = Field("sqlite+aiosqlite:///./data/dev.db", validation_alias="DATABASE_URL")
     ```

4. **Update `main.py` lifespan:**
   - Ensure `create_all()` is gated as per Step 1.
   - Add PostgreSQL-specific startup checks:
     ```python
     if settings.app_env != "dev":
         # Verify database is reachable
         try:
             async with engine.connect() as conn:
                 await conn.execute(text("SELECT 1"))
             logger.info("Database connection verified")
         except Exception as e:
             logger.error("Database connection failed: %s", e)
             raise
     ```

5. **Update `conftest.py`:**
   - Test suite should continue using SQLite (`sqlite+aiosqlite:///...`) for speed and isolation.
   - Ensure `DATABASE_URL` is overridden in the test environment (already done via fixture).
   - Remove any WAL-specific pragmas that are SQLite-only and gate them:
     ```python
     if "sqlite" in test_db_url:
         await session.execute(text("PRAGMA wal_checkpoint(FULL)"))
     ```

6. **Audit for SQLite-specific SQL:**
   - Step 5 of Phase 4.1 already replaced SQLite-specific `strftime`/`printf` in `flow_state.py`.
   - Search for any remaining `PRAGMA`, `strftime`, or `sqlite`-specific SQL in application code (not test code).
   - Gate or replace any found instances.

7. **Test against both databases:**
   ```bash
   # Test against SQLite (default, fast)
   cd code/backend && python -m pytest -q

   # Test against PostgreSQL (optional, for CI)
   DATABASE_URL="postgresql+asyncpg://..." python -m pytest -q
   ```

## Integration & Edge Cases

- **Neon SSL requirement:** Neon requires `sslmode=require`. The `DATABASE_URL` must include this parameter. `asyncpg` handles SSL natively.
- **Connection idle timeout:** Neon may close connections that are idle for >5 minutes. `pool_pre_ping=True` handles this by testing connections before use.
- **DateTime handling:** PostgreSQL returns `datetime` objects natively (timezone-aware). Ensure the app doesn't break on timezone-aware datetimes. Current models use `datetime.now(timezone.utc).replace(tzinfo=None)` — this should work with both SQLite and PostgreSQL.
- **JSON column type:** SQLAlchemy's `JSON` type works with both SQLite (stored as TEXT) and PostgreSQL (native JSONB). No changes needed.
- **Case sensitivity:** PostgreSQL is case-sensitive for string comparisons by default. SQLite is case-insensitive. Verify any `LIKE` queries are correctly cased. (Ghost list service was already updated in Phase 4.1 to use `==` comparisons.)
- **WAL checkpoints:** The `PRAGMA wal_checkpoint` calls in test fixtures are SQLite-only. Gate them behind a dialect check.

## Acceptance Criteria

1. `make dev` starts successfully with `DATABASE_URL=sqlite+aiosqlite:///./data/dev.db` (unchanged dev behavior).
2. Setting `DATABASE_URL=postgresql+asyncpg://...` and starting the server connects to Neon successfully.
3. `GET /health` returns `{"status":"ok"}` when connected to PostgreSQL.
4. Login, task CRUD, and report operations work against PostgreSQL (manual test via curl or frontend).
5. `pytest -q` passes with the default SQLite test database.
6. No `PRAGMA` or SQLite-specific SQL exists in `app/` code (only in `tests/` behind a dialect check).
7. `pool_pre_ping` is enabled for PostgreSQL connections.

## Testing / QA

### Automated
```bash
cd code/backend

# SQLite (default)
python -m pytest -q --tb=short

# PostgreSQL (if test database is available)
DATABASE_URL="postgresql+asyncpg://..." python -m pytest -q --tb=short
```

### Manual
1. Start the server with `DATABASE_URL` pointing to Neon:
   ```bash
   DATABASE_URL="postgresql+asyncpg://..." .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. `curl http://localhost:8000/health` → `{"status":"ok"}`
3. Login via the frontend and verify tasks load from the migrated data.

## Files touched

- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/app/db/session.py](code/backend/app/db/session.py)
- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [code/backend/app/main.py](code/backend/app/main.py)
- [code/backend/tests/conftest.py](code/backend/tests/conftest.py)

## Estimated effort

0.5–1 dev day

## Concurrency & PR strategy

- Branch: `phase-4.2/step-4-asyncpg-switchover`
- Blocking steps:
  - `Blocked until: .github/artifacts/phase4-2/plan/step-3-neon-provision-migrate.md`
  - **🔴 Blocked until: Neon DATABASE_URL is available**
- Merge Readiness: true

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| `asyncpg` connection errors on Neon | `pool_pre_ping=True` retries dead connections. Add connection verification at startup. |
| Tests break when run against PostgreSQL due to dialect differences | Maintain SQLite as default test database. Add CI matrix for both if needed. |
| DateTime timezone handling differs between SQLite and PostgreSQL | App uses naive datetimes (`replace(tzinfo=None)`). PostgreSQL `TIMESTAMP` without timezone matches. |
| `aiosqlite` still required for dev | Both drivers coexist in `requirements.txt`. Driver selected based on `DATABASE_URL` scheme. |

## References

- [SQLAlchemy asyncpg docs](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.asyncpg)
- [Neon connection pooling](https://neon.tech/docs/connect/connection-pooling)
- [code/backend/app/db/session.py](code/backend/app/db/session.py) — Current session setup
- [step-5-flow-state-portability (Phase 4.1)](../summary/step1-5-summary.md) — SQLite SQL already removed

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
