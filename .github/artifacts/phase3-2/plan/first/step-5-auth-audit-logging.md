# Step 5 — Auth Audit Logging

**Audit finding addressed:** S-15 (no audit log for auth events)

---

## Purpose

Record login attempts — both successful and failed — in the `action_logs` table so that auth events are visible in the activity trail and can be used for future security monitoring.

---

## Deliverables

- `code/backend/app/api/auth.py` — `_log_auth_event` async helper added; called at the end of `POST /login` for both success and failure paths.

---

## Primary files to change

- [code/backend/app/api/auth.py](code/backend/app/api/auth.py)

---

## Detailed implementation steps

1. **`app/api/auth.py`** — Add a fire-and-forget helper function `_log_auth_event` that inserts an `ActionLog` row using its own short-lived `async_sessionmaker` session (so it never blocks or fails the login response):

   ```python
   from ..db.session import async_session_maker   # import the sessionmaker, not the dependency
   from ..models.action_log import ActionLog
   import uuid
   
   async def _log_auth_event(
       action_type: str,
       summary: str,
       user_id: str | None,
       client_host: str | None,
   ) -> None:
       """Write an auth event to action_logs. Never raises — errors are swallowed."""
       try:
           async with async_session_maker() as session:
               log = ActionLog(
                   id=str(uuid.uuid4()),
                   user_id=user_id,
                   action_type=action_type,
                   summary=summary,
                   client_host=client_host,
               )
               session.add(log)
               await session.commit()
       except Exception:
           pass  # Auth logging must never block or break the login response
   ```

   > **Important:** `client_host` is populated from `request.client.host` if `request.client` is not `None`. The `Request` object must be available in the login route handler (see step 2).

2. **`POST /login` route handler** — Add `request: Request` as a parameter if not already present (required for `request.client.host`). At the end of each code path:

   - On **authentication failure** (user not found or password incorrect), before returning 401:
     ```python
     await _log_auth_event(
         action_type="LOGIN_FAILED",
         summary=f"Failed login attempt for username '{payload.username}'",
         user_id=None,
         client_host=request.client.host if request.client else None,
     )
     ```

   - On **authentication success**, before returning the token:
     ```python
     await _log_auth_event(
         action_type="LOGIN_SUCCESS",
         summary=f"Successful login for user '{user.username}'",
         user_id=str(user.id),
         client_host=request.client.host if request.client else None,
     )
     ```

3. **Stats service exclusion** — The `GET /stats/pulse` endpoint and `calculate_flow_state` service query `action_logs` to determine user activity. Auth events must NOT be counted as user activity — they would cause a fresh login to reset the silence/staleness gap to zero, masking procrastination signals. Both queries must filter out auth action types:

   - **`app/api/stats.py`** — In the `last_action_stmt` query, add:
     ```python
     .where(ActionLog.action_type.notin_(("LOGIN_SUCCESS", "LOGIN_FAILED")))
     ```
   - **`app/services/flow_state.py`** — In the `calculate_flow_state` query, add the same `.where(ActionLog.action_type.notin_(...))` filter.

   > **This is a required part of this step.** Omitting these filters make the stats tests fail — the `auth_headers` fixture calls `/login` before each test, creating a `LOGIN_SUCCESS` entry that poisons the pulse/flow gap calculation.

4. **`ActionLog` model — `client_host` field:** The existing `ActionLog` model in `code/backend/app/models/action_log.py` may not have a `client_host` column. If it does not:
   - Add `client_host: Mapped[str | None] = mapped_column(String(45), nullable=True)` to the model.
   - Run an `ALTER TABLE action_logs ADD COLUMN client_host VARCHAR(45)` migration on `dev.db`.
   - **BEFORE MERGE:** snapshot `dev.db` before adding the column.
   - If adding the column is too risky for this step, log the client IP in the `summary` string instead and skip the `client_host` field. Document the trade-off.

---

## Integration & Edge Cases

- **`_log_auth_event` must never raise:** The `try/except Exception: pass` pattern is intentional. A failure to write the audit log (network blip, DB lock) must not cause the `/login` endpoint to return 500. This is consistent with the pattern used by `ActionLogMiddleware`.
- **`user_id=None` for failed logins:** The username in a failed login attempt may not correspond to any real user. Storing `user_id=None` is correct; the `summary` field captures the attempted username as a string.
- **`async_session_maker` vs `get_async_session`:** The login route uses FastAPI's DI-provided session via `Depends(get_async_session)`. The `_log_auth_event` helper must NOT reuse the request-scoped session — it has its own commit lifecycle. Import and use `async_session_maker` directly.
- **Stats service pollution:** Login events in `action_logs` will pollute the pulse/flow-state calculation if not filtered. The filter in step 3 (`action_type.notin_(...)`) is mandatory. Define the excluded types as a module-level constant to avoid repetition:
  ```python
  _AUTH_ACTION_TYPES = ("LOGIN_SUCCESS", "LOGIN_FAILED")
  ```
