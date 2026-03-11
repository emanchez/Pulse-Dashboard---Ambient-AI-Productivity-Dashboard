# Step 8 — Navigation Polish & Dead Code Cleanup

## Purpose

Add logout functionality, fix the orphaned "Create New Report" button, remove dead code, and clean up hardcoded placeholders in the navigation and tasks page.

## Deliverables

- Logout button accessible from the navbar (avatar dropdown or click).
- "Create New Report" button conditionally rendered (only when `onCreateReport` is provided).
- `PulseCard.tsx` deleted (confirmed dead code).
- Hardcoded `QuickAccessCard` placeholders removed or replaced.
- Non-functional bell icon addressed.

## Primary files to change (required)

- [code/frontend/components/nav/AppNavBar.tsx](code/frontend/components/nav/AppNavBar.tsx)
- [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx)
- [code/frontend/app/reports/page.tsx](code/frontend/app/reports/page.tsx)
- [code/frontend/components/PulseCard.tsx](code/frontend/components/PulseCard.tsx) (delete)

## Detailed implementation steps

### 8.1 — Logout functionality

1. In [code/frontend/components/nav/AppNavBar.tsx](code/frontend/components/nav/AppNavBar.tsx):
   - Add `onLogout?: () => void` to the `AppNavBarProps` interface.
   - Replace the static avatar `<div>` (currently hardcoded "U") with a clickable element that triggers logout. Options:
     - **Simple approach:** Wrap avatar in a `<button onClick={onLogout} title="Logout">` with hover state.
     - **Dropdown approach:** Add a small dropdown on click with "Logout" option (more extensible but more code).
   - Recommended: simple approach for now — single click on avatar logs out. Add a tooltip `title="Click to logout"`.

2. In [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx):
   - The `useAuth` hook already provides `logout`. Pass `onLogout={logout}` to `AppNavBar`:
     ```tsx
     <AppNavBar
       silenceState={silenceState}
       gapMinutes={gapMinutes}
       onLogout={logout}
     />
     ```

3. In [code/frontend/app/reports/page.tsx](code/frontend/app/reports/page.tsx):
   - Same: pass `onLogout={logout}` to `AppNavBar`.

### 8.2 — Conditional "Create New Report" button

1. In [code/frontend/components/nav/AppNavBar.tsx](code/frontend/components/nav/AppNavBar.tsx):
   - Wrap the "Create New Report" button in a conditional:
     ```tsx
     {onCreateReport && (
       <button
         onClick={onCreateReport}
         className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 ..."
       >
         + Create New Report
       </button>
     )}
     ```
   - Currently the button always renders, even on `/tasks` where `onCreateReport` is not passed, resulting in a no-op click.

### 8.3 — Remove hardcoded QuickAccess placeholders

1. In [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx):
   - The page renders two `QuickAccessCard` components with hardcoded strings:
     - "Team Sync" — "Starts in 14 mins"
     - "Docs & Assets" — "Internal wiki access"
   - Remove these `QuickAccessCard` instances entirely, or replace them with data-driven content. Since there is no backend support for quick access items, removal is appropriate. Remove the `QuickAccessCard` import if no longer used.
   - Also remove the `Users` and `FileText` imports from `lucide-react` if they were only used for the QuickAccess icons.

### 8.4 — Delete PulseCard.tsx

1. Delete [code/frontend/components/PulseCard.tsx](code/frontend/components/PulseCard.tsx).
2. Before deletion, verify no imports exist: `grep -r "PulseCard" code/frontend/`. Expected result: no matches (component is confirmed unused by audit).

### 8.5 — Address non-functional bell icon

1. In [code/frontend/components/nav/AppNavBar.tsx](code/frontend/components/nav/AppNavBar.tsx):
   - The bell icon has `cursor-pointer` but no handler. Either:
     - Remove it entirely (recommended for MVP — no notifications feature exists), or
     - Add `pointer-events-none opacity-50` and `title="Notifications — coming soon"` to indicate it's a future feature.

## Integration & Edge Cases

- No persistence changes.
- Removing `QuickAccessCard` from the tasks page may affect the `BentoGrid` layout — verify the grid still renders correctly without those cells. The `tasks-dashboard` variant in `BentoGrid.tsx` assigns grid positions; ensure removed items don't leave blank slots.
- `logout()` from `useAuth` clears localStorage and navigates to `/login`.

## Acceptance Criteria (required)

1. Clicking the avatar circle in the navbar triggers logout and redirects to `/login`.
2. On `/tasks`, the "Create New Report" button is not visible (since `onCreateReport` is not passed).
3. On `/reports`, the "Create New Report" button is visible and functional.
4. `PulseCard.tsx` is deleted; `grep -r "PulseCard" code/frontend/` returns no results.
5. The hardcoded "Team Sync" and "Docs & Assets" cards are removed from `/tasks`.
6. The bell icon is either removed or visually marked as disabled.
7. `npm run build` passes with zero errors.

## Testing / QA (required)

**Automated:**
```bash
cd code/frontend && npm run build
grep -r "PulseCard" code/frontend/  # Should return empty
```

**Manual QA checklist:**
1. Navigate to `/tasks` — confirm no "Create New Report" button in navbar.
2. Navigate to `/reports` — confirm "Create New Report" button is present and functional.
3. Click the avatar in the navbar — confirm redirect to `/login`.
4. Confirm you are logged out (visiting `/tasks` redirects to `/login`).
5. Log back in — navigate to `/tasks` — confirm "Team Sync" and "Docs & Assets" cards are gone.
6. Confirm the tasks page grid still renders correctly without the QuickAccess cards.
7. Confirm the bell icon is either absent or visually disabled.

## Files touched (repeat for reviewers)

- [code/frontend/components/nav/AppNavBar.tsx](code/frontend/components/nav/AppNavBar.tsx)
- [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx)
- [code/frontend/app/reports/page.tsx](code/frontend/app/reports/page.tsx)
- [code/frontend/components/PulseCard.tsx](code/frontend/components/PulseCard.tsx) (deleted)

## Estimated effort

0.5–1 dev day

## Concurrency & PR strategy

- Suggested branch: `phase-3/step-8-nav-polish-cleanup`
- Blocking steps: None
- Merge Readiness: false
- This step is in Concurrency Group A and can be worked/merged independently.
- **Note:** If Step 5 (Task CRUD UI) also modifies the tasks page layout or removes QuickAccessCard, coordinate to avoid merge conflicts. Since Step 5 is in Group B (blocked on 3+4), this step will likely merge first.

## Risks & Mitigations

- **Risk:** Removing QuickAccessCard breaks BentoGrid layout. **Mitigation:** Test the grid visually after removal; adjust grid slots if needed.
- **Risk:** Avatar-click logout surprises users (no confirmation). **Mitigation:** Acceptable for single-user app; add confirmation dialog if desired.

## References

- [code/frontend/lib/hooks/useAuth.ts](code/frontend/lib/hooks/useAuth.ts) — `logout()` function
- [code/frontend/components/dashboard/QuickAccessCard.tsx](code/frontend/components/dashboard/QuickAccessCard.tsx) — component being removed from page

## Author Checklist (must complete before PR)

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation) — N/A (frontend UI + cleanup)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected — N/A
