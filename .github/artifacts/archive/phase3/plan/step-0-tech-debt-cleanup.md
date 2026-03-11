# Step 0 — Backend Tech Debt Cleanup

## Purpose

Resolve correctness, safety, and code-quality issues identified in the Phase 2.2 final audit that directly impact Phase 3 development, establishing a clean foundation before adding new ManualReport and SystemState features.

## Deliverables

- Single canonical `get_current_user` dependency in `code/backend/app/api/auth.py` with null-safety (raises 401 if JWT `sub` is missing)
- All `datetime.utcnow()` calls replaced with `datetime.now(datetime.UTC)` across the backend
- Single `_to_camel` helper owned by `code/backend/app/schemas/base.py`; duplicate definitions in model files removed
- All `== None` SQLAlchemy comparisons replaced with `.is_(None)`
- `SessionLogSchema` redundant `alias_generator` / `model_config` cleaned to rely on `CamelModel` inheritance
- `ActionLogMiddleware` hardened: log exceptions with traceback instead of silently swallowing
- All existing tests pass green

## Primary files to change (required)

- [code/backend/app/api/auth.py](../../../../code/backend/app/api/auth.py) — harden `get_current_user`
- [code/backend/app/api/tasks.py](../../../../code/backend/app/api/tasks.py) — remove duplicate `get_current_user` and `oauth2_scheme`; import from `auth.py`
- [code/backend/app/api/sessions.py](../../../../code/backend/app/api/sessions.py) — verify imports use canonical `get_current_user` from `auth.py`
- [code/backend/app/api/stats.py](../../../../code/backend/app/api/stats.py) — replace `datetime.utcnow()` → `datetime.now(datetime.UTC)`; fix `== None` → `.is_(None)`
- [code/backend/app/db/base.py](../../../../code/backend/app/db/base.py) — replace `datetime.utcnow` in `TimestampedBase` defaults
- [code/backend/app/models/session_log.py](../../../../code/backend/app/models/session_log.py) — replace `datetime.utcnow()`, clean `SessionLogSchema.model_config`
- [code/backend/app/models/manual_report.py](../../../../code/backend/app/models/manual_report.py) — remove duplicate `_to_camel`
- [code/backend/app/models/system_state.py](../../../../code/backend/app/models/system_state.py) — remove duplicate `_to_camel`
- [code/backend/app/services/session_service.py](../../../../code/backend/app/services/session_service.py) — replace `datetime.utcnow()`
- [code/backend/app/middlewares/action_log.py](../../../../code/backend/app/middlewares/action_log.py) — harden error handling
- [code/backend/app/schemas/base.py](../../../../code/backend/app/schemas/base.py) — no change expected; verify it is the single `_to_camel` owner
- [code/backend/tests/conftest.py](../../../../code/backend/tests/conftest.py) — clean duplicate imports if present

## Detailed implementation steps

1. **Consolidate `get_current_user` with null-safety** in `code/backend/app/api/auth.py`:
   - Modify the existing `get_current_user` function to raise `HTTPException(401, "Invalid credentials")` if `payload.get("sub")` returns `None` or empty string.
   - Ensure `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")` is defined here.
   - Final signature: `async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:`

2. **Remove duplicate auth from `tasks.py`**:
   - Delete the local `oauth2_scheme` and `get_current_user` definitions in `code/backend/app/api/tasks.py`.
   - Replace with `from ..api.auth import get_current_user` (or `from .auth import get_current_user` depending on import style).
   - Verify all route functions still use `user: str = Depends(get_current_user)`.

3. **Verify `sessions.py` and `stats.py` imports**:
   - `code/backend/app/api/sessions.py` — confirm it imports `get_current_user` from `auth.py`. If it has its own copy, consolidate.
   - `code/backend/app/api/stats.py` — already imports from `app.api.auth`; confirm no local copy.

4. **Replace `datetime.utcnow()` globally**:
   - Add `from datetime import datetime, UTC` (Python 3.11+) or `from datetime import datetime, timezone` and use `datetime.now(timezone.utc)` at the top of each affected file.
   - Files to update:
     - `code/backend/app/db/base.py` — `TimestampedBase.created_at` and `updated_at` defaults: `default=lambda: datetime.now(timezone.utc)`
     - `code/backend/app/models/session_log.py` — `started_at` default, `elapsed_minutes` property
     - `code/backend/app/services/session_service.py` — `start_session()` and `stop_session()` explicit `utcnow()` calls
     - `code/backend/app/api/stats.py` — `now = datetime.utcnow()` in `get_pulse_stats`
   - Use `datetime.now(timezone.utc)` pattern (compatible with Python 3.10+).

5. **Remove duplicate `_to_camel` helpers**:
   - Delete the `_to_camel` function definition from:
     - `code/backend/app/models/manual_report.py`
     - `code/backend/app/models/system_state.py`
   - These files already import `CamelModel` from `..schemas.base` which owns `_to_camel`. The local copies are dead code.

6. **Fix `== None` SQLAlchemy comparisons**:
   - In `code/backend/app/api/stats.py`, find `SystemState.end_date == None` and replace with `SystemState.end_date.is_(None)`.
   - Grep the entire `code/backend/` for `== None` in SQLAlchemy context and fix any others.

7. **Clean `SessionLogSchema` model_config**:
   - In `code/backend/app/models/session_log.py`, the `SessionLogSchema` defines a redundant inline `alias_generator` lambda that duplicates what `CamelModel` already provides.
   - Replace `model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=lambda s: ...)` with `model_config = ConfigDict(from_attributes=True)`.
   - `CamelModel` already provides `alias_generator` and `populate_by_name`.

8. **Harden `ActionLogMiddleware`**:
   - In `code/backend/app/middlewares/action_log.py`, the `except Exception:` block uses `logger.exception(...)` which is correct (it logs the traceback). Verify this is in place.
   - Confirm the middleware does NOT re-raise — silent logging is acceptable for middleware (we don't want logging failures to break user requests).
   - Add a more specific comment explaining the design choice.

9. **Clean test imports**:
   - In `code/backend/tests/conftest.py`, remove duplicate `import os` on lines 1 and 4, duplicate `import asyncio` if present, and any other redundant imports.

10. **Run full test suite** to confirm no regressions:
    ```bash
    cd code/backend
    pytest tests/ -v --tb=short
    ```

## Integration & Edge Cases

- **Import chain:** After removing `get_current_user` from `tasks.py`, ensure the `from .auth import get_current_user` import resolves correctly from all router files. FastAPI circular import risk is low since `auth.py` does not import from other router files.
- **`datetime.now(timezone.utc)` vs `datetime.utcnow()`:** The new calls return timezone-aware datetimes. SQLite stores these as strings and may include `+00:00` suffix. Verify that existing SQLAlchemy `DateTime` columns handle this (SQLAlchemy typically strips tzinfo on storage and restores as naive). If this causes issues, use `datetime.now(timezone.utc).replace(tzinfo=None)` to keep naive UTC datetimes.
- **`_to_camel` removal safety:** The removed functions in model files are not called anywhere — schemas inherit from `CamelModel` which has its own. Confirm with `grep -r "_to_camel" code/backend/` that only `schemas/base.py` defines it after cleanup.
- No persistence changes in this step — no backup or migration required.

## Acceptance Criteria

1. `grep -r "def get_current_user" code/backend/app/` returns exactly ONE match in `code/backend/app/api/auth.py`.
2. `get_current_user` raises `HTTPException(401)` when JWT `sub` claim is `None` or empty — verified by test.
3. `grep -rn "datetime.utcnow" code/backend/app/` returns zero matches.
4. `grep -rn "def _to_camel" code/backend/app/` returns exactly ONE match in `code/backend/app/schemas/base.py`.
5. `grep -rn "== None" code/backend/app/` returns zero matches in SQLAlchemy query contexts (`.where()`, `.filter()` calls).
6. `SessionLogSchema.model_config` no longer contains an inline `alias_generator` lambda.
7. All existing tests in `code/backend/tests/` pass: `pytest tests/ -v` exits 0.
8. Manual: Start backend, call `POST /sessions/start` → verify camelCase JSON still correct. Call `GET /stats/pulse` → verify response shape unchanged.

## Testing / QA

### Tests to add/modify — `code/backend/tests/test_api.py` or `test_auth.py`

```python
def test_missing_sub_claim_returns_401(client):
    """Verify get_current_user rejects tokens with no 'sub' claim."""
    from app.core.security import create_access_token
    # Create a token with empty subject
    bad_token = create_access_token(subject="")
    r = client.get("/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert r.status_code == 401
```

### Manual QA checklist

1. Start backend: `cd code/backend && uvicorn app.main:app --reload`
2. Login → get token → call `GET /tasks/` → verify 200 response (tasks router uses consolidated auth)
3. Call `POST /sessions/start` with valid body → verify 201 with camelCase JSON
4. Call `GET /stats/pulse` → verify response contains `silenceState`, `lastActionAt`, `gapMinutes`
5. Call `POST /sessions/stop` → verify 200
6. Run `pytest tests/ -v` → all green

## Files touched (repeat for reviewers)

- [code/backend/app/api/auth.py](../../../../code/backend/app/api/auth.py)
- [code/backend/app/api/tasks.py](../../../../code/backend/app/api/tasks.py)
- [code/backend/app/api/sessions.py](../../../../code/backend/app/api/sessions.py)
- [code/backend/app/api/stats.py](../../../../code/backend/app/api/stats.py)
- [code/backend/app/db/base.py](../../../../code/backend/app/db/base.py)
- [code/backend/app/models/session_log.py](../../../../code/backend/app/models/session_log.py)
- [code/backend/app/models/manual_report.py](../../../../code/backend/app/models/manual_report.py)
- [code/backend/app/models/system_state.py](../../../../code/backend/app/models/system_state.py)
- [code/backend/app/services/session_service.py](../../../../code/backend/app/services/session_service.py)
- [code/backend/app/middlewares/action_log.py](../../../../code/backend/app/middlewares/action_log.py)
- [code/backend/tests/conftest.py](../../../../code/backend/tests/conftest.py)

## Estimated effort

0.5–1 dev day (mechanical refactoring + test verification)

## Concurrency & PR strategy

- **Suggested branch:** `phase-3/step-0-tech-debt-cleanup`
- **Blocking steps:** None — this is the first step.
- **Merge Readiness:** false (set to true after implementation and tests pass)
- This step MUST merge before Steps 1, 2, or any other Phase 3 step.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `datetime.now(timezone.utc)` returns tz-aware datetime that breaks SQLite storage | Test timestamp round-trip; if needed, use `.replace(tzinfo=None)` to keep naive UTC |
| Removing `get_current_user` from tasks.py breaks import | Update import to `from .auth import get_current_user`; tests will catch |
| `_to_camel` removal accidentally breaks a schema | Grep confirms the removed definitions are dead code; CamelModel inheritance provides the function |

## References

- [Phase 2.2 Final Report — Backend Findings](../../archive/phase2-2/summary/final-report.md)
- [schemas/base.py — CamelModel](../../../../code/backend/app/schemas/base.py)
- [PLANNING.md](../../PLANNING.md)
- [Phase 3 Master](./master.md)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
- [ ] Author signoff
