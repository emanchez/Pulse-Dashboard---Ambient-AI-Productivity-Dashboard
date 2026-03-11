# Step 1 — Backend: CORS Config Hardening & Service Exception Handling

## Purpose

Fix two independent backend failures that together cause a CORS-blocked 500 response on `/reports` and `/tasks/`: (1) the `FRONTEND_CORS_ORIGINS` setting resolves to a single origin when a developer's shell environment has the variable exported, and (2) `report_service.py` has no exception handling, so any DB error propagates as an unhandled exception whose 500 response is sent without a CORS header.

---

## Deliverables

- Updated `code/backend/app/core/config.py` — CORS origin parsing fixed; `env_file` re-enabled; `isinstance` dead code replaced with a `@field_validator`.
- Updated `code/backend/.env` — `FRONTEND_CORS_ORIGINS` set to a comma-separated, four-origin string covering all dev cases.
- Updated `code/backend/app/services/report_service.py` — `create_report` and `update_report` wrap `db.get`, `db.commit`, and `db.refresh` in `try/except SQLAlchemyError` and re-raise as `HTTPException(500)`.
- Updated `code/backend/tests/test_reports.py` — new test asserting structured 500 response shape on a simulated DB commit error.

---

## Primary files to change

- [code/backend/app/core/config.py](../../../../code/backend/app/core/config.py)
- [code/backend/.env](../../../../code/backend/.env)
- [code/backend/app/services/report_service.py](../../../../code/backend/app/services/report_service.py)
- [code/backend/tests/test_reports.py](../../../../code/backend/tests/test_reports.py)

---

## Detailed implementation steps

### 1. Fix `config.py` — Enable `.env` loading and repair origin parsing

**File:** [code/backend/app/core/config.py](../../../../code/backend/app/core/config.py)

**Current state (broken):**
```python
class Settings(BaseSettings):
    frontend_cors_origins: List[str] = Field([...], env="FRONTEND_CORS_ORIGINS")

    class Config:
        env_file = None     # disables .env loading entirely
```
plus dead-code guard:
```python
def get_settings() -> Settings:
    s = Settings()
    if isinstance(origins, str):   # always False — pydantic parses list first
        ...
```

**Required changes:**

1a. Migrate from `class Config` to pydantic-settings V2 `model_config = SettingsConfigDict(...)`:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    frontend_cors_origins: str = Field(
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
        alias="FRONTEND_CORS_ORIGINS",
    )
    ...
```

- Declare `frontend_cors_origins` as **`str`** (not `List[str]`) so pydantic-settings passes the raw env-var string through without pre-parsing.

1b. Add a `@field_validator` on `frontend_cors_origins` to split on commas:
```python
from pydantic import field_validator

@field_validator("frontend_cors_origins", mode="before")
@classmethod
def parse_origins(cls, v: str | list) -> list[str]:
    if isinstance(v, list):
        return [o.strip() for o in v if o.strip()]
    return [o.strip() for o in str(v).split(",") if o.strip()]
```
Change the field type annotation to `list[str]` (the validator replaces the raw string).

1c. Remove (or leave as a no-op stub with a comment) the now-unnecessary `get_settings()` isinstance guard. The function itself can remain as the cached factory; just delete the dead conditional.

1d. Update the field default to an empty string (or a sensible dev default) since the validator handles all parsing:
```python
frontend_cors_origins: list[str] = Field(default_factory=list)
```
With `env_file=".env"` re-enabled, the `.env` value is always loaded if the file exists.

---

### 2. Update `.env` — All four dev origins as a comma-separated string

**File:** [code/backend/.env](../../../../code/backend/.env)

Replace the single-origin value:
```dotenv
# Before
FRONTEND_CORS_ORIGINS=http://localhost:3000

# After
FRONTEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001
```

This ensures that whether the backend reads from the file (new `env_file=".env"`) or from a shell-exported `FRONTEND_CORS_ORIGINS`, the validator correctly splits the comma-separated string into four origins.

---

### 3. Wrap DB calls in `report_service.py`

**File:** [code/backend/app/services/report_service.py](../../../../code/backend/app/services/report_service.py)

Add at the top of the file:
```python
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
```

In `create_report`, wrap the DB block:
```python
try:
    db.add(report)
    await db.commit()
    await db.refresh(report)
except SQLAlchemyError as exc:
    await db.rollback()
    raise HTTPException(status_code=500, detail="Database error while creating report") from exc
```

Similarly in `update_report`:
```python
try:
    await db.commit()
    await db.refresh(result)
except SQLAlchemyError as exc:
    await db.rollback()
    raise HTTPException(status_code=500, detail="Database error while updating report") from exc
