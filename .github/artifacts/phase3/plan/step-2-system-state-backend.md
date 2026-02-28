# Step 2 — SystemState CRUD API

## Purpose

Build a full CRUD API for `SystemState` (Vacation/Leave scheduling) so users can create, view, edit, and delete scheduled pauses, enabling the existing `/stats/pulse` endpoint to dynamically reflect "SYSTEM PAUSED" status and the frontend to manage inactivity periods.

## Deliverables

- New `SystemStateCreate` and `SystemStateUpdate` Pydantic schemas in `code/backend/app/models/system_state.py`
- New `PaginatedSystemStatesResponse` schema
- New `code/backend/app/services/system_state_service.py` — business logic: create (validate dates, check overlaps), list, get active, update, delete
- New `code/backend/app/api/system_states.py` — 5 JWT-guarded, user-scoped endpoints
- Updated `code/backend/app/main.py` — register system-states router + model import
- Extended `code/backend/app/middlewares/action_log.py` — log mutations on `/system-states` paths
- New `code/backend/tests/test_system_states.py` — comprehensive test suite
- Updated `code/backend/app/schemas/__init__.py` — re-export new schemas

## Primary files to change (required)

- [code/backend/app/models/system_state.py](../../../../code/backend/app/models/system_state.py) *(modify — add create/update schemas)*
- [code/backend/app/services/system_state_service.py](../../../../code/backend/app/services/system_state_service.py) *(new)*
- [code/backend/app/api/system_states.py](../../../../code/backend/app/api/system_states.py) *(new)*
- [code/backend/app/main.py](../../../../code/backend/app/main.py) *(modify)*
- [code/backend/app/middlewares/action_log.py](../../../../code/backend/app/middlewares/action_log.py) *(modify)*
- [code/backend/app/schemas/__init__.py](../../../../code/backend/app/schemas/__init__.py) *(modify)*
- [code/backend/tests/test_system_states.py](../../../../code/backend/tests/test_system_states.py) *(new)*

## Detailed implementation steps

1. **Create `SystemStateCreate` schema** in `code/backend/app/models/system_state.py`:
   ```python
   class SystemStateCreate(CamelModel):
       mode_type: str           # required; must be "vacation" or "leave"
       start_date: datetime     # required
       end_date: datetime       # required; must be > start_date
       requires_recovery: bool = True
       description: str | None = None
   ```
   - Add Pydantic validators: `mode_type` must be in `{"vacation", "leave"}` (case-insensitive, normalized to lowercase), `end_date > start_date`.

2. **Create `SystemStateUpdate` schema**:
   ```python
   class SystemStateUpdate(CamelModel):
       mode_type: str | None = None
       start_date: datetime | None = None
       end_date: datetime | None = None
       requires_recovery: bool | None = None
       description: str | None = None
   ```
   - Validate `mode_type` if provided, and check `end_date > start_date` when both are present in the update.

3. **Update `SystemStateSchema`** (read DTO):
   - Add `model_config = ConfigDict(from_attributes=True)` for ORM support.
   - Add `created_at: datetime | None = None`, `updated_at: datetime | None = None` fields.

4. **Create `system_state_service.py`** in `code/backend/app/services/`:
   - `create_state(db, user_id, data: SystemStateCreate) -> SystemState`:
     - Validate no overlapping active state for the user: query for any existing `SystemState` where `user_id` matches AND date ranges overlap (`existing.start_date < data.end_date AND existing.end_date > data.start_date`). Raise `HTTPException(409, "Overlapping system state exists")` if found.
     - `mode_type` stored lowercase.
     - Insert and return.
   - `list_states(db, user_id) -> list[SystemState]`:
     - Return all states for user, ordered by `start_date DESC`.
   - `get_active_state(db, user_id) -> SystemState | None`:
     - Query where `user_id` matches, `start_date <= now`, and (`end_date IS NULL OR end_date >= now`), and `mode_type` in `("vacation", "leave")`.
     - Return first result or None.
   - `get_state(db, user_id, state_id) -> SystemState | None`:
     - Fetch by ID scoped to user.
   - `update_state(db, user_id, state_id, data: SystemStateUpdate) -> SystemState | None`:
     - Fetch scoped to user; apply non-None fields; validate overlap if dates changed.
   - `delete_state(db, user_id, state_id) -> bool`:
     - Fetch scoped to user; delete; return True/False.

5. **Create `system_states.py` router** in `code/backend/app/api/`:
   - `POST /system-states` → 201, body `SystemStateCreate`, response `SystemStateSchema`
   - `GET /system-states` → 200, response `list[SystemStateSchema]`
   - `GET /system-states/active` → 200, response `SystemStateSchema | None` (returns `null` when no active state)
   - `PUT /system-states/{state_id}` → 200, body `SystemStateUpdate`, response `SystemStateSchema`; 404 if not found
   - `DELETE /system-states/{state_id}` → 204; 404 if not found
   - All routes use `Depends(get_current_user)` from `code/backend/app/api/auth.py`
   - Router: `router = APIRouter(prefix="/system-states")`

