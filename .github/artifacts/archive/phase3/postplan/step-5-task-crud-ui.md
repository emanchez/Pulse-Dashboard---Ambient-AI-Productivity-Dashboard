# Step 5 — Task CRUD UI

## Purpose

Build a task management interface on the tasks page so users can create, edit, and delete tasks — the core missing functionality flagged in user observations.

## Deliverables

- "Create Task" button accessible from the tasks page.
- Task creation form (modal or inline) with fields: name, priority, deadline, notes, tags.
- Inline or modal editing of existing tasks.
- Delete action with confirmation.
- Completed toggle on tasks.
- Proper empty state in `TaskQueueTable` when no tasks exist (replace skeleton loaders with a CTA).

## Primary files to change (required)

- [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx)
- [code/frontend/components/dashboard/TaskQueueTable.tsx](code/frontend/components/dashboard/TaskQueueTable.tsx)
- [code/frontend/components/TaskBoard.tsx](code/frontend/components/TaskBoard.tsx) (integrate and restyle, or remove if building fresh)
- New file (if needed): `code/frontend/components/tasks/TaskForm.tsx` or similar

## Detailed implementation steps

### Approach decision

The implementer may choose one of two approaches:

**Option A — Integrate existing `TaskBoard.tsx`:**
1. Import `TaskBoard` in [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx).
2. Restyle `TaskBoard.tsx` from light-mode (`bg-rose-50`, `bg-amber-50`, `bg-sky-50`, `bg-white`, `text-gray-*`) to dark theme (`bg-slate-800`, `bg-slate-900`, `text-white`, `text-slate-300`, `border-slate-600`, etc.) matching existing dark component patterns.
3. Fix the input elements inside `TaskBoard.tsx` that have the same white-on-white issue (`border-gray-300` without explicit text/bg colors).
4. Wire the `onSave` callback to refresh the task list on the page.
5. Add a delete button to each task row (call `deleteTask` from `api.ts`).

**Option B — Build fresh task management UI:**
1. Create a `TaskForm` modal component (similar structure to `ReportForm.tsx`).
2. Add a "Create Task" button to the tasks page that opens the modal.
3. Add edit/delete actions to each row in `TaskQueueTable`.
4. Wire `createTask`, `updateTask`, `deleteTask` from [code/frontend/lib/api.ts](code/frontend/lib/api.ts).

### Common requirements (both approaches)

1. The "Create Task" button should use the `TaskCreate` type from [code/frontend/lib/api.ts](code/frontend/lib/api.ts).
2. The edit flow should use the `TaskUpdate` type.
3. After any mutation (create/edit/delete), refresh the task list by re-calling `listTasks`.
4. In [code/frontend/components/dashboard/TaskQueueTable.tsx](code/frontend/components/dashboard/TaskQueueTable.tsx), replace the skeleton loader empty state with:
   ```tsx
   <div className="text-center py-8">
     <p className="text-slate-400 mb-4">No tasks yet</p>
     <button onClick={onCreateTask} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm">
       Create Your First Task
     </button>
   </div>
   ```
   (Pass an `onCreateTask` callback prop from the tasks page.)
5. Include client-side validation matching the backend: name required (non-empty), priority must be one of High/Medium/Low or null.
6. Display API errors to users (follow the pattern established in Step 2).
7. All form inputs must use dark theme styling (`bg-slate-900 border-slate-600 text-white`).

## Integration & Edge Cases

- No persistence changes (backend already handles CRUD).
- The task list refreshes via polling (every 60s) — ensure mutations trigger an immediate refresh in addition to the polling cycle.
- If `TaskBoard.tsx` is not used, consider deleting or archiving it to avoid dead code.
- The `BentoGrid` component's `tasks-dashboard` variant renders fixed grid slots — ensure the task CRUD UI fits within the existing layout or extends it.

## Acceptance Criteria (required)

1. A "Create Task" button is visible on `/tasks`.
2. Clicking "Create Task" opens a form with fields: name (required), priority (dropdown: High/Medium/Low), deadline (date picker), notes (textarea), tags (text input).
3. Submitting a valid task calls `POST /tasks/` and the new task appears in the list.
4. Submitting with an empty name shows a validation error.
5. Each task in the list has an edit action that opens a pre-populated form; saving calls `PUT /tasks/{id}`.
6. Each task in the list has a delete action with confirmation; deleting calls `DELETE /tasks/{id}`.
7. The completed toggle on a task calls `PUT /tasks/{id}` with updated `isCompleted`.
8. When no tasks exist, the table shows "No tasks yet" with a "Create Your First Task" CTA — not skeleton loaders.
9. All form inputs use dark theme styling (no white-on-white).
10. `npm run build` passes with zero errors.

## Testing / QA (required)

**Automated:**
```bash
cd code/frontend && npm run build
```

**Manual QA checklist:**
1. Navigate to `/tasks` with no tasks — confirm "No tasks yet" message and CTA button.
2. Click "Create Task" — confirm form opens with all fields.
3. Submit with empty name — confirm validation error.
4. Submit with name "Test Task" + priority "High" — confirm task appears in list.
5. Click edit on the new task — confirm form is pre-populated.
6. Change name to "Updated Task" and save — confirm list updates.
7. Click delete on the task — confirm confirmation dialog, then confirm task disappears.
8. Toggle completed on a task — confirm visual change and persistence on refresh.
9. All form inputs render with visible text on dark background.

## Files touched (repeat for reviewers)

- [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx)
- [code/frontend/components/dashboard/TaskQueueTable.tsx](code/frontend/components/dashboard/TaskQueueTable.tsx)
- [code/frontend/components/TaskBoard.tsx](code/frontend/components/TaskBoard.tsx) (modified or deleted)
- New file(s) if Option B is chosen

## Estimated effort

1–2 dev days

## Concurrency & PR strategy

- Suggested branch: `phase-3/step-5-task-crud-ui`
- Blocking steps:
  - Blocked until: `.github/artifacts/phase3/postplan/step-3-backend-task-hardening.md` (branch: `phase-3/step-3-backend-task-hardening`)
  - Blocked until: `.github/artifacts/phase3/postplan/step-4-type-sync-regen.md` (branch: `phase-3/step-4-type-sync-regen`)
- Merge Readiness: false

## Risks & Mitigations

- **Risk:** `TaskBoard.tsx` restyling is more work than building fresh. **Mitigation:** Implementer may choose either approach; acceptance criteria are the same.
- **Risk:** BentoGrid layout doesn't accommodate a task form. **Mitigation:** Use a modal overlay (same pattern as ReportForm) which bypasses grid constraints.

## References

- [User observations](./observations.txt) — "no way to add or edit tasks at the moment"
- [code/frontend/components/TaskBoard.tsx](code/frontend/components/TaskBoard.tsx) — existing (unused) task editing component
- [code/frontend/components/reports/ReportForm.tsx](code/frontend/components/reports/ReportForm.tsx) — reference modal + dark form pattern
- [Step 3 — Backend Task Hardening](./step-3-backend-task-hardening.md)
- [Step 4 — Type Sync Regen](./step-4-type-sync-regen.md)

## Author Checklist (must complete before PR)

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation) — N/A (frontend UI)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected — N/A
