# Step 5 — SystemState Management UI

## Purpose

Build a frontend interface for managing System States (Vacation/Leave schedules) so users can create, view, edit, and delete scheduled pauses directly from the dashboard, enabling the silence indicator to dynamically reflect "SYSTEM PAUSED" status without manual database intervention.

## Deliverables

- New `code/frontend/components/system-state/SystemStateManager.tsx` — main component: list of states + create form
- New `code/frontend/components/system-state/SystemStateCard.tsx` — individual state display with edit/delete actions
- New `code/frontend/components/system-state/SystemStateForm.tsx` — create/edit form with mode type selector, date range, description, recovery toggle
- Integration into the Reports page (or accessible from navbar) as a collapsible panel or modal
- Dynamic "SYSTEM PAUSED" badge in `AppNavBar` works end-to-end when an active state is created/deleted

## Primary files to change (required)

- [code/frontend/components/system-state/SystemStateManager.tsx](../../../../code/frontend/components/system-state/SystemStateManager.tsx) *(new)*
- [code/frontend/components/system-state/SystemStateCard.tsx](../../../../code/frontend/components/system-state/SystemStateCard.tsx) *(new)*
- [code/frontend/components/system-state/SystemStateForm.tsx](../../../../code/frontend/components/system-state/SystemStateForm.tsx) *(new)*
- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx) *(modify — add SystemState trigger/panel)*
- [code/frontend/components/nav/AppNavBar.tsx](../../../../code/frontend/components/nav/AppNavBar.tsx) *(modify — add settings/pause icon trigger)*

## Detailed implementation steps

1. **Create `SystemStateCard.tsx`** in `code/frontend/components/system-state/`:
   - Displays a single system state with:
     - Mode type badge: "VACATION" (sky-500) or "LEAVE" (violet-500)
     - Date range: formatted start → end dates
     - Status indicator: "Active" (pulsing green dot) if covering now, "Upcoming" (blue dot) if in future, "Expired" (slate dot) if past
     - Description text (if present)
     - `requiresRecovery` indicator (small recovery icon/text if true)
     - Edit + Delete action buttons (icon buttons, right side)
   - Props: `state: SystemStateSchema`, `onEdit: (state: SystemStateSchema) => void`, `onDelete: (id: string) => void`
   - Styling: dark card `bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-3`

2. **Create `SystemStateForm.tsx`** in `code/frontend/components/system-state/`:
   - Modal or inline form with fields:
     - Mode type: dropdown/segmented control — "Vacation" or "Leave"
     - Start date: date input (`type="date"` or datetime-local)
     - End date: date input (must be after start date; validated client-side)
     - Description: optional text input (single line or short textarea)
     - Requires recovery: toggle switch (default on)
   - Modes: "create" (empty, calls `createSystemState`) and "edit" (pre-populated, calls `updateSystemState`)
   - Error handling: show inline error for overlap (409 from backend), validation errors (422)
   - Props: `mode: "create" | "edit"`, `state?: SystemStateSchema`, `token: string`, `onClose: () => void`, `onSave: () => void`
   - Styling: dark theme modal overlay `bg-slate-800 border border-slate-700 rounded-xl p-6`

3. **Create `SystemStateManager.tsx`** in `code/frontend/components/system-state/`:
   - Fetches `listSystemStates(token)` on mount
   - Renders:
     - Header: "System Pauses" with a "+ Schedule Pause" button
     - Active state (if any): highlighted at top with "Currently Active" label
     - Upcoming states: sorted by start date
     - Past/expired states: collapsed section (expandable)
   - State management: `states: SystemStateSchema[]`, `showForm: boolean`, `editingState: SystemStateSchema | null`
   - After create/edit/delete: refetch list + call `onStateChange()` callback so parent can refresh pulse data
   - Props: `token: string`, `onStateChange?: () => void`

4. **Integrate into Reports page**:
   - Add a trigger to access SystemState management. Options (choose one):
     - **Option A (recommended):** A "System Pauses" section below the reports list, collapsible, with a section header matching the dark theme
     - **Option B:** A settings icon in the navbar that opens SystemStateManager as a side panel
   - When a state is created/deleted, refresh pulse data so the navbar badge updates
   - Add to `reports/page.tsx`:
     ```tsx
     <SystemStateManager token={token} onStateChange={refreshPulse} />
     ```

5. **Update `AppNavBar.tsx`** (optional enhancement):
   - When `silenceState === "paused"`, clicking the badge could open a quick view of the active system state (tooltip or popover showing "Vacation until March 7")
   - This is a polish item — not required for acceptance. Core functionality is the badge itself already working via pulse endpoint.

