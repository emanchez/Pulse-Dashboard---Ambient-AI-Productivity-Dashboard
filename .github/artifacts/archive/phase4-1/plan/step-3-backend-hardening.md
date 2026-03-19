# Step 3 — Backend Hardening: Settings Cache, N+1 Fix, Status Enum, User Verification

## Purpose

Address four moderate backend issues from the audit that are independent of each other but all relate to backend correctness and hardening:

1. **`get_settings()` creates a fresh `Settings` object per call** — wasteful, should be cached.
2. **N+1 query pattern in `_validate_task_ids`** — loops individual `db.get()` calls instead of batch query.
3. **ManualReport status validation excludes `archived`** — the `archive_report` endpoint sets `status="archived"` but the `ManualReportUpdate` validator only allows `{"draft", "published"}`, creating a mismatch.
4. **`get_current_user()` does not verify user exists in DB** — a deleted user's JWT remains valid until expiry.

## Deliverables

- Cached `get_settings()` using `@lru_cache`.
- Batch query in `_validate_task_ids` replacing the N+1 loop.
- `"archived"` added to `ManualReportCreate` and `ManualReportUpdate` allowed status values.
- `get_current_user()` verifies user exists in the DB (returns 401 if not).
- Tests for each fix.

## Primary files to change

- [code/backend/app/core/config.py](code/backend/app/core/config.py) — Add `@lru_cache` to `get_settings()`
- [code/backend/app/services/report_service.py](code/backend/app/services/report_service.py) — Batch query in `_validate_task_ids`
- [code/backend/app/models/manual_report.py](code/backend/app/models/manual_report.py) — Add `"archived"` to status validators
- [code/backend/app/api/auth.py](code/backend/app/api/auth.py) — Add DB lookup in `get_current_user()`
- [code/backend/tests/test_api.py](code/backend/tests/test_api.py) — Tests for all four fixes
- [code/backend/tests/test_reports.py](code/backend/tests/test_reports.py) — Test for status enum fix

## Detailed implementation steps

### 3.1 Cache `get_settings()` with `@lru_cache`

In [code/backend/app/core/config.py](code/backend/app/core/config.py):

```python
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

This ensures `Settings()` is only instantiated once (parsing `.env` and env vars). All callers get the same instance. Note: `@lru_cache` (unbounded) is appropriate since there's only one possible input (no args).

**Edge case:** If tests need to override settings, they'll need to call `get_settings.cache_clear()` after patching env vars. Add a note in the docstring.

### 3.2 Fix N+1 query in `_validate_task_ids`

In [code/backend/app/services/report_service.py](code/backend/app/services/report_service.py), replace:

```python
async def _validate_task_ids(db: AsyncSession, task_ids: list[str]) -> None:
    for task_id in task_ids:
        result = await db.get(Task, task_id)
        ...
```

With a single batch query:

```python
async def _validate_task_ids(db: AsyncSession, task_ids: list[str]) -> None:
    """Raise 400 if any task ID does not exist, or 500 on DB error."""
    if not task_ids:
        return
    
    try:
        stmt = select(Task.id).where(Task.id.in_(task_ids))
        result = await db.execute(stmt)
        found_ids = set(result.scalars().all())
    except SQLAlchemyError as exc:
        logger.exception("Database error while validating task IDs")
        raise HTTPException(
            status_code=500,
            detail="Database error while validating linked tasks",
        ) from exc
    
    missing = set(task_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Task(s) not found: {', '.join(sorted(missing))}",
        )
```

This reduces N queries to 1 query, using `IN (...)` clause. Reports the first missing IDs in the error.

### 3.3 Add `"archived"` to ManualReport status validators

In [code/backend/app/models/manual_report.py](code/backend/app/models/manual_report.py), update both `ManualReportCreate` and `ManualReportUpdate`:

**ManualReportCreate.status_valid:**
```python
@field_validator("status")
@classmethod
def status_valid(cls, v: str) -> str:
    allowed = {"draft", "published", "archived"}
    if v not in allowed:
        raise ValueError(f"status must be one of {allowed}")
    return v
```

**ManualReportUpdate.status_valid:**
```python
@field_validator("status")
@classmethod
def status_valid(cls, v: str | None) -> str | None:
    if v is None:
        return v
    allowed = {"draft", "published", "archived"}
    if v not in allowed:
        raise ValueError(f"status must be one of {allowed}")
    return v
```

Extract the allowed set to a module-level constant to avoid repetition:

```python
REPORT_STATUSES = {"draft", "published", "archived"}
```

### 3.4 Verify user exists in `get_current_user()`

In [code/backend/app/api/auth.py](code/backend/app/api/auth.py), the current `get_current_user()` only decodes the JWT and returns `sub` — it never checks the DB:

```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    payload = decode_access_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return sub
```

Update to add a DB lookup:

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> str:
    payload = decode_access_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # Verify user still exists in DB (prevents deleted-user token reuse)
    user = await session.get(User, sub)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    return sub
```

**Import required:** Add `from ..models.user import User` and `from ..db.session import get_async_session` at the top of auth.py (the session import likely already exists).

**Performance note:** This adds one primary-key lookup per authenticated request. On SQLite this is ~0.1ms. For production with higher traffic, consider an in-memory TTL cache (out of scope for this step).

## Integration & Edge Cases

- **`@lru_cache` and tests:** Tests that need custom settings must call `get_settings.cache_clear()`. Existing tests that monkeypatch `os.environ` before import will still work since `get_settings()` is called at import time in several modules. Need to audit whether any tests depend on per-call Settings re-creation.
- **Batch query and duplicates:** If `task_ids` contains duplicates (e.g. `["abc", "abc"]`), the `set()` comparison handles it correctly.
- **`archived` status on create:** While unlikely, a user could create a report as `"archived"`. This is valid — it might be an import or deliberate filing.
- **`get_current_user` signature change:** Adding `session: AsyncSession` parameter changes the dependency injection chain. All route handlers that use `get_current_user` will now have an additional DB session dependency injected. Since FastAPI dependency injection is declarative, this should be seamless — but verify that no route handler manually creates its own session in a conflicting way.

## Acceptance Criteria

1. **AC-1:** `get_settings()` returns the same object identity on consecutive calls (`id(get_settings()) == id(get_settings())`).
2. **AC-2:** Creating a report with `associated_task_ids` containing 10 valid IDs produces exactly 1 SQL query for validation (not 10).
3. **AC-3:** Creating a report with `associated_task_ids` containing an invalid ID returns 400 with the missing ID in the error message.
4. **AC-4:** `POST /reports` with `{"status": "archived", ...}` succeeds (201).
5. **AC-5:** `PUT /reports/{id}` with `{"status": "archived"}` succeeds (200).
6. **AC-6:** After deleting a user directly from the DB, requests using that user's JWT return 401 (not 200 with stale data).
7. **AC-7:** All existing tests continue to pass.

## Testing / QA

### Tests to add

- **File:** [code/backend/tests/test_api.py](code/backend/tests/test_api.py)
  - `test_get_settings_cached` — Call `get_settings()` twice, assert same `id()`.
  
- **File:** [code/backend/tests/test_reports.py](code/backend/tests/test_reports.py)
  - `test_create_report_with_archived_status` — POST with `status: "archived"`, expect 201.
  - `test_update_report_to_archived_status` — PUT with `status: "archived"`, expect 200.
  - `test_validate_task_ids_batch_reports_missing` — POST with invalid `associated_task_ids`, expect 400.

- **File:** [code/backend/tests/test_api.py](code/backend/tests/test_api.py)
  - `test_deleted_user_token_returns_401` — Create user, get token, delete user from DB, make authenticated request, expect 401.

### Run commands
```bash
cd code/backend && python -m pytest tests/test_api.py tests/test_reports.py -v
```

### Manual QA checklist
1. Start backend, call any authenticated endpoint — verify it works.
2. Create a report with `status: "archived"` — verify 201.
3. Check server logs for "creating Settings" (or add a log line) — verify it only appears once.

## Files touched

- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [code/backend/app/services/report_service.py](code/backend/app/services/report_service.py)
- [code/backend/app/models/manual_report.py](code/backend/app/models/manual_report.py)
- [code/backend/app/api/auth.py](code/backend/app/api/auth.py)
- [code/backend/tests/test_api.py](code/backend/tests/test_api.py)
- [code/backend/tests/test_reports.py](code/backend/tests/test_reports.py)

## Estimated effort

1 dev day

## Concurrency & PR strategy

- **Suggested branch:** `phase-4.1/step-3-backend-hardening`
- **Blocking steps:** None — independent of Steps 1 and 2.
- **Merge Readiness:** false (pending implementation)
- Step 4 depends on this step (uses cached `get_settings()`).

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `@lru_cache` prevents test env var overrides | Document `get_settings.cache_clear()` pattern; add to test fixtures if needed |
| `get_current_user` DB lookup adds latency | PK lookup is ~0.1ms on SQLite; negligible for single-user app |
| Changing `get_current_user` signature breaks routes | FastAPI DI handles new `Depends` params transparently; run full test suite |

## References

- [MVP Final Audit §4 Backend](../../MVP_FINAL_AUDIT.md) — `get_settings()`, N+1, status mismatch
- [MVP Final Audit §3.2](../../MVP_FINAL_AUDIT.md) — `get_current_user()` should verify user exists
- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [code/backend/app/services/report_service.py](code/backend/app/services/report_service.py)
- [code/backend/app/models/manual_report.py](code/backend/app/models/manual_report.py)
- [code/backend/app/api/auth.py](code/backend/app/api/auth.py)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