6. **Update `main.py`**:
   - Add `from .api import system_states as system_states_router`
   - Add `app.include_router(system_states_router.router)`
   - Add `from .models.system_state import SystemState as _SystemState  # noqa: F401` to register model with Base.metadata (may already be imported indirectly via stats.py — verify and add explicit import).

7. **Extend `ActionLogMiddleware`**:
   - Add `/system-states` to the path matching in `dispatch`:
     ```python
     if (path.startswith("/tasks") or path.startswith("/reports") or path.startswith("/system-states")) and method in {"POST", "PUT", "DELETE", "PATCH"}:
     ```
   - Extract `state_id` from path segments for action log entries.

8. **Update `schemas/__init__.py`**:
   - Add re-exports: `SystemStateCreate`, `SystemStateUpdate`

9. **Verify `/stats/pulse` integration**:
   - The existing `GET /stats/pulse` in `code/backend/app/api/stats.py` already queries `SystemState` to determine `paused` status. Verify that system states created via the new CRUD endpoints are correctly picked up by the pulse query. This should work automatically since they share the same model and table.

10. **Write tests** in `code/backend/tests/test_system_states.py` — see Testing / QA section.

## Integration & Edge Cases

- **Overlap prevention:** Two vacation periods for the same user with overlapping date ranges are rejected with 409. The overlap check uses: `existing.start_date < new.end_date AND existing.end_date > new.start_date`.
- **Active state query:** Must match the same logic used in `GET /stats/pulse` (line-for-line: `start_date <= now`, `end_date IS NULL OR end_date >= now`, `mode_type IN ('vacation', 'leave')`). The pulse endpoint's existing behavior is the source of truth.
- **User scoping:** All queries filter by `user_id`. A user cannot see or modify another user's system states.
- **Null `end_date`:** If `end_date` is NULL, the state is considered indefinite (active forever until updated). The overlap check must handle this case.
- **`requires_recovery` flag:** Stored but not actively consumed until Phase 4 (AI re-entry suggestions). For now, it's just persisted.
- **DB migration:** `system_states` table already exists with all needed columns (including `user_id`). `create_all` is sufficient. No destructive changes.
- **BEFORE MERGE:** Snapshot `data/dev.db` to `data/dev.db.bak`.

## Acceptance Criteria

1. `POST /system-states` with `{ "modeType": "vacation", "startDate": "2026-03-01T00:00:00", "endDate": "2026-03-07T00:00:00", "description": "Spring break" }` returns `201` with JSON containing `id`, `modeType: "vacation"`, `startDate`, `endDate`, `requiresRecovery: true`, `userId`.
2. `POST /system-states` without JWT returns `401`.
3. `POST /system-states` with `endDate` before `startDate` returns `422`.
4. `POST /system-states` with `modeType: "invalid"` returns `422`.
5. `POST /system-states` with overlapping dates to an existing state returns `409`.
6. `GET /system-states` returns `200` with a list of all user's system states.
7. `GET /system-states/active` returns `200` with the currently active state when one exists; `null` when none.
8. `PUT /system-states/{id}` with `{ "description": "Extended" }` returns `200` with updated description.
9. `DELETE /system-states/{id}` returns `204`; subsequent `GET` returns `404`.
10. Creating a vacation state covering "now" causes `GET /stats/pulse` to return `silenceState: "paused"`.
11. Deleting that state causes `GET /stats/pulse` to revert to `engaged` or `stagnant`.
12. User A cannot access User B's system states.
13. `ActionLog` table contains entries for system-state mutations.
14. All existing tests pass with no regressions.

## Testing / QA

### Automated tests — `code/backend/tests/test_system_states.py`

