# Step 9 — Fix Test Harness: Resolve test_stats, test_sessions, test_system_states Failures

## Purpose

Fix the test infrastructure issue causing `test_stats.py` (5 failures), `test_sessions.py`, and `test_system_states.py` to fail. The root cause is a test harness architecture mismatch: the `client` fixture spawns a background uvicorn subprocess, but `create_user` writes directly to the pytest process's DB session. The subprocess has its own DB connection and never sees the user created by the test.

## Deliverables

- Refactored test fixtures so that all tests using the `client` (server subprocess) fixture create users and seed data through HTTP API calls to the running server, not via direct DB writes.
- All previously-failing tests pass: `test_stats.py`, `test_sessions.py`, `test_system_states.py`.
- No regressions in the existing 136 passing tests.
- Clear documentation of the two test patterns (in-process async vs. server subprocess).

## Primary files to change

- [code/backend/tests/conftest.py](code/backend/tests/conftest.py) — Refactor fixtures
- [code/backend/tests/test_stats.py](code/backend/tests/test_stats.py) — Fix test setup
- [code/backend/tests/test_sessions.py](code/backend/tests/test_sessions.py) — Fix test setup
- [code/backend/tests/test_system_states.py](code/backend/tests/test_system_states.py) — Fix test setup

## Detailed implementation steps

### 9.1 Understand the current architecture

The test suite has **two** fixture patterns:

1. **In-process async** (used by `test_ghost_list.py`, `test_ai.py`, etc.): Tests directly call async service functions with a test `AsyncSession`. No server subprocess. These work correctly.

