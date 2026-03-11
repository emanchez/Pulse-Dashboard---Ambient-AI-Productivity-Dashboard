# Step 2 — Frontend: Error Handling & Task ID Type Safety

## Purpose

Make `reports/page.tsx` resilient to partial fetch failures so a broken `/tasks/` response never silently empties the task-selection dropdown, and guard the `ReportForm.tsx` checkbox logic against `TaskSchema.id` being `null` or `undefined`.

---

## Deliverables

- Updated `code/frontend/app/reports/page.tsx` — `fetchAll` split into independent fetches; `handleAuthError` replaced with explicit error-state banner; loading spinner waits for both fetches to settle.
- Updated `code/frontend/components/reports/ReportForm.tsx` — `tasks` prop filtered to exclude items with a null or undefined `id`; `task.id` cast to `string` before use in `toggleTask` and `includes`.

---

## Primary files to change

- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx)
- [code/frontend/components/reports/ReportForm.tsx](../../../../code/frontend/components/reports/ReportForm.tsx)

---

## Detailed implementation steps

### 1. Split `fetchAll` and replace `handleAuthError` in `reports/page.tsx`

**File:** [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx)

**Current state (broken):**
```tsx
// Single Promise.all — one failure collapses both fetches
const [reportsRes, taskList] = await Promise.all([
  listReports(token, 0, 20),
  listTasks(token),
])
setReports(reportsRes.items)
setTasks(taskList)
// ...
} catch (err: any) {
  handleAuthError(err)  // swallows non-401 errors silently
}
```

**Required changes:**

1a. Add `fetchError` state above the existing state declarations:
```tsx
const [fetchError, setFetchError] = useState<string | null>(null)
```

1b. Remove `handleAuthError` entirely, or reduce it to only the `logout()` call (see 1c).

1c. Replace the `useEffect` `fetchAll` implementation with two independent `try/catch` blocks using `Promise.allSettled`:

```tsx
const fetchAll = async () => {
  setLoading(true)
  setFetchError(null)

  const [reportsResult, tasksResult] = await Promise.allSettled([
    listReports(token, 0, 20),
    listTasks(token),
  ])

  if (reportsResult.status === "fulfilled") {
    setReports(reportsResult.value.items)
    setTotalReports(reportsResult.value.total)
  } else {
    const msg = reportsResult.reason?.message ?? "Unknown error"
    if (msg.includes("401")) {
      logout()
      return
    }
    setFetchError(`Could not load reports: ${msg}`)
  }

  if (tasksResult.status === "fulfilled") {
    setTasks(tasksResult.value)
  } else {
    const msg = tasksResult.reason?.message ?? "Unknown error"
    if (msg.includes("401")) {
      logout()
      return
    }
    // Non-fatal: surface a banner; do not clear existing task list
    setFetchError(
      (prev) => prev
        ? `${prev} | Could not load tasks — task linking unavailable`
        : "Could not load tasks — task linking unavailable"
    )
  }

  setLoading(false)
}
```

Note: `setFetchError` above uses the functional updater form — the type must be `Dispatch<SetStateAction<string | null>>` for it to accept `(prev) => ...`. If simpler is preferred, store separate `reportError` and `taskError` states — the agent should choose whichever keeps the diff minimal.

1d. Render the error banner in the JSX, directly below the `<AppNavBar>` and above the main content area:
```tsx
{fetchError && (
  <div className="bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg px-4 py-3 text-sm mb-4">
    {fetchError}
  </div>
)}
```

---

### 2. Guard `task.id` nullability in `ReportForm.tsx`

**File:** [code/frontend/components/reports/ReportForm.tsx](../../../../code/frontend/components/reports/ReportForm.tsx)

**Current state (latent bug):**
```tsx
tasks.map((task) => (
  <label key={task.id} ...>
    <input
      type="checkbox"
      checked={selectedTaskIds.includes(task.id)}   // task.id: string|null|undefined
      onChange={() => toggleTask(task.id)}           // expects string
    />
```

**Required changes:**

2a. Directly above the `tasks.map(...)` render, derive a safe list:
```tsx
const safeTasks = tasks.filter((t): t is typeof t & { id: string } => t.id != null)
```

2b. Replace `tasks.map(...)` with `safeTasks.map(...)` — all other logic remains identical.

2c. Replace `tasks.length === 0` empty-state check with `safeTasks.length === 0`:
```tsx
{safeTasks.length === 0 ? (
  <p className="...">No tasks available</p>
) : (
  safeTasks.map((task) => (
    ...
  ))
)}
```

No changes to `toggleTask`, `selectedTaskIds`, or any other state — the type narrowing happens at the render boundary only.

---

## Integration & Edge Cases

