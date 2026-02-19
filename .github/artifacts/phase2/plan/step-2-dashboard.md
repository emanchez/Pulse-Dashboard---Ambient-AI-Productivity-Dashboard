# Step 2 — Dashboard Experience

## Purpose
Transform the Bento dashboard into a Zone A/B experience that shows the Silence Indicator, priority-colors tasks, and keeps edits local until the user manually taps “Save changes.”

## Deliverables
- Enhanced `[code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx)` layout that reserves Zone A for the Silence Indicator and Zone B for the task board.
- New `/components/PulseCard.tsx` and `/components/TaskBoard.tsx` (or equivalent) that render silence state badges, show the manual save button, and handle color-coded priorities.
- Updates to `[code/frontend/lib/api.ts](code/frontend/lib/api.ts)` to expose a `fetchPulse(token)` helper and any batching helpers for updating multiple tasks in one request.
- A manual-save flow where edits are kept in state, the “Save changes” button disables when there are no pending updates, and only triggers when clicked.

## Primary files to change (required)
- [code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx)
- [code/frontend/components/PulseCard.tsx](code/frontend/components/PulseCard.tsx)
- [code/frontend/components/TaskBoard.tsx](code/frontend/components/TaskBoard.tsx)
- [code/frontend/app/page.tsx](code/frontend/app/page.tsx)
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts)

## Detailed implementation steps
1. Refactor `BentoGrid` so Zone A spans `md:col-span-2` for the Pulse card, Zone B occupies `md:col-span-1` for the Task board, and other columns remain placeholders for future zones; provide `className` props to allow theming and debugging overlays for QA.
2. Implement `PulseCard` in `code/frontend/components/PulseCard.tsx` with a `useEffect` that polls `fetchPulse(token)` every 30 seconds (cleanup timer on unmount), renders `silenceState` badges (blue/amber/green), displays human-readable `gapMinutes` (e.g., "Gap: 1h 20m") plus `pausedUntil` when present, and surfaces the token expiry or refresh action if the backend responds 401.
3. Build `TaskBoard` in `code/frontend/components/TaskBoard.tsx` that renders fetched tasks in a `table` or `div` grid, wires field inputs (name, priority dropdown, notes textarea) to local state, stores diffs in an `unsavedChanges` Map keyed by task id, and shows an `Unsaved` pill and priority-colored border per row whenever dirty.
4. Add the `Save changes` control inside `TaskBoard` that stays disabled when `unsavedChanges.size === 0` and toggles to `Saving…` while sequentially calling `updateTask(token, id, change)` for each pending edit; any failure should set an `error` string, re-enable the button, and keep the `unsavedChanges` entry so the user can retry.
5. Update `code/frontend/app/page.tsx` to compose `BentoGrid`, `PulseCard`, and `TaskBoard`, fetch/reload tasks (`listTasks`) and pulse data on mount, and pass the JWT token (reuse existing auth flow) to both components while showing skeleton loaders until data arrives.
6. Implement `useTasks()` hook or similar to centralize task fetching, dirty diff tracking, and the manual save action, so the `Save changes` button can be placed consistently within the Task board area while resetting state on success (pull data from server again to avoid normalization drift).
7. Apply priority color tokens per row (High = `text-rose-600`/`bg-rose-50`, Medium = `text-amber-700`/`bg-amber-50`, Low = `text-sky-700`/`bg-sky-50`) including subtle drop shadows or accents to reinforce PDD palette, and ensure the manual save experience works on mobile/responsive breakpoints.

## Integration & Edge Cases
- If the pulse endpoint responds with `paused`, the TaskBoard should still allow edits, but the Silence Indicator must show the paused end time (the manual save behavior is unaffected).
- The TaskBoard should guard against stale tokens by funneling API errors through a refresh or logout (reuse existing auth logic or display a prompt).
- Handle empty task lists gracefully and show a CTA to create new tasks once API is wired to creation (Phase 3+).

## Acceptance Criteria (required)
1. Silence Indicator (Zone A) displays the `silenceState` badge and updates every 30s; when `silenceState` is `paused`, it shows the `pausedUntil` timestamp.
2. Task rows apply priority colors (High = rose, Medium = amber, Low = sky) and show a subtle `Unsaved` pill when the fields differ from the last saved state.
3. Editing a task does not call the API until the user clicks “Save changes,” and the button is disabled unless `unsavedChanges` exists.
4. After clicking “Save changes,” each changed task updates via `PUT /tasks/{id}`; once all requests succeed, the unsaved markers disappear and the button re-enters the disabled state.

## Testing / QA (required)
- Tests to add: Basic component tests are optional, but include a manual QA checklist; automated snapshot tests are not required yet.
- Manual QA checklist:
  1. Login and visit the dashboard; ensure the Silence Indicator cycles between engaged/stagnant/paused when the backend data changes.
  2. Modify several task fields (name, priority, notes) and confirm the “Save changes” button enables but no API calls fire until clicked.
  3. Click “Save changes” and ensure priority colors are preserved, the button disables during saving, and pending flags clear on success.
  4. Verify the Pulse card shows the `pausedUntil` value whenever SystemState indicates a vacation.

## Files touched (repeat for reviewers)
- [code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx)
- [code/frontend/components/PulseCard.tsx](code/frontend/components/PulseCard.tsx)
- [code/frontend/components/TaskBoard.tsx](code/frontend/components/TaskBoard.tsx)
- [code/frontend/app/page.tsx](code/frontend/app/page.tsx)
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts)

## Estimated effort
- 2-3 developer days

## Concurrency & PR strategy
- Blocking steps:
  - Blocked until: `.github/artifacts/phase2/plan/step-1-pulse-api.md`
- Merge Readiness: false

## Risks & Mitigations
- Risk: Manual save state drifts if the backend returns different normalized values (e.g., server modifies priority casing). Mitigation: reload tasks after saves and diff against server response.
- Risk: Pulse poll floods the backend. Mitigation: throttle to 30s and cleanup the interval on unmount.

## References
- [.github/artifacts/PDD.md](.github/artifacts/PDD.md)
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts)
- [code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx)

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] Primary files to change referenced
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests noted or manual QA defined
- [ ] Manual QA checklist added