2. **Server subprocess** (used by `test_stats.py`, `test_sessions.py`, `test_system_states.py`): The `server` fixture spawns `uvicorn app.main:app` as a subprocess. The `client` fixture is an `httpx.Client` that talks to this subprocess. The `create_user` fixture writes to the DB via `async_session` (the pytest process's engine). The subprocess has its **own** engine/session — it reads from the same `test.db` file, but writes from `create_user` may not be visible due to SQLite locking or connection caching.

### 9.2 Root cause analysis

The `_auth_headers(client)` helper in `test_stats.py` calls `client.post("/login", ...)` but the user was created via direct `async_session` writes. Possible issues:

1. **SQLite WAL mode:** The subprocess's SQLAlchemy connection may not see uncommitted or recently-committed writes from the pytest process's connection if they use different WAL checkpoints.
2. **Timing:** The user creation happens in `create_user` fixture (sync wrapper around async), and the server may already be running by the time the user is inserted.
3. **Separate DB files:** If the subprocess resolves `DATABASE_URL` differently (relative path `./data/dev.db` vs absolute path), it might use a different DB file entirely.

### 9.3 Solution: Use the `auth_headers` fixture

The `conftest.py` already has an `auth_headers` fixture that:
1. Creates the user via `async_session` (direct DB write).
2. Logs in via `client.post("/login", ...)` (HTTP call to subprocess).

The problem is that `test_stats.py` uses `create_user` + manual `_auth_headers()` instead of the `auth_headers` fixture. But actually, both patterns have the same fundamental issue: they create the user via direct DB writes.

### 9.4 Fix Option A: Ensure DB visibility between processes (Recommended)

The core issue is that the subprocess and the pytest process share a SQLite file but may have caching issues. Fix by:

1. **Force WAL checkpoint after writes.** After creating the user in `create_user` and `auth_headers` fixtures, execute a WAL checkpoint to ensure data is flushed to the main DB file:

```python
from sqlalchemy import text

async def _ensure_wal_checkpoint(session):
    """Force WAL checkpoint so subprocess connections see latest writes."""
    await session.execute(text("PRAGMA wal_checkpoint(FULL)"))
```

Add this after every direct DB write in fixtures:

```python
@pytest.fixture
def create_user():
    async def _create():
        async with async_session() as session:
            # ... create user ...
            await session.commit()
            await session.execute(text("PRAGMA wal_checkpoint(FULL)"))
            return user
    return asyncio.get_event_loop().run_until_complete(_create())
```

2. **Alternatively, use `check_same_thread=False` and shared cache.** In the test `DATABASE_URL`, use:
```python
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}?cache=shared"
```

### 9.5 Fix Option B: Create users via API calls only

Instead of direct DB writes, create the test user via a one-time setup endpoint or use the subprocess's `/login` with pre-seeded data:

1. Add a `create_dev_user` script call before the server starts.
2. Or, modify the server's lifespan to create a dev user when `APP_ENV=test`.

This is a bigger change but eliminates the cross-process DB visibility issue entirely.

### 9.6 Fix Option C: Unified test client (no subprocess)

Replace the subprocess-based `server` + `client` fixtures with FastAPI's `TestClient` or `httpx.AsyncClient` with `ASGITransport`:

```python
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
```

This runs the app in-process, sharing the same DB engine. No subprocess, no cross-process visibility issues.

**Recommended approach:** Option C is the cleanest long-term fix. It eliminates the subprocess entirely and makes all tests use the same DB connection pool. However, it requires rewriting tests to use `async` patterns.

**Pragmatic approach:** Option A (WAL checkpoint) + Option B (dev user in lifespan) is the quickest fix with minimal test refactoring.

### 9.7 Fix `test_stats.py` specifically

The immediate failures are:

```
test_stats.py::test_pulse_no_actionlog_defaults_to_engaged - KeyError: 'access_token'
test_stats.py::test_pulse_stagnant_48h - KeyError: 'access_token'
...
```

The `_auth_headers(client)` function calls `client.post("/login", ...)` and expects `r.json()["access_token"]`. The login fails because the user doesn't exist in the subprocess's DB view.

**Quick fix for all three test files:**

1. Update `conftest.py` to ensure user creation is visible:
```python
@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    async def _prepare():
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
            except OSError:
                pass
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Pre-seed test user so it's in the DB file before subprocess starts
        async with async_session() as session:
            user = User(username="testuser", hashed_password=get_password_hash("testpass"))
            session.add(user)
            await session.commit()
    
    asyncio.get_event_loop().run_until_complete(_prepare())
    yield
```

Since `prepare_database` runs before `server` starts (both are session-scoped, `prepare_database` is `autouse=True`), the user will be in the DB file before the subprocess opens it.

2. Update `_auth_headers` in `test_stats.py` to handle login failure gracefully:
```python
def _auth_headers(client):
    r = client.post("/login", json={"username": "testuser", "password": "testpass"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
```

3. Remove redundant `create_user` calls from individual tests (user is pre-seeded).

### 9.8 Update test_sessions.py and test_system_states.py

Apply the same pattern: use the pre-seeded user, remove direct DB user creation from test setup.

### 9.9 Add a conftest docstring documenting the two patterns

```python
"""Test fixtures for the Ambient AI Productivity Dashboard.

Two test patterns are used:

1. **In-process async tests** (test_ghost_list.py, test_ai.py, etc.):
   Use `async_session` directly to call service functions.
   No server subprocess. Fast, no cross-process issues.

2. **HTTP integration tests** (test_stats.py, test_sessions.py, etc.):
   Use `client` fixture which talks to a real uvicorn subprocess.
   Requires pre-seeded DB data (created in `prepare_database`).
   Use `auth_headers` fixture for authentication.
"""
```

## Integration & Edge Cases

- **Session-scoped user:** The user is created once for the entire test session. Tests that delete the user will break subsequent tests. Add a note: do not delete the pre-seeded user.
- **Parallel test execution:** If `pytest-xdist` is used for parallel execution, the subprocess approach has race conditions. Stick to sequential execution for now.
- **`create_user` fixture still used by other tests:** Keep the fixture for tests that need a specific user creation flow, but update it to use WAL checkpoint.
- **Test DB cleanup:** The `_clear_tables()` helpers in `test_stats.py` use direct `async_session` writes. These may also have visibility issues. Ensure WAL checkpoint after clears, or switch to HTTP-based cleanup.

## Acceptance Criteria

1. **AC-1:** `pytest tests/test_stats.py -v` passes all 5+ tests (0 failures).
2. **AC-2:** `pytest tests/test_sessions.py -v` passes all tests (0 errors).
3. **AC-3:** `pytest tests/test_system_states.py -v` passes all tests (0 errors).
4. **AC-4:** Full test suite `pytest -q` passes (136+ tests, 0 failures).
5. **AC-5:** No test uses direct DB writes that bypass the subprocess's visibility (or uses WAL checkpoint after writes).
6. **AC-6:** `conftest.py` docstring documents the two test patterns.

## Testing / QA

### Run commands
```bash
# Previously failing tests — must all pass
cd code/backend && python -m pytest tests/test_stats.py tests/test_sessions.py tests/test_system_states.py -v

# Full suite — must maintain 136+ passes, 0 failures
cd code/backend && python -m pytest -q --tb=short
```

### Manual QA checklist
1. Delete `tests/test.db` if it exists.
2. Run `pytest -q` — verify all tests pass.
3. Run again (without deleting DB) — verify still passes (idempotent).
4. Run individual test files in isolation — verify they pass independently.

## Files touched

- [code/backend/tests/conftest.py](code/backend/tests/conftest.py)
- [code/backend/tests/test_stats.py](code/backend/tests/test_stats.py)
- [code/backend/tests/test_sessions.py](code/backend/tests/test_sessions.py)
- [code/backend/tests/test_system_states.py](code/backend/tests/test_system_states.py)

## Estimated effort

1–2 dev days

## Concurrency & PR strategy

- **Suggested branch:** `phase-4.1/step-9-test-harness-fix`
- **Blocking steps:** Merge after Steps 1–5 to validate backend changes.
- **Merge Readiness:** false (pending implementation)

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Pre-seeded user conflicts with tests that create users | Use unique usernames per fixture; pre-seeded is "testuser" |
| WAL checkpoint slows fixture setup | Checkpoint is fast (~1ms); only runs in session-scoped fixture |
| Refactoring breaks currently-passing tests | Run full suite after every change; preserve existing patterns |

## References

- [MVP Final Audit §5](../../MVP_FINAL_AUDIT.md) — Test Status, Failing/Erroring Tests
- [code/backend/tests/conftest.py](code/backend/tests/conftest.py)
- [code/backend/tests/test_stats.py](code/backend/tests/test_stats.py)
- [SQLite WAL docs](https://www.sqlite.org/wal.html)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
