# Step 1 — SessionLog Model + Session Endpoints

## Purpose

Introduce a `SessionLog` database entity and three JWT-guarded FastAPI endpoints (`POST /sessions/start`, `POST /sessions/stop`, `GET /sessions/active`) so the frontend can track and display an active focus session with elapsed time, task name, and goal minutes.

## Deliverables

- `code/backend/app/models/session_log.py` — `SessionLog` SQLAlchemy model + `SessionLogSchema` / `SessionStartRequest` Pydantic schemas
- `code/backend/app/services/session_service.py` — helper functions: `get_active_session`, `start_session`, `stop_session`
- `code/backend/app/api/sessions.py` — router with three endpoints
- Updated `code/backend/app/main.py` — mounts `/sessions` router
- Updated `code/backend/app/db/base.py` — ensures `SessionLog` model is imported so Alembic sees it
- Alembic migration: `session_logs` table
- New tests: `code/backend/tests/test_sessions.py`

## Primary files to change (required)

- [code/backend/app/models/session_log.py](../../../../code/backend/app/models/session_log.py) *(new)*
- [code/backend/app/services/session_service.py](../../../../code/backend/app/services/session_service.py) *(new)*
- [code/backend/app/api/sessions.py](../../../../code/backend/app/api/sessions.py) *(new)*
- [code/backend/app/main.py](../../../../code/backend/app/main.py)
- [code/backend/app/db/base.py](../../../../code/backend/app/db/base.py)
- [code/backend/tests/test_sessions.py](../../../../code/backend/tests/test_sessions.py) *(new)*

## Detailed implementation steps

1. **Create `SessionLog` model** in `code/backend/app/models/session_log.py`:
   - Extend `TimestampedBase`; table name `session_logs`
   - Columns: `user_id: String(36)` (indexed, not null), `task_id: String(36)` (nullable), `task_name: String(256)` (nullable), `goal_minutes: Integer` (nullable), `started_at: DateTime` (default `datetime.utcnow`), `ended_at: DateTime` (nullable)
   - Add computed `@property elapsedMinutes(self) -> int` — returns `int((datetime.utcnow() - self.started_at).total_seconds() // 60)` when `ended_at` is `None`, else `int((self.ended_at - self.started_at).total_seconds() // 60)`.

2. **Create Pydantic schemas** in the same file:
   - `SessionStartRequest(CamelModel)`: `task_id: str | None`, `task_name: str`, `goal_minutes: int | None`
   - `SessionLogSchema(CamelModel)`: `id`, `user_id`, `task_id`, `task_name`, `goal_minutes`, `started_at`, `ended_at`, `elapsed_minutes` (all optional/nullable as appropriate); `model_config` with `from_attributes = True`

3. **Create `session_service.py`**:
   - `get_active_session(db, user_id) -> SessionLog | None` — queries `session_logs` where `user_id = user_id AND ended_at IS NULL`, orders by `started_at DESC`, returns first result.
   - `start_session(db, user_id, req: SessionStartRequest) -> SessionLog` — calls `get_active_session` first; if one exists, returns it (idempotent). Otherwise inserts a new `SessionLog` row and commits.
   - `stop_session(db, user_id) -> SessionLog | None` — fetches active session, sets `ended_at = datetime.utcnow()`, commits, returns updated row. Returns `None` if no active session.

4. **Create `sessions.py` router** in `code/backend/app/api/sessions.py`:
   - `POST /sessions/start` — body `SessionStartRequest`, response `SessionLogSchema` (201). Calls `start_session`. Raises `HTTPException(400)` if `task_name` is blank.
   - `POST /sessions/stop` — no body, response `SessionLogSchema`. Calls `stop_session`; raises `HTTPException(404, "No active session")` if nothing to stop.
   - `GET /sessions/active` — response `SessionLogSchema | None` (200 in both cases). Returns `None` as JSON `null` when no session active.
   - All routes use `get_current_user` dependency from `code/backend/app/api/auth.py` and `AsyncSession` from `code/backend/app/db/session.py`.

5. **Update `main.py`** — add `from .api import sessions as sessions_router` and `app.include_router(sessions_router.router, prefix="/sessions")` after the existing router includes.

6. **Update `code/backend/app/db/base.py`** — add `from ..models.session_log import SessionLog  # noqa: F401` so Alembic autogenerate picks up the model.

7. **Generate Alembic migration**:
   ```bash
   cd code/backend
   alembic revision --autogenerate -m "add_session_logs"
   alembic upgrade head
   ```
   Verify `session_logs` table exists in `data/dev.db`.

8. **Write tests** in `code/backend/tests/test_sessions.py` — see Testing / QA section.

## Integration & Edge Cases

- **Idempotent start:** Calling `POST /sessions/start` twice without stopping must return the *existing* session on the second call (same `id`), not create a duplicate.
- **No cross-user data:** `get_active_session` always filters by `user_id` extracted from JWT — never returns another user's session.
- **`elapsed_minutes` on schema serialisation:** Because `SessionLog.elapsed_minutes` is a Python `@property`, the Pydantic schema must use `model_config = ConfigDict(from_attributes=True)` to pick it up. Verify this works in tests.
- **DB migration on existing dev.db:** The `session_logs` table is additive — no existing tables are altered. Still: snapshot `data/dev.db` to `data/dev.db.bak` before running `alembic upgrade head`.
- **Async session:** All DB calls use `AsyncSession` + `await db.execute(select(...))` pattern consistent with the rest of the codebase.

## Acceptance Criteria

1. `GET /sessions/active` with a valid JWT and no active session returns `200` with body `null`.
2. `POST /sessions/start` with `{ "taskName": "UI Redesign", "goalMinutes": 60 }` returns `201` with a body containing `id`, `taskName: "UI Redesign"`, `goalMinutes: 60`, `startedAt` (ISO datetime string), `endedAt: null`, and `elapsedMinutes >= 0`.
3. Calling `POST /sessions/start` again without stopping returns `201` (or `200`) with the **same `id`** as the first call.
4. `GET /sessions/active` after a start returns the active session with `elapsedMinutes >= 0`.
5. `POST /sessions/stop` returns `200` with `endedAt` non-null and `elapsedMinutes >= 0`.
6. `GET /sessions/active` after a stop returns `200` with body `null`.
7. `POST /sessions/start` without a JWT returns `401`.
8. `POST /sessions/stop` when no session is active returns `404` with `"No active session"` in the detail.
9. `POST /sessions/start` with blank `taskName` returns `400`.
10. `GET /stats/flow-state` and all pre-existing endpoints still return correct responses after the migration (regression check).

## Testing / QA

### Automated tests — `code/backend/tests/test_sessions.py`

```python
# pytest fixtures: client, auth_headers (reuse from conftest.py)

def test_active_session_empty(client, auth_headers):
    r = client.get("/sessions/active", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() is None

def test_start_session(client, auth_headers):
    r = client.post("/sessions/start", json={"taskName": "UI Redesign", "goalMinutes": 60}, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["taskName"] == "UI Redesign"
    assert data["endedAt"] is None
    assert data["elapsedMinutes"] >= 0

def test_start_idempotent(client, auth_headers):
    r1 = client.post("/sessions/start", json={"taskName": "UI Redesign"}, headers=auth_headers)
    r2 = client.post("/sessions/start", json={"taskName": "UI Redesign"}, headers=auth_headers)
    assert r1.json()["id"] == r2.json()["id"]

def test_stop_session(client, auth_headers):
    client.post("/sessions/start", json={"taskName": "UI Redesign"}, headers=auth_headers)
    r = client.post("/sessions/stop", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["endedAt"] is not None

def test_stop_no_session_404(client, auth_headers):
    r = client.post("/sessions/stop", headers=auth_headers)
    assert r.status_code == 404

def test_start_no_auth_401(client):
    r = client.post("/sessions/start", json={"taskName": "x"})
    assert r.status_code == 401

def test_start_blank_name_400(client, auth_headers):
    r = client.post("/sessions/start", json={"taskName": ""}, headers=auth_headers)
    assert r.status_code == 400
```

**Run command:**

```bash
cd code/backend
pytest tests/test_sessions.py -v
```

### Manual QA checklist

1. Start backend: `uvicorn app.main:app --reload`
2. `POST /login` → copy token
3. `GET /sessions/active` → expect `null`
4. `POST /sessions/start` with `{"taskName":"UI Redesign","goalMinutes":60}` → expect `201` with session object
5. Wait 10 seconds; `GET /sessions/active` → `elapsedMinutes` should be ≥ 0 (possibly 0 for short waits, confirmed positive after 60+ s)
6. `POST /sessions/start` again → same `id` returned
7. `POST /sessions/stop` → `endedAt` populated
8. `GET /sessions/active` → `null`
9. `POST /sessions/stop` again → `404`
10. Run full existing test suite: `pytest tests/ -v` — all prior tests still pass

## Files touched

- [code/backend/app/models/session_log.py](../../../../code/backend/app/models/session_log.py) *(new)*
- [code/backend/app/services/session_service.py](../../../../code/backend/app/services/session_service.py) *(new)*
- [code/backend/app/api/sessions.py](../../../../code/backend/app/api/sessions.py) *(new)*
- [code/backend/app/main.py](../../../../code/backend/app/main.py)
- [code/backend/app/db/base.py](../../../../code/backend/app/db/base.py)
- [code/backend/tests/test_sessions.py](../../../../code/backend/tests/test_sessions.py) *(new)*
- `alembic/versions/<hash>_add_session_logs.py` *(generated)*

## Estimated effort

1–2 dev days

## Concurrency & PR strategy

- **Blocking steps:** None — this step has no dependencies and can be started immediately.
- **Merge Readiness: false** *(flip to `true` when all Acceptance Criteria pass and tests are green)*
- Suggested branch: `phase-2-2/step-1-session-model`

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Alembic migration breaks existing `dev.db` | **BEFORE MERGE:** snapshot `data/dev.db` → `data/dev.db.bak`; test migration on the snapshot copy first |
| `elapsed_minutes` @property not serialised by Pydantic | Use `model_config = ConfigDict(from_attributes=True)`; assert value in tests |
| Duplicate active sessions if race condition | Service layer checks for active session within the same transaction; SQLite single-writer prevents true concurrency issues in dev |
| `user_id` column missing on `session_logs` breaks user isolation | Index `user_id` in model; all service queries filter by it — assert in tests |

## References

- [PDD.md — §3.1 Task Schema](../PDD.md)
- [code/backend/app/models/task.py](../../../../code/backend/app/models/task.py) *(pattern reference)*
- [code/backend/app/api/tasks.py](../../../../code/backend/app/api/tasks.py) *(pattern reference)*
- [master.md](./master.md)

## Author Checklist

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/` (happy path + validation)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected
