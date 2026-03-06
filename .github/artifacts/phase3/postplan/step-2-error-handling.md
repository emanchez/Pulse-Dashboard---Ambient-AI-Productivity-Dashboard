# Step 2 — Frontend Error Handling

## Purpose

Surface API errors to users in ReportForm and SystemStateManager, fixing the silent failure that makes the report save button appear non-functional.

## Deliverables

- Visible error banners in `ReportForm` when `createReport` / `updateReport` API calls fail.
- Visible error banners in `SystemStateManager` when fetch or delete calls fail.
- Errors are dismissible or auto-clear on next successful action.

## Primary files to change (required)

- [code/frontend/components/reports/ReportForm.tsx](code/frontend/components/reports/ReportForm.tsx)
- [code/frontend/components/system-state/SystemStateManager.tsx](code/frontend/components/system-state/SystemStateManager.tsx)

## Detailed implementation steps

### ReportForm.tsx

1. Add a new state variable: `const [apiError, setApiError] = useState<string | null>(null)`.
2. In the `handleSubmit` function, clear the error before the try block: `setApiError(null)`.
3. In the `catch` block (currently `console.error("Failed to save report:", err)`), extract a user-friendly message: `setApiError(err instanceof Error ? err.message : "Failed to save report. Please try again.")`. Keep the `console.error` for debugging.
4. Render the error above the action buttons (before the `<div className="flex items-center justify-end gap-3">` block):
   ```tsx
   {apiError && (
     <div className="mb-4 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg px-4 py-3 text-sm">
       {apiError}
     </div>
   )}
   ```
5. The error should auto-clear on the next submit attempt (step 2 above handles this).

### SystemStateManager.tsx

1. Add a new state variable: `const [error, setError] = useState<string | null>(null)`.
2. In `fetchStates`, replace the empty `catch {}` block with: `catch (err) { setError(err instanceof Error ? err.message : "Failed to load system states.") }`.
3. In `handleDelete`, replace the empty `catch {}` block with: `catch (err) { setError(err instanceof Error ? err.message : "Failed to delete state.") }`.
4. Clear the error at the start of each operation: `setError(null)` at the top of `fetchStates` and `handleDelete`.
5. Render the error banner near the top of the component's return JSX (after the heading):
   ```tsx
   {error && (
     <div className="mb-4 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg px-4 py-3 text-sm">
       {error}
     </div>
   )}
   ```

## Integration & Edge Cases

- No persistence changes.
- Error messages from the backend may contain raw HTTP text (e.g. `"Request failed 422: {...}"` from the `request()` helper in `api.ts`). The displayed message may not always be pretty; a future enhancement could parse JSON error details. For now, showing the raw error is better than showing nothing.
- If the backend is unreachable, `fetch` throws a `TypeError` — this is also caught and displayed.

## Acceptance Criteria (required)

1. When `createReport` fails (e.g., backend returns 422), a visible red error banner appears within the ReportForm modal.
2. When `updateReport` fails, the same error banner appears.
3. The error clears when the user attempts to submit again.
4. When `fetchStates` fails in SystemStateManager, an error banner is visible.
5. When `handleDelete` fails in SystemStateManager, an error banner is visible.
6. `npm run build` passes with zero errors.

## Testing / QA (required)

**Automated:**
- No backend test changes.
- `cd code/frontend && npm run build` must pass.

**Manual QA checklist:**
1. Open the Report creation form. Stop the backend server. Click "Save Report" — confirm an error message appears in the form.
2. Restart the backend. Submit again — confirm the error clears and the report saves successfully.
3. Navigate to `/reports` (which includes SystemStateManager). Stop the backend — confirm an error message appears in the system states section.
4. On the system states section, attempt to delete a state while the backend is down — confirm an error appears.

## Files touched (repeat for reviewers)

- [code/frontend/components/reports/ReportForm.tsx](code/frontend/components/reports/ReportForm.tsx)
- [code/frontend/components/system-state/SystemStateManager.tsx](code/frontend/components/system-state/SystemStateManager.tsx)

## Estimated effort

< 0.5 dev days

## Concurrency & PR strategy

- Suggested branch: `phase-3/step-2-error-handling`
- Blocking steps: None
- Merge Readiness: false
- This step is in Concurrency Group A and can be worked/merged independently.

## Risks & Mitigations

- **Risk:** Error messages from backend contain sensitive info (stack traces). **Mitigation:** The app is local-first / single-user; raw errors are acceptable for now. Production hardening would sanitize messages.

## References

- [User observations](./observations.txt) — "cannot actually submit reports, save button does nothing"
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts) — `request()` helper throws `Error` with status and body text.

## Author Checklist (must complete before PR)

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation) — N/A (frontend only)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected — N/A
