# Phase 3 Postplan — Group B Implementation Summary

**Date:** 2026-03-06  
**Steps:** 3, 4, 5 (Concurrency Group B — serial chain)  
**Branch convention:** `phase-3/step-<n>-<short-desc>`  
**Backend tests:** 75 passed (including 10 new task-hardening tests)  
**Frontend build:** `npm run build` — 0 TypeScript errors, 7/7 pages compiled

---

## Overview

This session covered the complete planning and implementation of Phase 3 Postplan Group B:
the serial chain that closes the critical task data-isolation gap, regenerates the TypeScript
client, and delivers the full task CRUD interface.

A discovery research pass was run first to audit the exact current state of every relevant
file before writing a single line of code. The implementer chose **Option B** (fresh modal
pattern) over restyling the dead-code `TaskBoard.tsx`.

---

## Planning Session

Before implementation, a comprehensive pre-implementation research pass documented:

- `Task` model: no `user_id`, no `TaskCreate`, no validators; `create_task` accepted full
  `TaskSchema` including client-set `id`; all 4 endpoints ignored the `user` param returned
  by `get_current_user` — tasks were globally shared.
- `ManualReport` was identified as the gold-standard pattern (user_id on model, separate
  Create schema, field validators, None pass-through on Update).
- Frontend: no `TaskCreate` type, `createTask`/`updateTask` both used the full `Task` type;
  `TaskQueueTable` was read-only with a shimmer skeleton empty state; `TaskBoard.tsx` was
  dead code (light theme, unused, fetched its own data).
- Approach decision: Option B — fresh `TaskForm` modal + wire actions into `TaskQueueTable`,
  then delete `TaskBoard.tsx`.

The full plan was detailed in the prior chat turn (steps 3.1–3.7, 4.1–4.5, 5.11–5.15) and
is reflected in the step documents at `.github/artifacts/phase3/postplan/`.

---

## Step 3 — Backend Task Hardening

### 3.1 — Task model (`code/backend/app/models/task.py`)

| Change | Detail |
|---|---|
| Added `user_id` column | `Mapped[str] = mapped_column(String(36), nullable=False, index=True)` |
| Added `user_id` to `TaskSchema` | `user_id: str \| None = None` — included in read responses |
| Added `TaskCreate` schema | New class, no `id`/`created_at`/`updated_at`, extends `CamelModel` |
| `TaskCreate` validators | `name`: strip, non-empty, ≤256 chars; `priority`: must be High/Medium/Low or None |
| `TaskUpdate.name` | Changed from required `str` to optional `str \| None = None` (true PATCH semantics, matching `ManualReportUpdate`) |
| `TaskUpdate` validators | Same validator pattern as `TaskCreate`, with None pass-through |
| `_ALLOWED_PRIORITIES` | Module-level constant `{"High", "Medium", "Low"}` shared by both validator sets |

### 3.2 — Task endpoints (`code/backend/app/api/tasks.py`)

| Endpoint | Change |
|---|---|
| `GET /tasks/` | `select(Task)` → `select(Task).where(Task.user_id == user)` |
| `POST /tasks/` | Input type `TaskSchema` → `TaskCreate`; sets `user_id=user`; removes `id=payload.id or None` |
| `PUT /tasks/{id}` | Ownership check: `if result.user_id != user: raise HTTPException(403)`; `user_id` added to `_protect_from_none`; None values in payload now skipped unconditionally (safe for optional fields) |
| `DELETE /tasks/{id}` | Ownership check: `if result.user_id != user: raise HTTPException(403)` |

### 3.3 — Migration script (`code/backend/scripts/migrate_task_user_id.py`) — new file

Idempotent SQLite migration:
1. Checks `PRAGMA table_info(tasks)` — only runs `ALTER TABLE` if `user_id` column missing.
2. Queries first user from `users` table.
3. `UPDATE tasks SET user_id = ? WHERE user_id IS NULL`.
4. Prints row count and exits.

Ran successfully on `dev.db`: backfilled 3 existing tasks. Pre-migration backup saved as
`data/dev.db.pre-step3.bak`.

### 3.4 — Test updates

