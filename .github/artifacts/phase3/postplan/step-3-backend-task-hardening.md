# Step 3 — Backend Task Hardening

## Purpose

Add `user_id` scoping to the Task model, create a proper `TaskCreate` schema, add field validation, and update all task endpoints to be user-scoped — closing the critical data-isolation gap.

## Deliverables

- `user_id` column on the `Task` SQLAlchemy model with foreign key to `users.id`.
- Data migration script to backfill existing tasks.
- `TaskCreate` Pydantic schema (excludes `id`, `created_at`, `updated_at`).
- Field validators on `TaskCreate` and `TaskUpdate` for `name` and `priority`.
- All task endpoints (`list`, `create`, `update`, `delete`) filter/set `user_id` from JWT.
- New and updated backend tests for user scoping and validation.

## Primary files to change (required)

- [code/backend/app/models/task.py](code/backend/app/models/task.py)
- [code/backend/app/api/tasks.py](code/backend/app/api/tasks.py)
- [code/backend/tests/test_api.py](code/backend/tests/test_api.py)
- [code/backend/scripts/migrate_task_user_id.py](code/backend/scripts/migrate_task_user_id.py) (new file)

## Detailed implementation steps

### 3.1 — Add `user_id` to Task model

1. In [code/backend/app/models/task.py](code/backend/app/models/task.py), add to the `Task` SQLAlchemy class:
   ```python
   user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
   ```
2. Add `user_id` to `TaskSchema` as `user_id: str | None = None` so read responses include it.
3. Add `user_id` to `TaskUpdate` as `user_id: str | None = None` (but it should be protected from overwrite in the update handler — add to `_protect_from_none` set).

### 3.2 — Create `TaskCreate` schema

1. In [code/backend/app/models/task.py](code/backend/app/models/task.py), add a new Pydantic model:
   ```python
   class TaskCreate(CamelModel):
       name: str
       priority: str | None = None
       tags: str | None = None
       is_completed: bool = False
       deadline: datetime | None = None
       notes: str | None = None
   ```
2. Add field validators (see 3.3).

### 3.3 — Add field validators

1. Add to `TaskCreate`:
   ```python
   @field_validator("name")
   @classmethod
   def name_not_empty(cls, v: str) -> str:
       v = v.strip()
       if not v:
           raise ValueError("name must not be empty")
       if len(v) > 256:
           raise ValueError("name must be <= 256 characters")
       return v

   @field_validator("priority")
   @classmethod
   def priority_valid(cls, v: str | None) -> str | None:
       if v is None:
           return v
       allowed = {"High", "Medium", "Low"}
       if v not in allowed:
           raise ValueError(f"priority must be one of {allowed}")
       return v
   ```
2. Add the same validators to `TaskUpdate` (with `None` pass-through for optionals, same pattern as `ManualReportUpdate`).

### 3.4 — Update task endpoints

1. In [code/backend/app/api/tasks.py](code/backend/app/api/tasks.py):
   - `list_tasks`: change `select(Task)` to `select(Task).where(Task.user_id == user)`.
   - `create_task`: change parameter type from `TaskSchema` to `TaskCreate`. Set `user_id=user` when constructing the `Task` instance. Remove the `id=payload.id or None` line (IDs are always server-generated).
   - `update_task`: add a check `if result.user_id != user: raise HTTPException(403)`. Add `"user_id"` to `_protect_from_none`.
   - `delete_task`: add a check `if result.user_id != user: raise HTTPException(403)`.
2. Import `TaskCreate` alongside `TaskSchema` and `TaskUpdate`.

### 3.5 — Migration script

1. Create [code/backend/scripts/migrate_task_user_id.py](code/backend/scripts/migrate_task_user_id.py):
   - Connect to the SQLite database at `data/dev.db`.
   - If the `user_id` column does not exist on `tasks`, add it via `ALTER TABLE tasks ADD COLUMN user_id VARCHAR(36)`.
   - Query the first user from `users` table.
   - Run `UPDATE tasks SET user_id = ? WHERE user_id IS NULL`.
   - Print summary of migrated rows.
2. Script should be idempotent (safe to run multiple times).

### 3.6 — Update tests

1. In [code/backend/tests/test_api.py](code/backend/tests/test_api.py):
   - Update the `create_task` test helper/fixture to use the new `TaskCreate` schema shape (no `id`, `createdAt`, `updatedAt`).
   - Add test: `test_create_task_empty_name_rejected` — POST `/tasks/` with `{"name": ""}` → 422.
   - Add test: `test_create_task_invalid_priority_rejected` — POST `/tasks/` with `{"name": "Test", "priority": "Critical"}` → 422.
   - Add test: `test_list_tasks_user_scoped` — confirm tasks created by user A are not visible to user B (if multi-user test fixtures exist, otherwise note as future).
   - Ensure existing task CRUD tests still pass with the updated schema.

## Integration & Edge Cases

- **Database migration:** The `ALTER TABLE` approach works for SQLite dev. Production (PostgreSQL) would need `ALTER TABLE tasks ADD COLUMN user_id VARCHAR(36) NOT NULL DEFAULT ''` followed by backfill and constraint addition.
- **Existing dev.db:** If `data/dev.db` already has tasks with no `user_id`, those rows will fail new queries until the migration script is run. The step's pre-merge checklist requires running the script.
- **BEFORE MERGE:** Back up `data/dev.db` → `data/dev.db.bak`. Run `python scripts/migrate_task_user_id.py`. Follow atomic-write pattern.
- **`create_all` behavior:** SQLAlchemy `create_all` will create the column for fresh databases. Existing databases need the migration script.

## Acceptance Criteria (required)

1. `Task` model includes a `user_id` column (`String(36)`, `nullable=False`, indexed).
2. `POST /tasks/` accepts `TaskCreate` schema (no `id`, `createdAt`, `updatedAt` fields accepted).
3. `POST /tasks/` with `{"name": ""}` returns 422.
4. `POST /tasks/` with `{"name": "Test", "priority": "Critical"}` returns 422.
5. `POST /tasks/` with `{"name": "Valid Task", "priority": "High"}` returns 201 with `userId` in the response.
6. `GET /tasks/` only returns tasks belonging to the authenticated user.
7. `PUT /tasks/{id}` returns 403 if the task belongs to a different user.
8. `DELETE /tasks/{id}` returns 403 if the task belongs to a different user.
9. Migration script successfully backfills existing tasks with the dev user's ID.
10. `pytest -q` passes all existing + new tests.

## Testing / QA (required)

**Automated:**
```bash
cd code/backend && pytest -q tests/test_api.py -v
```

New tests to add in [code/backend/tests/test_api.py](code/backend/tests/test_api.py):
- `test_create_task_with_valid_data` — 201, response includes `userId`.
- `test_create_task_empty_name_rejected` — 422.
- `test_create_task_invalid_priority_rejected` — 422.
- `test_list_tasks_user_scoped` — tasks not leaked across users (if fixture supports it).
- `test_update_task_wrong_user_rejected` — 403 (if fixture supports it).
- `test_delete_task_wrong_user_rejected` — 403 (if fixture supports it).

**Manual QA checklist:**
1. Back up `data/dev.db`.
2. Run migration: `python scripts/migrate_task_user_id.py`.
3. Start backend: `uvicorn app.main:app --reload`.
4. `curl -X POST localhost:8000/tasks/ -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"name":"Test","priority":"High"}'` → 201 with `userId` in response.
5. `curl -X POST localhost:8000/tasks/ -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"name":""}'` → 422.

## Files touched (repeat for reviewers)

- [code/backend/app/models/task.py](code/backend/app/models/task.py)
- [code/backend/app/api/tasks.py](code/backend/app/api/tasks.py)
- [code/backend/tests/test_api.py](code/backend/tests/test_api.py)
- [code/backend/scripts/migrate_task_user_id.py](code/backend/scripts/migrate_task_user_id.py) (new)

## Estimated effort

1–2 dev days

## Concurrency & PR strategy

- Suggested branch: `phase-3/step-3-backend-task-hardening`
- Blocking steps: None (this is the root of serial Group B)
- Merge Readiness: false
- Steps 4 and 5 are blocked on this step.

## Risks & Mitigations

- **Risk:** Existing dev.db breaks after model change without migration. **Mitigation:** Migration script is idempotent; pre-merge backup required.
- **Risk:** Existing tests assume `TaskSchema` for creation. **Mitigation:** Update test fixtures as part of this step.

## References

- [Phase 3 Final Report — "Global tasks data leak"](../summary/final-report.md)
- [code/backend/app/models/manual_report.py](code/backend/app/models/manual_report.py) — reference pattern for `Create` schema with validators.
- [PDD — Task Schema](../../PDD.md)

## Author Checklist (must complete before PR)

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/` (happy path + validation)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected
