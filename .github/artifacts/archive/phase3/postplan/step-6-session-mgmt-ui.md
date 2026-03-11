# Step 6 — Session Management UI

## Purpose

Add start/stop focus session controls to the CurrentSessionCard so users can manage sessions directly from the tasks page UI.

## Deliverables

- "Start Focus Session" button visible when no session is active.
- A small form (task selector + optional goal) for starting a session.
- "Stop Session" button visible when a session is active.
- Session state refreshes in the UI after start/stop.

## Primary files to change (required)

- [code/frontend/components/dashboard/CurrentSessionCard.tsx](code/frontend/components/dashboard/CurrentSessionCard.tsx)
- [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx)

## Detailed implementation steps

1. Read the current state of [code/frontend/components/dashboard/CurrentSessionCard.tsx](code/frontend/components/dashboard/CurrentSessionCard.tsx). It currently displays session info (task name, goal, start time, elapsed duration) but has no interactive controls.

2. Add props to `CurrentSessionCard`:
   ```typescript
   interface CurrentSessionCardProps {
     session: SessionLogSchema | null
     tasks: Task[]
     onStartSession: (taskId: string, goal?: string) => Promise<void>
     onStopSession: () => Promise<void>
   }
   ```

3. When `session` is `null` (no active session):
   - Render a "Start Focus Session" button.
   - On click, show an inline form or small dropdown with:
     - A `<select>` to pick a task from `tasks` list.
     - An optional `<input>` for a session goal/description.
     - "Start" and "Cancel" buttons.
   - On "Start", call `onStartSession(selectedTaskId, goal)`.
   - Style all form elements with dark theme: `bg-slate-900 border-slate-600 text-white`.

4. When `session` is not null (active session):
   - Keep the existing session info display.
   - Add a "Stop Session" button with a distinct style (e.g., `bg-red-600 hover:bg-red-700`) at the bottom of the card.
   - On click, call `onStopSession()`.

5. In [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx):
   - Import `startSession` and `stopSession` from [code/frontend/lib/api.ts](code/frontend/lib/api.ts).
   - Create handler functions:
     ```typescript
     const handleStartSession = async (taskId: string, goal?: string) => {
       if (!token) return
       try {
         const session = await startSession(token, { taskId, goal })
         setActiveSession(session)
       } catch (err) {
         // Display error or console.error
       }
     }

     const handleStopSession = async () => {
       if (!token) return
       try {
         await stopSession(token)
         setActiveSession(null)
       } catch (err) {
         // Display error or console.error
       }
     }
     ```
   - Pass `tasks`, `onStartSession={handleStartSession}`, and `onStopSession={handleStopSession}` to `CurrentSessionCard`.

6. Add loading/disabled states to the start/stop buttons to prevent double-clicks.

## Integration & Edge Cases

- No persistence changes (backend already handles sessions).
- If the selected task is deleted while the session form is open, the start call may fail with 404 — display the error via the pattern from Step 2.
- The session polling (every 30s) continues alongside; the UI should not flicker when polling refreshes coincide with a user action. Use a debounce or skip the next poll after a manual action.
- `SessionStartRequest` type requires `taskId` (string) and optional `goal` (string) — verify against [code/frontend/lib/generated/types.gen.ts](code/frontend/lib/generated/types.gen.ts).

## Acceptance Criteria (required)

1. When no session is active, a "Start Focus Session" button is visible in the CurrentSessionCard.
2. Clicking "Start Focus Session" reveals a task selector and optional goal input.
3. Selecting a task and clicking "Start" calls `POST /sessions/start` and the card updates to show the active session.
4. When a session is active, a "Stop Session" button is visible.
5. Clicking "Stop Session" calls `POST /sessions/stop` and the card returns to the "no session" state.
6. Start/stop buttons show loading state during API calls.
7. `npm run build` passes with zero errors.

## Testing / QA (required)

**Automated:**
```bash
cd code/frontend && npm run build
```

**Manual QA checklist:**
1. Navigate to `/tasks` with no active session — confirm "Start Focus Session" button visible.
2. Click "Start Focus Session" — confirm task dropdown and goal input appear.
3. Select a task and click "Start" — confirm the card transitions to show the active session with elapsed time.
4. Confirm "Stop Session" button is now visible.
5. Click "Stop Session" — confirm the card returns to the idle state.
6. Start a session, then refresh the page — confirm the active session persists (fetched from API).

## Files touched (repeat for reviewers)

- [code/frontend/components/dashboard/CurrentSessionCard.tsx](code/frontend/components/dashboard/CurrentSessionCard.tsx)
- [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx)

## Estimated effort

0.5–1 dev day

## Concurrency & PR strategy

- Suggested branch: `phase-3/step-6-session-mgmt-ui`
- Blocking steps: None
- Merge Readiness: false
- This step is in Concurrency Group A and can be worked/merged independently.

## Risks & Mitigations

- **Risk:** `SessionStartRequest` type shape differs from expected. **Mitigation:** Check generated types before implementation.
- **Risk:** Race condition if user double-clicks start. **Mitigation:** Disable button during API call.

## References

- [code/frontend/lib/api.ts](code/frontend/lib/api.ts) — `startSession()`, `stopSession()` wrappers
- [code/frontend/lib/generated/types.gen.ts](code/frontend/lib/generated/types.gen.ts) — `SessionStartRequest` type
- [code/backend/app/api/sessions.py](code/backend/app/api/sessions.py) — backend session endpoints

## Author Checklist (must complete before PR)

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation) — N/A (frontend UI)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected — N/A