**`code/backend/tests/conftest.py`:**
- Added `from app.models.task import Task  # noqa: F401` — ensures `tasks` table is
  registered with `Base.metadata` during `prepare_database`.
- Added `auth_headers_b` fixture — creates `testuser2`/`testpass2` and returns auth headers,
  enabling cross-user 403 tests.

**`code/backend/tests/test_api.py` — 9 new tests:**

| Test | Assertion |
|---|---|
| `test_create_task_with_valid_data` | 201, response contains `userId` |
| `test_create_task_empty_name_rejected` | 422 |
| `test_create_task_whitespace_name_rejected` | 422 |
| `test_create_task_invalid_priority_rejected` | 422 |
| `test_create_task_valid_priorities_accepted` | 201 for High, Medium, Low |
| `test_list_tasks_user_scoped` | User A's task not visible to user B |
| `test_update_task_wrong_user_rejected` | 403 |
| `test_delete_task_wrong_user_rejected` | 403 |

**`pytest -q` result: 75 passed, 17 warnings** (all existing 66 tests + 9 new).

---

## Step 4 — TypeScript Client Regeneration

Backend started on port 8001 with Step 3 changes. Generation script run:
```bash
OPENAPI_URL=http://127.0.0.1:8001/openapi.json bash lib/generate-client.sh \
  http://127.0.0.1:8001/openapi.json lib/generated
```

### Generated output (`code/frontend/lib/generated/types.gen.ts`)

| Type | Change |
|---|---|
| `TaskCreate` | New — fields: `name`, `priority?`, `tags?`, `isCompleted?`, `deadline?`, `notes?` |
| `TaskSchema` | Added `userId?: string \| null` |
| `TaskUpdate` | `name` is now `string \| null` (optional) — matches backend |
| `index.ts` | `TaskCreate` now exported from the barrel |

### `code/frontend/lib/api.ts`

- Imported `TaskCreate` and `TaskUpdate` from `./generated`.
- Both re-exported from `api.ts`.
- `createTask(token, task: TaskCreate)` — now strongly typed.
- `updateTask(token, id, task: TaskUpdate)` — now strongly typed.

**`npm run build` — 0 errors** after regen.

---

## Step 5 — Task CRUD UI

### New file: `code/frontend/components/tasks/TaskForm.tsx`

Dark-theme modal following the `ReportForm.tsx` pattern:
- `mode: "create" | "edit"`, `task?`, `token`, `onClose`, `onSave` props.
- Fields: name (required, with inline validation error), priority (select: High/Medium/Low),
  deadline (date input), notes (textarea), tags (text).
- Client-side validation: empty name rejected with `text-red-400` error message.
- API error banner: `bg-red-500/20 text-red-400 border border-red-500/30`.
- `saving` state disables the submit button to prevent double-clicks.
- All inputs: `bg-slate-900 border-slate-600 text-white`.
- `createTask` / `updateTask` called from `lib/api.ts` with correct `TaskCreate`/`TaskUpdate` types.

### Updated: `code/frontend/components/dashboard/TaskQueueTable.tsx`

**New props:**
- `onCreateTask?: () => void`
- `onEdit?: (task: TaskSchema) => void`
- `onDelete?: (task: TaskSchema) => void`
- `onToggleComplete?: (task: TaskSchema) => void`

**Empty state:** Replaced shimmer skeleton with:
```
"No tasks yet" + "Create Your First Task" button (blue, calls onCreateTask)
```

**Table changes:**
- Added Priority column with color-coded labels (red/amber/green).
- Added completed checkbox column (calls `onToggleComplete`).
- Completed tasks show `line-through text-slate-400`.
- Added Actions column per row: Pencil (edit) and Trash2 (delete with `window.confirm`).
- Added "New Task" button in the table header (blue, calls `onCreateTask`).

### Updated: `code/frontend/app/tasks/page.tsx`