6. **Verify build + end-to-end flow**:
   ```bash
   cd code/frontend
   npm run build   # zero errors
   ```

## Integration & Edge Cases

- **Active state badge:** The `AppNavBar` badge already reflects "SYSTEM PAUSED" via the pulse endpoint. After creating/deleting a state, the pulse data is refetched so the badge updates within the polling interval or on manual refresh.
- **Date input timezone:** HTML date inputs use the browser's local timezone. The backend stores UTC. Document that displayed dates are in local time and stored dates are UTC. For Phase 3 MVP, this discrepancy is acceptable for a single-user tool.
- **Overlap error:** If the backend returns 409 for overlapping states, display a user-friendly error message: "This schedule overlaps with an existing pause. Please adjust the dates."
- **Empty state:** When no system states exist, show: "No scheduled pauses. Use System Pauses to schedule vacation or leave periods."
- **Delete confirmation:** Show a simple confirmation dialog before deleting a state.
- **Recovery flag:** Display but don't act on `requiresRecovery` — Phase 4 AI will use this for re-entry suggestions.

## Acceptance Criteria

1. A "System Pauses" section is accessible from the Reports page (or navbar).
2. Clicking "+ Schedule Pause" opens a form with mode type, date range, description, and recovery toggle.
3. Submitting the form calls `POST /system-states` and the new state appears in the list.
4. An active state (covering now) shows a pulsing "Active" indicator.
5. The `AppNavBar` badge updates to "SYSTEM PAUSED" after creating a vacation covering the current time (within polling interval or on page refresh).
6. Editing a state updates it via `PUT /system-states/{id}`.
7. Deleting a state removes it and the navbar badge reverts (if it was active).
8. Attempting to create an overlapping state shows a user-friendly error message.
9. Past states are shown in a collapsed/dimmed section.
10. `npm run build` exits 0 with zero TypeScript errors.

## Testing / QA

### Automated checks

```bash
cd code/frontend
npm run build   # zero errors
```

### Manual QA checklist

1. Navigate to `/reports` → scroll to System Pauses section
2. Click "+ Schedule Pause" → verify form appears
3. Select "Vacation", set dates covering this week, add description → submit → verify state appears
4. Verify `AppNavBar` badge changes to "SYSTEM PAUSED" (may require page refresh or wait for poll)
5. Click edit on the state → verify form pre-populates → change description → save → verify update
6. Click delete → confirm → verify state removed → badge reverts
7. Create a state in the future → verify "Upcoming" indicator (not "Active")
8. Try creating an overlapping state → verify error message
9. Check mobile responsiveness — form and cards should stack
10. Verify no console errors

## Files touched (repeat for reviewers)

- [code/frontend/components/system-state/SystemStateManager.tsx](../../../../code/frontend/components/system-state/SystemStateManager.tsx)
- [code/frontend/components/system-state/SystemStateCard.tsx](../../../../code/frontend/components/system-state/SystemStateCard.tsx)
- [code/frontend/components/system-state/SystemStateForm.tsx](../../../../code/frontend/components/system-state/SystemStateForm.tsx)
- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx)
- [code/frontend/components/nav/AppNavBar.tsx](../../../../code/frontend/components/nav/AppNavBar.tsx)

## Estimated effort

1.5–2 dev days

## Concurrency & PR strategy

- **Suggested branch:** `phase-3/step-5-system-state-ui`
- **Blocking steps:** `phase-3/step-3-type-sync` must be merged first (TypeScript types and API wrappers required).
- **Merge Readiness:** false
- Can be developed in parallel with Step 4 (Reports page) after Step 3 merges.
- If developed in parallel with Step 4, the integration into `reports/page.tsx` may need conflict resolution at merge time.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Date input UX is poor on some browsers | Use native HTML date inputs for MVP; consider a date picker library later |
| Merge conflict with Step 4 on `reports/page.tsx` | Coordinate: Step 4 adds ReportList, Step 5 adds SystemStateManager; both modify the same page but different sections |
| Timezone confusion between local display and UTC storage | Document clearly; add tooltip "All times in UTC" for Phase 3 |

## References

- [PDD.md — §3.4 SystemState, §3.3 System Pause](../../PDD.md)
- [product.md — §3.3 System Pause (Vacation Mode)](../../product.md)
- [Phase 3 Master](./master.md)
- [Step 2 — SystemState Backend](./step-2-system-state-backend.md)
- [Step 3 — Type Sync](./step-3-type-sync.md)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added (build gate)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
- [ ] Author signoff
