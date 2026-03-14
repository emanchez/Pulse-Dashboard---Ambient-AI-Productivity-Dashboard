# Step 2 — Task Update: Allow Clearing Nullable Fields

## Purpose

Fix the task update endpoint so that nullable fields (`deadline`, `notes`, `tags`, `priority`) can be explicitly set to `null`. Currently the update handler skips all `None` values via `if v is None: continue`, making it impossible for users to remove a deadline or clear notes once set.

## Deliverables

- Updated `PUT /tasks/{task_id}` handler to distinguish between "field not sent" (excluded from payload) and "field explicitly set to null" (included with value `null`).
- Updated `TaskUpdate` schema usage to leverage `model_dump(exclude_unset=True)` for correct partial-update semantics.
- New tests verifying that nullable fields can be cleared.

## Primary files to change

- [code/backend/app/api/tasks.py](code/backend/app/api/tasks.py) — Update handler logic
- [code/backend/app/models/task.py](code/backend/app/models/task.py) — Verify `TaskUpdate` schema supports nullable fields (likely already correct)
- [code/backend/tests/test_api.py](code/backend/tests/test_api.py) — Add tests for null-clearing behavior

## Detailed implementation steps

### 2.1 Understand the current bug

In [code/backend/app/api/tasks.py](code/backend/app/api/tasks.py), the update handler does:

```python
for k, v in payload.model_dump().items():
    if not hasattr(result, k):
        continue
    if v is None and k in _protect_from_none:
        continue
    if v is None:  # ← BUG: skips ALL None values, including intentional clears
        continue
    setattr(result, k, v)
```

`model_dump()` returns **all** fields with their defaults (including `None` for unset optional fields). This means there's no way to distinguish "user didn't send this field" from "user sent this field as null."

### 2.2 Fix: Use `model_dump(exclude_unset=True)`

Replace the update logic with:

```python
# Only iterate fields the client explicitly included in the request body.
# This distinguishes "not sent" (excluded) from "sent as null" (included with None value).
updates = payload.model_dump(exclude_unset=True)

# Fields that must never be overwritten — not part of TaskUpdate schema anyway,
# but guard defensively.
_PROTECTED_FIELDS = {"id", "created_at", "updated_at", "user_id"}

for field, value in updates.items():
    if field in _PROTECTED_FIELDS:
        continue
    if not hasattr(result, field):
        continue
    setattr(result, field, value)
```

Key change: `exclude_unset=True` means only fields the client explicitly sent in the JSON body appear in the dict. If the client sends `{"deadline": null}`, `deadline` will be in the dict with value `None` and will be set on the model. If the client sends `{"name": "new name"}` without `deadline`, then `deadline` is excluded entirely and left unchanged.

### 2.3 Verify TaskUpdate schema

Check that [code/backend/app/models/task.py](code/backend/app/models/task.py) `TaskUpdate` has all nullable fields as `Optional` with no default (or `default=None`). The existing schema likely already supports this — verify:

```python
class TaskUpdate(CamelModel):
    name: str | None = None
    priority: str | None = None
    tags: str | None = None
    is_completed: bool | None = None
    deadline: datetime | None = None
    notes: str | None = None
```

All fields should be `Optional` with `default=None`. This is correct because Pydantic's `exclude_unset=True` tracks whether a field was explicitly provided regardless of its default.

### 2.4 Move `_PROTECTED_FIELDS` to module level

Move the set out of the function body to avoid re-creation on every request:

```python
# Module level, above the router
_PROTECTED_FIELDS = frozenset({"id", "created_at", "updated_at", "user_id"})
```

### 2.5 Frontend: Update TaskForm to send explicit nulls

In [code/frontend/components/tasks/TaskForm.tsx](code/frontend/components/tasks/TaskForm.tsx), the edit mode currently sends `undefined` for empty fields:

```typescript
const data: TaskUpdate = {
    name: name.trim(),
    priority: priority || undefined,  // ← sends undefined (field omitted)
    deadline: deadline ? new Date(deadline).toISOString() : undefined,
    ...
}
```

For the "clear" behavior to work, the frontend must send `null` instead of `undefined` when the user clears a field. Change to:

```typescript
const data: TaskUpdate = {
    name: name.trim(),
    priority: priority || null,      // ← sends null (field included, value null)
    deadline: deadline ? new Date(deadline).toISOString() : null,
    notes: notes.trim() || null,
    tags: tags.trim() || null,
}
```

**Important:** `JSON.stringify` omits `undefined` properties but includes `null` ones, which is exactly the behavior we need.

### 2.6 Add tests

Add tests to [code/backend/tests/test_api.py](code/backend/tests/test_api.py):