```python
# Fixtures: client, auth_headers (reuse from conftest.py)
from datetime import datetime, timedelta

def _future(days=1):
    return (datetime.utcnow() + timedelta(days=days)).isoformat()

def _past(days=1):
    return (datetime.utcnow() - timedelta(days=days)).isoformat()

def test_create_system_state(client, auth_headers):
    r = client.post("/system-states", json={
        "modeType": "vacation",
        "startDate": _future(1),
        "endDate": _future(7),
        "description": "Spring break"
    }, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["modeType"] == "vacation"
    assert data["requiresRecovery"] is True

def test_create_no_auth(client):
    r = client.post("/system-states", json={
        "modeType": "vacation", "startDate": _future(1), "endDate": _future(7)
    })
    assert r.status_code == 401

def test_create_invalid_mode_type(client, auth_headers):
    r = client.post("/system-states", json={
        "modeType": "holiday", "startDate": _future(1), "endDate": _future(7)
    }, headers=auth_headers)
    assert r.status_code == 422

def test_create_end_before_start(client, auth_headers):
    r = client.post("/system-states", json={
        "modeType": "vacation", "startDate": _future(7), "endDate": _future(1)
    }, headers=auth_headers)
    assert r.status_code == 422

def test_create_overlapping(client, auth_headers):
    client.post("/system-states", json={
        "modeType": "vacation", "startDate": _future(10), "endDate": _future(15)
    }, headers=auth_headers)
    r = client.post("/system-states", json={
        "modeType": "leave", "startDate": _future(12), "endDate": _future(18)
    }, headers=auth_headers)
    assert r.status_code == 409

def test_list_states(client, auth_headers):
    r = client.get("/system-states", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_active_state_none(client, auth_headers):
    r = client.get("/system-states/active", headers=auth_headers)
    assert r.status_code == 200
    # may be null if no active state covers now

def test_get_active_state_exists(client, auth_headers):
    # Create a state covering now
    client.post("/system-states", json={
        "modeType": "vacation",
        "startDate": _past(1),
        "endDate": _future(1)
    }, headers=auth_headers)
    r = client.get("/system-states/active", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data is not None
    assert data["modeType"] == "vacation"

def test_update_state(client, auth_headers):
    create = client.post("/system-states", json={
        "modeType": "leave", "startDate": _future(20), "endDate": _future(25)
    }, headers=auth_headers)
    state_id = create.json()["id"]
    r = client.put(f"/system-states/{state_id}", json={
        "description": "Mental health break"
    }, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["description"] == "Mental health break"

def test_delete_state(client, auth_headers):
    create = client.post("/system-states", json={
        "modeType": "leave", "startDate": _future(30), "endDate": _future(35)
    }, headers=auth_headers)
    state_id = create.json()["id"]
    r = client.delete(f"/system-states/{state_id}", headers=auth_headers)
    assert r.status_code == 204

def test_pulse_reflects_active_state(client, auth_headers):
    """Creating a current vacation should make pulse return 'paused'."""
    client.post("/system-states", json={
        "modeType": "vacation",
        "startDate": _past(1),
        "endDate": _future(5)
    }, headers=auth_headers)
    r = client.get("/stats/pulse", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["silenceState"] == "paused"
```

### Manual QA checklist

1. Start backend: `uvicorn app.main:app --reload`
2. Login → get token
3. `POST /system-states` with vacation covering this week → verify 201
4. `GET /system-states/active` → verify returns the vacation
5. `GET /stats/pulse` → verify `silenceState` is `"paused"`
6. `DELETE /system-states/{id}` → verify 204
7. `GET /stats/pulse` → verify `silenceState` reverts
8. Attempt overlapping create → verify 409

## Files touched (repeat for reviewers)

- [code/backend/app/models/system_state.py](../../../../code/backend/app/models/system_state.py)
- [code/backend/app/services/system_state_service.py](../../../../code/backend/app/services/system_state_service.py)
- [code/backend/app/api/system_states.py](../../../../code/backend/app/api/system_states.py)
- [code/backend/app/main.py](../../../../code/backend/app/main.py)
- [code/backend/app/middlewares/action_log.py](../../../../code/backend/app/middlewares/action_log.py)
- [code/backend/app/schemas/__init__.py](../../../../code/backend/app/schemas/__init__.py)
- [code/backend/tests/test_system_states.py](../../../../code/backend/tests/test_system_states.py)

## Estimated effort

1–1.5 dev days

## Concurrency & PR strategy

- **Suggested branch:** `phase-3/step-2-system-state-backend`
- **Blocking steps:** `phase-3/step-0-tech-debt-cleanup` must be merged first.
- **Merge Readiness:** false
- Can be developed in parallel with Step 1 (ManualReport backend) after Step 0 merges.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Overlap check misses edge cases (NULL end_date, exact boundary) | Test with boundary conditions; handle NULL end_date as "infinity" |
| New system states break existing `GET /stats/pulse` test expectations | Review `test_stats.py` and update if needed; the pulse query logic doesn't change |
| `create_all` doesn't add columns to existing `system_states` table | Table schema is already correct (model was defined in Phase 2); verify with `pragma table_info(system_states)` |

## References

- [PDD.md — §3.4 SystemState](../../PDD.md)
- [architecture.md — §1 Data Schema](../../architecture.md)
- [agents.md — §2 Silence Gap Analysis (SystemState rules)](../../agents.md)
- [Phase 3 Master](./master.md)
- [Step 0 — Tech Debt](./step-0-tech-debt-cleanup.md)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
- [ ] Author signoff