- Imports: `TaskForm`, `deleteTask`, `updateTask`, `Plus` icon, `TaskUpdate` type.
- `showTaskForm: boolean`, `editingTask: Task | null` state added.
- `refreshTasks()` helper: re-fetches and sets task list.
- `handleOpenCreate()` — clears `editingTask`, opens form.
- `handleEdit(task)` — sets `editingTask`, opens form in edit mode.
- `handleDelete(task)` — calls `deleteTask`, then `refreshTasks`.
- `handleToggleComplete(task)` — calls `updateTask({ isCompleted: !task.isCompleted })`, then `refreshTasks`.
- `handleFormSave()` — closes modal, clears editing state, calls `refreshTasks`.
- `row2C` placeholder replaced with a functional "Create Task" button card.
- `TaskQueueTable` wired with all four callbacks.
- `TaskForm` modal rendered conditionally when `showTaskForm` is true.

### Deleted: `code/frontend/components/TaskBoard.tsx`

Confirmed no imports across the codebase (only referenced in `README.md` and the build
cache). The component was light-themed dead code superseded by the new `TaskForm` approach.

**Final `npm run build` — 0 TypeScript errors, 7/7 pages compiled.**

---

## Files Changed

| File | Change type |
|---|---|
| `code/backend/app/models/task.py` | Modified — `user_id` column, `TaskCreate` schema, validators, `TaskUpdate` optional name |
| `code/backend/app/api/tasks.py` | Modified — user-scoped queries, ownership checks, `TaskCreate` input type |
| `code/backend/tests/conftest.py` | Modified — `Task` model import, `auth_headers_b` fixture |
| `code/backend/tests/test_api.py` | Modified — 9 new task tests |
| `code/backend/scripts/migrate_task_user_id.py` | **New** — idempotent SQLite migration |
| `code/frontend/lib/generated/types.gen.ts` | Regenerated — `TaskCreate`, `userId` in `TaskSchema` |
| `code/frontend/lib/generated/index.ts` | Regenerated — `TaskCreate` in barrel |
| `code/frontend/lib/api.ts` | Modified — `TaskCreate`/`TaskUpdate` imports, re-exports, function signatures |
| `code/frontend/components/tasks/TaskForm.tsx` | **New** — dark-theme task CRUD modal |
| `code/frontend/components/dashboard/TaskQueueTable.tsx` | Modified — actions column, empty state, priority column |
| `code/frontend/app/tasks/page.tsx` | Modified — CRUD handlers, form modal, "Create Task" quick action |
| `code/frontend/components/TaskBoard.tsx` | **Deleted** — confirmed unused dead code |

---

## Phase Acceptance Criteria — Group B Status

| Criterion | Status |
|---|---|
| `Task` model has `user_id` column (`String(36)`, `nullable=False`, indexed) | ✅ |
| `POST /tasks/` accepts `TaskCreate` (no `id`, `createdAt`, `updatedAt`) | ✅ |
| `POST /tasks/` with `{"name": ""}` → 422 | ✅ |
| `POST /tasks/` with invalid priority → 422 | ✅ |
| `POST /tasks/` valid → 201 with `userId` in response | ✅ |
| `GET /tasks/` returns only authenticated user's tasks | ✅ |
| `PUT /tasks/{id}` returns 403 for wrong user | ✅ |
| `DELETE /tasks/{id}` returns 403 for wrong user | ✅ |
| Migration script backfills existing tasks | ✅ (3 rows backfilled) |
| `TaskCreate` type in generated TypeScript client | ✅ |
| `TaskSchema` type includes `userId` | ✅ |
| `createTask()` accepts `TaskCreate` | ✅ |
| `updateTask()` accepts `TaskUpdate` | ✅ |
| "Create Task" button visible on `/tasks` | ✅ |
| Task creation form with all required fields | ✅ |
| Empty name → client-side validation error | ✅ |
| Valid task → appears in list | ✅ |
| Edit action → pre-populated form, `PUT /tasks/{id}` | ✅ |
| Delete action → confirmation, `DELETE /tasks/{id}` | ✅ |
| Completed toggle → `PUT /tasks/{id}` | ✅ |
| Empty state shows "No tasks yet" CTA (not skeleton) | ✅ |
| All form inputs are dark-themed (no white-on-white) | ✅ |
| `pytest -q` — 75 passed | ✅ |
| `npm run build` — 0 TypeScript errors | ✅ |