```

Also wrap the Task ownership validation `await db.get(Task, task_id)` calls in both functions with the same `SQLAlchemyError` guard (catch and re-raise as 500 if the DB lookup itself errors — distinct from the intentional `HTTPException(400)` on "task not found").

---

### 4. Add test for structured 500 response

**File:** [code/backend/tests/test_reports.py](../../../../code/backend/tests/test_reports.py)

Add a test that patches `AsyncSession.commit` to raise `SQLAlchemyError` and asserts:
- Response status code is `500`.
- Response body is JSON with a `"detail"` key (not a raw stack trace).

Use `unittest.mock.patch` or `pytest-mock`'s `mocker.patch` targeting `sqlalchemy.ext.asyncio.AsyncSession.commit`.

---

## Integration & Edge Cases

- **`env_file` re-enablement:** With `env_file=".env"` active, pydantic-settings loads `.env` relative to the **working directory** when the server starts. If uvicorn is launched from a directory other than `code/backend/`, the `.env` file will not be found. This is acceptable for dev; document in the step that `uvicorn` must be started from `code/backend/`. Alternatively, use an absolute path via `Path(__file__).parent.parent / ".env"` in the config.
- **Shell env override still works:** If `FRONTEND_CORS_ORIGINS` is exported in the shell, pydantic-settings V2 gives shell env vars priority over `.env` file values. The validator handles both `str` (comma-separated) and `list` inputs, so shell-exported values still work correctly after this fix.
- **`db.rollback()` in async context:** The `await db.rollback()` call in the except block is safe for aiosqlite sessions. Confirm the `AsyncSession` is not in a finalizing state before rolling back (standard SQLAlchemy async pattern).
- **No persistence schema changes** — no migrations required.

---

## Acceptance Criteria

1. `GET http://localhost:8000/reports?offset=0&limit=20` with `Origin: http://localhost:3000` returns `Access-Control-Allow-Origin: http://localhost:3000` in response headers.
2. `GET http://localhost:8000/reports?offset=0&limit=20` with `Origin: http://127.0.0.1:3000` returns `Access-Control-Allow-Origin: http://127.0.0.1:3000` in response headers.
3. Both criteria 1 and 2 hold whether or not `FRONTEND_CORS_ORIGINS` is exported in the shell prior to starting the server.
4. A simulated `SQLAlchemyError` on `db.commit` during `POST /reports` returns HTTP 500 with `{"detail": "Database error while creating report"}` — not an HTML traceback.
5. `pytest -q` in `code/backend` — all 75 existing tests pass plus at least 1 new test for the structured-500 path; 0 failures.
6. Manual: start backend, open browser DevTools Network tab, navigate to `/reports` in the frontend — no `CORS header missing` error in the console.

---

## Testing / QA

### Automated tests

**File:** `code/backend/tests/test_reports.py`

- **Happy path (existing):** `test_create_report` — should still pass with no changes.
- **New — structured 500:** `test_create_report_db_commit_error` — patches `AsyncSession.commit` to raise `SQLAlchemyError`, POSTs a valid report, asserts 500 + `{"detail": "Database error while creating report"}`.

**Run:**
```bash
cd code/backend
pytest tests/test_reports.py -v
pytest -q
```

### Manual QA checklist

1. Start backend: `uvicorn app.main:app --reload --port 8000` (from `code/backend/`).
2. In a separate terminal, run: `curl -sS -H "Origin: http://localhost:3000" http://localhost:8000/health` — confirm `200` and `Access-Control-Allow-Origin: http://localhost:3000` header present.
3. Run: `curl -sS -H "Origin: http://127.0.0.1:3000" http://localhost:8000/health` — confirm same for `127.0.0.1:3000`.
4. Temporarily set `FRONTEND_CORS_ORIGINS=http://localhost:3000` in shell (`export`), restart backend, repeat steps 2–3 — confirm `127.0.0.1:3000` still returns the correct header (comma-split validator fires).
5. Unset the env var (`unset FRONTEND_CORS_ORIGINS`), restart backend, confirm same behavior.

---

## Files touched

- [code/backend/app/core/config.py](../../../../code/backend/app/core/config.py)
- [code/backend/.env](../../../../code/backend/.env)
- [code/backend/app/services/report_service.py](../../../../code/backend/app/services/report_service.py)
- [code/backend/tests/test_reports.py](../../../../code/backend/tests/test_reports.py)

---

## Estimated effort

0.5–1 dev day.

---

## Concurrency & PR strategy

Step 1 and Step 2 touch entirely different files and can be developed in parallel. Step 1 must be **deployed** before Step 2 reaches a live environment (Step 2 relies on CORS headers being present on `/tasks/`).

- **Branch:** `phase-3/bugfix/step-1-backend-cors`
- **Blocking steps:** None — this step is unblocked.
- **Merge Readiness:** false (set to `true` after all acceptance criteria pass)

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `env_file` relative path fails when uvicorn is started from a different cwd | Medium | Document `cd code/backend` before `uvicorn` startup; or use `Path(__file__)` absolute resolution |
| `SettingsConfigDict` not available in the installed pydantic-settings version | Low | Confirm `pydantic-settings>=2.0` in `requirements.txt`; fall back to `class Config` with `env_file=".env"` if needed |
| `await db.rollback()` in an already-closed session raises a secondary exception | Low | Wrap rollback in a nested `try/except Exception: pass` to suppress cascading errors |
| New 500 response shape breaks an existing test that asserts on raw error content | Low | Run full `pytest -q` before marking merge-ready |

---

## References

- [master.md](./master.md)
- [step-2-frontend-error-handling-and-type-safety.md](./step-2-frontend-error-handling-and-type-safety.md)
- [observations.txt](./observations.txt)
- [PLANNING.md](../../PLANNING.md)
- [code/backend/app/core/config.py](../../../../code/backend/app/core/config.py)
- [code/backend/app/services/report_service.py](../../../../code/backend/app/services/report_service.py)
- [code/backend/app/main.py](../../../../code/backend/app/main.py)
- pydantic-settings V2 docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

---

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added (`test_create_report_db_commit_error`)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected — **N/A: no schema changes**