```python
def test_task_update_clears_deadline(client, auth_headers):
    # Create task with deadline
    task = client.post("/tasks/", json={"name": "Test", "deadline": "2026-04-01T00:00:00"}, headers=auth_headers).json()
    assert task["deadline"] is not None
    
    # Clear deadline
    updated = client.put(f"/tasks/{task['id']}", json={"deadline": None}, headers=auth_headers).json()
    assert updated["deadline"] is None

def test_task_update_clears_notes(client, auth_headers):
    task = client.post("/tasks/", json={"name": "Test", "notes": "Important"}, headers=auth_headers).json()
    updated = client.put(f"/tasks/{task['id']}", json={"notes": None}, headers=auth_headers).json()
    assert updated["notes"] is None

def test_task_update_preserves_unset_fields(client, auth_headers):
    task = client.post("/tasks/", json={"name": "Test", "priority": "High", "notes": "Keep"}, headers=auth_headers).json()
    # Only update name — priority and notes should be preserved
    updated = client.put(f"/tasks/{task['id']}", json={"name": "Renamed"}, headers=auth_headers).json()
    assert updated["priority"] == "High"
    assert updated["notes"] == "Keep"
```

## Integration & Edge Cases

- **`name` field:** Must never be set to `null` (it's required). The `TaskUpdate` schema has `name: str | None = None`. If a client sends `{"name": null}`, the model column is `NOT NULL` which would cause a DB error. Add a guard: if `name` is explicitly null, skip it or raise 422.
- **`is_completed` field:** Setting to `null` doesn't make sense (boolean column). The ORM column is `NOT NULL` with a default. Add `is_completed` to `_PROTECTED_FROM_NULL` (distinct from `_PROTECTED_FIELDS`).
- **No persistence change:** This is a logic-only fix. No schema or migration needed.

## Acceptance Criteria

1. **AC-1:** `PUT /tasks/{id}` with body `{"deadline": null}` sets the task's deadline to `null` (200 response, `deadline: null`).
2. **AC-2:** `PUT /tasks/{id}` with body `{"notes": null}` sets the task's notes to `null`.
3. **AC-3:** `PUT /tasks/{id}` with body `{"tags": null}` sets the task's tags to `null`.
4. **AC-4:** `PUT /tasks/{id}` with body `{"priority": null}` sets the task's priority to `null`.
5. **AC-5:** `PUT /tasks/{id}` with body `{"name": "New Name"}` (no other fields) preserves all other fields unchanged.
6. **AC-6:** `PUT /tasks/{id}` with body `{"name": null}` either skips the null (preserves existing name) or returns 422.
7. **AC-7:** Frontend TaskForm in edit mode sends `null` for cleared optional fields.
8. **AC-8:** Existing task update tests continue to pass.

## Testing / QA

### Tests to add

- **File:** [code/backend/tests/test_api.py](code/backend/tests/test_api.py)
  - `test_task_update_clears_deadline` — Create with deadline, PUT with `null`, verify cleared.
  - `test_task_update_clears_notes` — Create with notes, PUT with `null`, verify cleared.
  - `test_task_update_clears_tags` — Create with tags, PUT with `null`, verify cleared.
  - `test_task_update_clears_priority` — Create with priority, PUT with `null`, verify cleared.
  - `test_task_update_preserves_unset_fields` — PUT with only `name`, verify other fields untouched.
  - `test_task_update_null_name_rejected` — PUT with `{"name": null}`, verify 422 or unchanged.

### Run commands
```bash
cd code/backend && python -m pytest tests/test_api.py -v -k "task_update"
```

### Manual QA checklist
1. Create a task with deadline, notes, tags, and priority via the UI.
2. Edit the task, clear the deadline field, save.
3. Verify the task now shows no deadline.
4. Repeat for notes, tags, and priority.

## Files touched

- [code/backend/app/api/tasks.py](code/backend/app/api/tasks.py)
- [code/frontend/components/tasks/TaskForm.tsx](code/frontend/components/tasks/TaskForm.tsx)
- [code/backend/tests/test_api.py](code/backend/tests/test_api.py)

## Estimated effort

0.5 dev days

## Concurrency & PR strategy

- **Suggested branch:** `phase-4.1/step-2-task-update-nullable-fields`
- **Blocking steps:** None — independent of all other steps.
- **Merge Readiness:** false (pending implementation)

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Frontend sends `null` for fields user didn't intend to clear | Only clear when the form field is explicitly empty; populated fields send their value |
| `name: null` causes DB constraint violation | Guard against null for required fields (name, is_completed) |

## References

- [MVP Final Audit §2.2](../../MVP_FINAL_AUDIT.md) — Task Update Cannot Clear Nullable Fields
- [code/backend/app/api/tasks.py](code/backend/app/api/tasks.py)
- [code/frontend/components/tasks/TaskForm.tsx](code/frontend/components/tasks/TaskForm.tsx)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