- **`Promise.allSettled` availability:** Available in all modern browsers and Node.js 12.9+. No polyfill needed.
- **Loading state race:** `setLoading(false)` must be called only after both settled results have been processed. In the implementation above it is called at the end of `fetchAll`, after the `if/else` blocks — this is correct. Do not move it into `finally` unless you also handle the early `return` on 401.
- **`fetchError` functional updater:** If the TypeScript compiler complains about the `prev =>` pattern, fall back to two separate states (`reportsFetchError`, `tasksFetchError`) and conditionally render both banners — the acceptance criteria only require that the user sees a visible message.
- **Refresh after save:** `refreshReports()` (called by `handleFormSave`) re-runs `fetchAll`. After a successful save the task list will be re-fetched; this is correct (no change needed to refresh logic).
- **No persistence changes** — no backend changes, no migrations.

---

## Acceptance Criteria

1. Opening `/reports` when the backend is running normally shows tasks in the "Link Tasks" dropdown (given the authenticated user has at least one task).
2. Selecting a task checkbox toggles its checked state and the task ID is included in `associatedTaskIds` when the report is saved.
3. If `listTasks` fails with a non-401 network or server error while `listReports` succeeds: the reports list renders normally AND an inline error banner appears reading "Could not load tasks — task linking unavailable" (or similar).
4. If `listTasks` fails with a 401: `logout()` is called and the user is redirected to the login page.
5. If every task in the list has a valid UUID `id`, the `task.id` null guard has no visible effect — behavior is identical to before.
6. `npm run build` — 0 TypeScript errors.
7. Manual: open the Report form → "Link Tasks" → tasks are visible and selectable → save → confirm `associatedTaskIds` in the response JSON.

---

## Testing / QA

### Automated tests

There are no existing frontend unit tests. The acceptance criteria are verified manually and via the `npm run build` TypeScript check.

If a test suite is introduced later, the following cases should be covered:
- `fetchAll` with `listTasks` rejecting: assert `fetchError` state is set and `tasks` is not cleared to `[]`.
- `safeTasks` filter: assert that a `Task` with `id: null` is excluded from the rendered list.

**Build check:**
```bash
cd code/frontend
npm run build
```

### Manual QA checklist

1. Start backend and frontend (`npm run dev`).
2. Log in as the dev user.
3. Navigate to `/reports`.
4. Click "New Report". In the form, expand "Link Tasks". Confirm tasks appear in the dropdown.
5. Select one task. Fill in title and body. Click Save. Confirm 201 response with no console errors.
6. Reopen the saved report in edit mode. Confirm the previously linked task's checkbox is pre-checked.
7. **Failure simulation:** temporarily change `listTasks` in `lib/api.ts` to throw `new Error("simulated")`. Refresh `/reports`. Confirm: report list still renders; error banner appears; "Link Tasks" shows "No tasks available"; no console unhandled rejection.
8. Revert the simulation. Confirm normal operation resumes.

---

## Files touched

- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx)
- [code/frontend/components/reports/ReportForm.tsx](../../../../code/frontend/components/reports/ReportForm.tsx)

---

## Estimated effort

0.5 dev day.

---

## Concurrency & PR strategy

Can be developed in parallel with Step 1. Must not be deployed to a live environment before Step 1 is live (the frontend improvements only provide a useful UX when the backend is correctly returning CORS headers and non-500 task responses).

- **Branch:** `phase-3/bugfix/step-2-frontend-errors`
- **Blocking steps:** None at compile time. Runtime dependency: `phase-3/bugfix/step-1-backend-cors` must be deployed first.
- **Merge Readiness:** false (set to `true` after all acceptance criteria pass and Step 1 is merged)

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `setFetchError` functional updater pattern causes TypeScript error | Low | Fall back to two separate error states (`reportsFetchError`, `tasksFetchError`) |
| `setLoading(false)` called before both settled results are processed (spinner flashes) | Low | Confirm `setLoading(false)` is at the end of `fetchAll`, after both `if/else` blocks, not in a separate `finally` |
| `safeTasks` filter changes the empty-state condition and the existing "No tasks available" message logic breaks | Low | Replace only the `tasks.length === 0` guard with `safeTasks.length === 0`; keep the message text identical |

---

## References

- [master.md](./master.md)
- [step-1-backend-cors-and-error-handling.md](./step-1-backend-cors-and-error-handling.md)
- [observations.txt](./observations.txt)
- [PLANNING.md](../../PLANNING.md)
- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx)
- [code/frontend/components/reports/ReportForm.tsx](../../../../code/frontend/components/reports/ReportForm.tsx)
- [code/frontend/lib/generated/types.gen.ts](../../../../code/frontend/lib/generated/types.gen.ts) — `TaskSchema.id: string | null | undefined`

---

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests listed — manual QA checklist + build check
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected — **N/A: frontend only**
