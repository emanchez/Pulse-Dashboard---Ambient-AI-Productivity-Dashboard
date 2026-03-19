# Phase 4.1 (Group C) Implementation Summary — Step 9: Test Harness Fix

**Date:** 2026-03-19
**Status:** ✅ Complete
**Test Result:** `185 passed, 0 failures` (full suite)
**Previously failing:** `test_stats.py` (5), `test_sessions.py` (all), `test_system_states.py` (all)

---

## ✅ Root Causes Identified & Fixed

### Root Cause 1 — Stale action_type query pattern (`test_system_states.py`)

`test_action_log_entries_created` queried `ActionLog.action_type.like("%/system-states%")` — the old HTTP-path format from before Step 1. After Step 1, action types are semantic strings: `SYSTEM_STATE_CREATE`, `TASK_CREATE`, etc.

**Fix:** Updated query to `action_type.like("SYSTEM_STATE%")` to match the new semantic format.

**Same issue in `tests/e2e/test_smoke.py`:** Checked `action_type.startswith("POST /tasks")` — updated to `action_type == "TASK_CREATE"`.

### Root Cause 2 — Cross-process SQLite WAL visibility

The `server` fixture spawns a uvicorn subprocess that writes ActionLog rows to `test.db`. The pytest process then reads those rows via its own `async_session` connection. Without forcing a WAL checkpoint, the pytest process's connection may not see rows recently written by the subprocess (SQLite WAL pages are not visible to other connections until checkpointed).

**Fix:** Added `async def _wal_checkpoint(session)` helper in `conftest.py` that executes `PRAGMA wal_checkpoint(FULL)`. Called:
- In all fixtures after direct DB writes (`create_user`, `_session_auth_token`, `_session_auth_token_b`)
- In `test_stats.py` helpers: `_clear_tables`, `_insert_action`, `_insert_system_state`
- In `test_system_states.py::test_action_log_entries_created` before reading ActionLog
- In `tests/e2e/test_smoke.py::test_e2e_login_and_tasks_flow` before reading ActionLog

### Root Cause 3 — Rate limiter triggering on `/login` (429 errors)

`auth_headers` was function-scoped and called `client.post("/login")` for every test. The full suite has 30+ tests using `auth_headers`, hitting slowapi's rate limit of 100 requests/minute on the `/login` endpoint.

**Fix:** Introduced two session-scoped fixtures:
- `_session_auth_token` — logs in as `testuser` **once** per test session
- `_session_auth_token_b` — logs in as `testuser2` **once** per test session

`auth_headers` and `auth_headers_b` are now cheap wrappers that return `{"Authorization": f"Bearer {token}"}` from the cached token — no HTTP call per test.

### Root Cause 4 — `asyncio.get_event_loop()` deprecation breaking cross-file tests

Naively replacing `asyncio.get_event_loop().run_until_complete()` with `asyncio.run()` in `prepare_database` caused `RuntimeError: There is no current event loop` in other test files (`test_inference_context.py`, etc.) that use `asyncio.get_event_loop()` internally. `asyncio.run()` creates AND closes the event loop; subsequent callers find no current loop.

**Fix:** Added a session-scoped `session_event_loop` fixture that:
1. Creates a fresh `asyncio.new_event_loop()`
2. Sets it as the current loop via `asyncio.set_event_loop(loop)`
3. Yields the loop so `prepare_database` (which depends on it) can call `session_event_loop.run_until_complete()` explicitly
4. Closes only after the entire session ends

All `get_event_loop().run_until_complete()` calls in other test files now find this shared session loop, eliminating the RuntimeError.

### Root Cause 5 — `create_user` fixture deleted + recreated user (UUID orphaning)

The original `create_user` fixture deleted the existing user then inserted a new one — generating a new UUID on every run. Any rows (tasks, action logs, etc.) previously associated with the old UUID became invisible to the API (all queries scope by `user_id`).

**Fix:** Changed to an upsert pattern — if the user exists, only the password is reset and the UUID is preserved. This aligns with the hard-won lesson documented in `copilot-instructions.md`.

---

## Files Changed

| File | Change |
|---|---|
| `tests/conftest.py` | Full rewrite: session event loop fixture, session-scoped auth tokens, WAL checkpoint helper, upsert `create_user`, comprehensive docstring |
| `tests/test_stats.py` | Added WAL checkpoint to `_clear_tables`, `_insert_action`, `_insert_system_state`; added assert message to `_auth_headers` |
| `tests/test_system_states.py` | Fixed `action_type.like("SYSTEM_STATE%")` query; added WAL checkpoint in `test_action_log_entries_created` |
| `tests/e2e/test_smoke.py` | Fixed `action_type == "TASK_CREATE"` check; added WAL checkpoint before DB read |

---

## Test Results

### Before
```
39 passed, 1 failed (test_action_log_entries_created)
+ 57 failed, 36 errors (full suite — rate limiter + event loop + WAL)
```

### After
```
185 passed, 0 failures, 2 warnings (full suite)
40/40 in test_stats.py + test_sessions.py + test_system_states.py
```

The 2 warnings are pre-existing `InsecureKeyLengthWarning` from `jwt` package in `test_api.py` — unrelated to this step.

---

## Acceptance Criteria Verification

| AC | Criterion | Result |
|---|---|---|
| AC-1 | `pytest tests/test_stats.py -v` — 0 failures | ✅ 10/10 pass |
| AC-2 | `pytest tests/test_sessions.py -v` — 0 errors | ✅ 9/9 pass |
| AC-3 | `pytest tests/test_system_states.py -v` — 0 errors | ✅ 21/21 pass |
| AC-4 | Full suite `pytest -q` — 0 failures | ✅ 185 passed |
| AC-5 | No test does a direct DB read from subprocess-written data without WAL checkpoint | ✅ All `_check()` helpers checkpoint first |
| AC-6 | `conftest.py` has docstring documenting the two test patterns | ✅ Comprehensive module docstring added |

---

## Hard-Won Lessons Applied

- **Silent `nohup` startup hides crashes:** `server` fixture logs subprocess output to `subprocess.DEVNULL` — acceptable for subprocess fixture since the health check loop verifies it's alive. For `make start`, the bug-report fix already added `logs/backend.log`.
- **Seeding scripts must be idempotent (upsert, not delete+recreate):** `create_user` fixture now upserts. Previously, delete+recreate generated a new UUID and orphaned all test data.
- **Rate limiter on `/login` must be respected in tests:** Calling `/login` per-test hits the 100/min limit. Session-scoped token caching is the correct pattern.
- **`asyncio.run()` closes the event loop — cannot be used when other code expects a persistent loop:** Replaced with a session-scoped shared event loop using `asyncio.new_event_loop()` + `asyncio.set_event_loop()`.
- **SQLite WAL is not auto-visible across connections:** Any pytest-process DB write that must be seen by the subprocess requires `PRAGMA wal_checkpoint(FULL)` before the cross-process read.
