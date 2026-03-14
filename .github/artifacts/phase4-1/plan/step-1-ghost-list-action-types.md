# Step 1 — Fix Ghost List Action Types

## Purpose

Fix the broken Ghost List feature by aligning the ActionLog middleware's `action_type` values with the semantic constants expected by `GhostListService`. Currently the middleware writes HTTP signatures (e.g. `"POST /tasks"`) but the ghost service filters on semantic types (e.g. `"TASK_CREATE"`). This mismatch causes the ghost list to never count task activity, classifying all old open tasks as "stale."

## Deliverables

- Updated `ActionLogMiddleware` to write semantic `action_type` values for task-related mutations.
- Updated `_TASK_ACTION_TYPES` tuple in `GhostListService` to match the new semantic types (or confirm they already match after the middleware fix).
- New/updated tests covering both the middleware action type mapping and the ghost list's ability to correctly classify tasks.

## Primary files to change

- [code/backend/app/middlewares/action_log.py](code/backend/app/middlewares/action_log.py) — Core fix: map HTTP method+path to semantic action types
- [code/backend/app/services/ghost_list_service.py](code/backend/app/services/ghost_list_service.py) — Verify `_TASK_ACTION_TYPES` alignment; may need minor adjustments
- [code/backend/tests/test_ghost_list.py](code/backend/tests/test_ghost_list.py) — Add/update tests for the new action type mapping
- [code/backend/tests/test_api.py](code/backend/tests/test_api.py) — Update any tests that assert on `action_type` format

## Detailed implementation steps

### 1.1 Define a semantic action type mapping in the middleware

Add a mapping function at the top of [code/backend/app/middlewares/action_log.py](code/backend/app/middlewares/action_log.py):

```python
_ACTION_TYPE_MAP: dict[tuple[str, str], str] = {
    ("POST", "/tasks"): "TASK_CREATE",
    ("PUT", "/tasks"): "TASK_UPDATE",
    ("DELETE", "/tasks"): "TASK_DELETE",
    ("POST", "/reports"): "REPORT_CREATE",
    ("PUT", "/reports"): "REPORT_UPDATE",
    ("DELETE", "/reports"): "REPORT_DELETE",
    ("PATCH", "/reports"): "REPORT_ARCHIVE",
    ("POST", "/system-states"): "SYSTEM_STATE_CREATE",
    ("PUT", "/system-states"): "SYSTEM_STATE_UPDATE",
    ("DELETE", "/system-states"): "SYSTEM_STATE_DELETE",
    ("POST", "/ai/accept-tasks"): "AI_ACCEPT_TASKS",
}
```

### 1.2 Create a helper to resolve the semantic action type

```python
def _resolve_action_type(method: str, path: str) -> str:
    """Map HTTP method + path prefix to a semantic action type.
    
    Falls back to 'METHOD /path' for unmapped routes.
    """
    parts = [p for p in path.split("/") if p]
    if not parts:
        return f"{method} {path}"
    
    # Build the resource prefix: /tasks, /reports, etc.
    resource = f"/{parts[0]}"
    
    return _ACTION_TYPE_MAP.get((method, resource), f"{method} {path}")
```

### 1.3 Update the `dispatch` method

Replace the line:
```python
action_type=f"{method} {path}",
```
with:
```python
action_type=_resolve_action_type(method, path),
```

Also update the `change_summary` to include the resolved action type for better readability:
```python
change_summary=f"{_resolve_action_type(method, path)} on {path} returned {response.status_code}",
```

### 1.4 Handle task completion detection

The current ghost service expects `"TASK_COMPLETE"` but a PUT to `/tasks/{id}` with `is_completed=True` is just a `TASK_UPDATE`. Two options:

**Option A (Recommended):** Remove `"TASK_COMPLETE"` from `_TASK_ACTION_TYPES` in the ghost service — a completed task has `is_completed=True` and is already filtered out by the `Task.is_completed == False` WHERE clause. The ghost list only cares about open tasks' action counts.

**Option B:** Parse the request body in the middleware to detect completion. This is heavyweight and violates the middleware's "fire-and-forget" pattern. **Not recommended.**

Update `_TASK_ACTION_TYPES` in [code/backend/app/services/ghost_list_service.py](code/backend/app/services/ghost_list_service.py):
```python
_TASK_ACTION_TYPES = (
    "TASK_CREATE", "TASK_UPDATE", "TASK_DELETE",
)
```

Remove `"TASK_COMPLETE"`, `"SESSION_START"`, `"SESSION_STOP"` — sessions are tracked via `SessionLog`, not `ActionLog`, and the ghost service should only count direct task mutations.

### 1.5 Update the `task_id` extraction for proper entity scoping

Currently `_extract_entity_id` returns the second URL segment, which for `/tasks/{uuid}` is the task UUID. For `/tasks` (POST, creating a new task), it correctly falls back to parsing the response body. No change needed here — just verify the behavior.

However, ensure that for non-task routes (e.g. `/reports/{id}`), the `task_id` column is set to `None` or the report ID (current behavior uses it as a generic entity ref). The ghost service already filters on `_TASK_ACTION_TYPES`, so non-task action types won't pollute the count. Document this clearly.

### 1.6 Update tests

In [code/backend/tests/test_ghost_list.py](code/backend/tests/test_ghost_list.py):
- Add a test that creates ActionLog entries with the **new** semantic types and verifies ghost list counts them.
- Add a test that creates ActionLog entries with the **old** HTTP signature types and verifies the ghost list ignores them (regression test for data created before this fix).

In [code/backend/tests/test_api.py](code/backend/tests/test_api.py):
- Update any assertions that check `action_type` to expect the new semantic format.

## Integration & Edge Cases

- **Existing ActionLog data:** Old entries with `"POST /tasks"` format will no longer match `_TASK_ACTION_TYPES`. This is acceptable — old data will simply not count toward ghost activity, causing old tasks to appear as "stale" (which is the conservative/correct behavior for tasks with no recent tracked activity).
- **Non-task routes:** `/reports`, `/system-states`, `/ai/accept-tasks` get their own semantic types but these don't affect ghost list since they're not in `_TASK_ACTION_TYPES`.
- **Auth action types:** `LOGIN_SUCCESS` and `LOGIN_FAILED` are written by `auth.py` directly (not via the middleware). No conflict.
- **Session actions:** `SESSION_START`/`SESSION_STOP` are written by session endpoints, not the middleware. The ghost service should not count them (they reflect work effort, but ghost detection is about task mutation pattern). Remove from `_TASK_ACTION_TYPES`.

## Acceptance Criteria

1. **AC-1:** After creating a task via `POST /tasks/`, the corresponding `ActionLog` entry has `action_type = "TASK_CREATE"` (not `"POST /tasks/"`).
2. **AC-2:** After updating a task via `PUT /tasks/{id}`, the `ActionLog` entry has `action_type = "TASK_UPDATE"`.
3. **AC-3:** After deleting a task via `DELETE /tasks/{id}`, the `ActionLog` entry has `action_type = "TASK_DELETE"`.
4. **AC-4:** `GET /stats/ghost-list` returns tasks with accurate `actionCount` values based on the new semantic types.
5. **AC-5:** A task with 0 task-related actions and `created_at > 14 days ago` appears in the ghost list with `ghostReason = "stale"`.
6. **AC-6:** A task with > 5 task-related actions and still open appears with `ghostReason = "wheel-spinning"`.
7. **AC-7:** Existing tests in `test_ghost_list.py` continue to pass.
8. **AC-8:** Manual verify: Create a task, update it 3 times, check ghost list — `actionCount` should be 4 (1 create + 3 updates).

## Testing / QA

### Tests to add/update

- **File:** [code/backend/tests/test_ghost_list.py](code/backend/tests/test_ghost_list.py)
  - `test_ghost_counts_semantic_action_types` — insert ActionLogs with `TASK_CREATE`, `TASK_UPDATE`; verify ghost list counts them.
  - `test_ghost_ignores_http_signature_types` — insert ActionLogs with `POST /tasks`; verify ghost list does NOT count them.
  - `test_ghost_ignores_session_action_types` — insert ActionLogs with `SESSION_START`; verify ghost list does NOT count them.

- **File:** [code/backend/tests/test_api.py](code/backend/tests/test_api.py)
  - Update `test_action_log_written_on_task_create` (or equivalent) to assert `action_type == "TASK_CREATE"`.

### Run commands
```bash
cd code/backend && python -m pytest tests/test_ghost_list.py tests/test_api.py -v
```

### Manual QA checklist
1. Start backend, log in, create a task via the UI or `curl`.
2. Query `action_logs` table directly: `SELECT action_type FROM action_logs ORDER BY timestamp DESC LIMIT 5;`
3. Verify the latest entry shows `TASK_CREATE` (not `POST /tasks/`).
4. Hit `GET /stats/ghost-list` — verify response shape and `actionCount` values.

## Files touched

- [code/backend/app/middlewares/action_log.py](code/backend/app/middlewares/action_log.py)
- [code/backend/app/services/ghost_list_service.py](code/backend/app/services/ghost_list_service.py)
- [code/backend/tests/test_ghost_list.py](code/backend/tests/test_ghost_list.py)
- [code/backend/tests/test_api.py](code/backend/tests/test_api.py)

## Estimated effort

1 dev day

## Concurrency & PR strategy

- **Suggested branch:** `phase-4.1/step-1-ghost-list-action-types`
- **Blocking steps:** None — this step is independent.
- **Merge Readiness:** false (pending implementation)
- No other step depends on this one (ghost list is a standalone feature).

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Old ActionLog data no longer counted by ghost list | Acceptable — old tasks appear "stale" which is the safe default. Document in release notes. |
| Middleware changes introduce latency | Mapping lookup is O(1) dict access; negligible. |
| `_extract_entity_id` returns report/state IDs in `task_id` column | Ghost service already filters on `_TASK_ACTION_TYPES` so non-task actions are excluded. |

## References

- [MVP Final Audit §2.1](../../MVP_FINAL_AUDIT.md) — Ghost List is Effectively Broken
- [PDD §4.3](../../PDD.md) — Sunday Synthesis / Ghost in the Machine
- [code/backend/app/middlewares/action_log.py](code/backend/app/middlewares/action_log.py)
- [code/backend/app/services/ghost_list_service.py](code/backend/app/services/ghost_list_service.py)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