- **`client_host` as IPv6:** `request.client.host` returns a string that may be an IPv6 address (up to 45 chars). Use `String(45)` for the column — sufficient for the longest IPv6 address.
- **`action_type` field length:** Confirm `ActionLog.action_type` column allows at least 32 characters. `"LOGIN_SUCCESS"` is 13 characters.

---

## Acceptance Criteria

1. A successful `POST /login` creates a row in `action_logs` with `action_type="LOGIN_SUCCESS"` and `user_id` set to the authenticated user's ID.
2. A failed `POST /login` (wrong password) creates a row in `action_logs` with `action_type="LOGIN_FAILED"` and `user_id=None`.
3. The `GET /stats/pulse` endpoint does NOT count `LOGIN_SUCCESS` or `LOGIN_FAILED` events when computing `gapMinutes` or `silenceState`.
4. `GET /stats/flow-state` does NOT include login events in the activity buckets.
5. `POST /login` continues to return the token (200) or 401 without any change in latency or behaviour — the audit log write is non-blocking.
6. All existing backend tests pass: `pytest code/backend/tests/ -q` exits 0.

---

## Testing / QA

**Tests to add in `code/backend/tests/test_api.py`:**

- `test_successful_login_creates_audit_log` — Call `POST /login` with correct credentials. Query `action_logs` directly via a test DB session. Assert one row with `action_type == "LOGIN_SUCCESS"` and `user_id == <test user id>`.
- `test_failed_login_creates_audit_log` — Call `POST /login` with wrong password. Query `action_logs`. Assert one row with `action_type == "LOGIN_FAILED"` and `user_id is None`.
- Confirm existing stats tests (`test_stats.py`) still pass (they rely on the stat service exclusion filter in step 3 of implementation).

```bash
.venv/bin/pytest code/backend/tests/test_api.py -q -k "audit_log"
.venv/bin/pytest code/backend/tests/test_stats.py -q
```

**Manual QA checklist:**

1. Start dev server.
2. Attempt login with wrong credentials:
   ```bash
   curl -s -X POST http://127.0.0.1:8001/login \
     -H "Content-Type: application/json" \
     -d '{"username":"devuser","password":"wrongpass"}'
   ```
3. Query the DB: `sqlite3 code/backend/data/dev.db "SELECT action_type, user_id, summary FROM action_logs ORDER BY created_at DESC LIMIT 3;"`. Expect a `LOGIN_FAILED` row.
4. Login with correct credentials. Expect a `LOGIN_SUCCESS` row.
5. Confirm `GET /stats/pulse` gap is not reset to 0 by the login events (gap should reflect actual task/report activity, not login time).

---

## Files touched

- [code/backend/app/api/auth.py](code/backend/app/api/auth.py)
- [code/backend/app/api/stats.py](code/backend/app/api/stats.py)
- [code/backend/app/services/flow_state.py](code/backend/app/services/flow_state.py)
- [code/backend/app/models/action_log.py](code/backend/app/models/action_log.py) *(if `client_host` column is added)*

---

## Estimated effort

0.5–1 dev day

---

## Concurrency & PR strategy

- `Blocking steps:` Blocked until Step 1 merges — the `auth.py` modifications interact with the updated login handler, and the test assertions rely on `decode_access_token` from the updated `security.py`.
- `Merge Readiness: false` — set to `true` once Step 1 is merged and all 6 acceptance criteria pass.
- `Depends-On: phase-3.2/step-1-jwt-auth-hardening`
- Branch: `phase-3.2/step-5-auth-audit-logging`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `action_logs` table missing `client_host` column causes `OperationalError` | Explicitly add the column via `ALTER TABLE` before running tests. If deferred: log IP in `summary` field and skip the column in this step. |
| `_log_auth_event` slow DB write adds latency to login | The helper is `await`-ed but uses its own short session. For further de-risking, fire it as a `asyncio.create_task` (truly background). Evaluate after testing. |
| Stats queries return incorrect results after auth events inserted | Covered by the mandatory `action_type.notin_(...)` filter in step 3. All `test_stats.py` tests must pass before marking `Merge Readiness: true`. |
| `async_session_maker` not exported from `db/session.py` | Confirm the export name. Typical pattern: `async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`. |

---

## References

- [.github/artifacts/phase3-2/summary/final-report.md](../../summary/final-report.md) — S-15
- [code/backend/app/api/auth.py](code/backend/app/api/auth.py)
- [code/backend/app/models/action_log.py](code/backend/app/models/action_log.py)
- [code/backend/app/api/stats.py](code/backend/app/api/stats.py)
- [code/backend/app/services/flow_state.py](code/backend/app/services/flow_state.py)

---

## Author Checklist

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/`
- [x] Manual QA checklist added
- [x] Backup/atomic-write noted (`dev.db` snapshot required if `client_host` column added)
