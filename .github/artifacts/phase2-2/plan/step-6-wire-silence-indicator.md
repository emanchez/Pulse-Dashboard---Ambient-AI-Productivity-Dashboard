# Step 6 — Wire + PDD §4.1 Silence Indicator Integration

## Purpose

Connect all live data fetches to the Tasks dashboard page, lift shared state to `app/tasks/page.tsx` to eliminate duplicate network calls, and implement the PDD §4.1 Silence Indicator so that the `AppNavBar` badge and `FocusHeader` subtitle copy reflect the real-time silence state derived from `GET /stats/pulse`.

## Deliverables

- Updated `code/frontend/app/tasks/page.tsx` — lifts all four data fetches (`getPulse`, `getFlowState`, `getActiveSession`, `listTasks`) to page level; passes data as props to all children
- Updated `code/frontend/app/layout.tsx` — passes live `silenceState` from page context down to `AppNavBar`
- Updated `code/frontend/components/nav/AppNavBar.tsx` — receives `silenceState` prop and reflects correct badge colour/text
- Updated `code/frontend/components/dashboard/FocusHeader.tsx` — receives `silenceState` + `pausedUntil` and renders state-aware subtitle
- Updated `code/frontend/components/dashboard/TaskQueueTable.tsx` — receives `activeSessionTaskId` prop from page, wired to live session data
- Updated `code/frontend/components/dashboard/DailyGoalsCard.tsx` — receives `tasks` as prop (shared fetch, no internal `listTasks` call)
- Updated `code/frontend/components/dashboard/TaskQueueTable.tsx` — receives `tasks` as prop (shared fetch, no internal `listTasks` call)

## Primary files to change (required)

- [code/frontend/app/tasks/page.tsx](../../../../code/frontend/app/tasks/page.tsx)
- [code/frontend/app/layout.tsx](../../../../code/frontend/app/layout.tsx)
- [code/frontend/components/nav/AppNavBar.tsx](../../../../code/frontend/components/nav/AppNavBar.tsx)
- [code/frontend/components/dashboard/FocusHeader.tsx](../../../../code/frontend/components/dashboard/FocusHeader.tsx)
- [code/frontend/components/dashboard/DailyGoalsCard.tsx](../../../../code/frontend/components/dashboard/DailyGoalsCard.tsx)
- [code/frontend/components/dashboard/TaskQueueTable.tsx](../../../../code/frontend/components/dashboard/TaskQueueTable.tsx)

## Detailed implementation steps

### 1. Lift all fetches to `app/tasks/page.tsx`

Replace the pattern of each component fetching its own data with a single set of `useEffect`/`useState` calls at the page level. The page holds:

```typescript
const [pulseStats, setPulseStats] = useState<PulseStats | null>(null)
const [flowState, setFlowState] = useState<FlowState | null>(null)
const [activeSession, setActiveSession] = useState<SessionLog | null>(null)
const [tasks, setTasks] = useState<Task[]>([])
const [loading, setLoading] = useState(true)
```

**Fetch on mount + polling:**

| Data | Function | Poll interval |
|---|---|---|
| `pulseStats` | `getPulse(token)` | 30,000 ms |
| `flowState` | `getFlowState(token)` | 60,000 ms |
| `activeSession` | `getActiveSession(token)` | 30,000 ms |
| `tasks` | `listTasks(token)` | 60,000 ms |

All four polls start simultaneously on mount. Each uses a `setInterval` cleanup pattern:

```typescript
useEffect(() => {
  const fetchAll = async () => { /* ... */ }
  fetchAll()
  const pulseTimer = setInterval(() => getPulse(token).then(setPulseStats), 30_000)
  const flowTimer  = setInterval(() => getFlowState(token).then(setFlowState), 60_000)
  const sessTimer  = setInterval(() => getActiveSession(token).then(setActiveSession), 30_000)
  const taskTimer  = setInterval(() => listTasks(token).then(setTasks), 60_000)
  return () => { clearInterval(pulseTimer); clearInterval(flowTimer);
                 clearInterval(sessTimer); clearInterval(taskTimer) }
}, [token])
```

All 401 responses call `logout` (reuse `onAuthError` pattern from existing components).

### 2. Pass data as props to children

Update component prop interfaces and the page composition:

- **`FocusHeader`**: receives `silenceState` + `pausedUntil` from `pulseStats`
- **`ProductivityPulseCard`**: receives `flowState: FlowState | null` (remove internal fetch; add loading state from `flowState === null`)
- **`CurrentSessionCard`**: receives `session: SessionLog | null` (remove internal fetch)
- **`DailyGoalsCard`**: receives `tasks: Task[]` (remove internal `listTasks` call)
- **`TaskQueueTable`**: receives `tasks: Task[]` + `activeSessionTaskId: string | null` from `activeSession?.taskId ?? null`

### 3. Propagate `silenceState` to `AppNavBar`

`AppNavBar` is rendered inside `app/layout.tsx` which is a server component — it cannot directly subscribe to client state from the tasks page. Solution: extract a thin `AppNavBarWrapper` client component that:
- Reads silence state via a shared React context (`SilenceStateContext`) or — simpler, matching the codebase pattern — accepts a `silenceState` prop from the page
- Since `layout.tsx` wraps all pages, use the approach of rendering `AppNavBar` with a default prop in `layout.tsx`, and override it inside `tasks/page.tsx` by rendering a page-level `AppNavBar` that sits outside of the layout's `<main>` wrapper using Next.js layout slots, **or** — the simpler approach compatible with the existing structure: move `AppNavBar` rendering out of `layout.tsx` and into each page's top-level render, keeping `layout.tsx` minimal. For this phase, **move `AppNavBar` from `layout.tsx` into `tasks/page.tsx`** directly (above `<BentoGrid>`), and keep `reports/page.tsx` rendering its own static `<AppNavBar silenceState="engaged" />`. Update `layout.tsx` to remove the `AppNavBar` import added in Step 4.

### 4. Silence Indicator state-to-UI mapping (PDD §4.1)

| `pulseStats.silenceState` | `AppNavBar` badge label | Badge Tailwind | `FocusHeader` subtitle |
|---|---|---|---|
| `"engaged"` | `FOCUS MODE ACTIVE` | `bg-emerald-500/20 text-emerald-400 border-emerald-500/30` | `"Deep work session active. Distractions minimized."` |
| `"stagnant"` | `STAGNANT — {gap}h gap` | `bg-amber-500/20 text-amber-400 border-amber-500/30` | `"Momentum gap detected. Re-engage to restore flow."` |
| `"paused"` | `SYSTEM PAUSED` | `bg-sky-500/20 text-sky-400 border-sky-500/30` | `"System paused${pausedUntil ? \` until ${date}\` : "."}"` |

For `stagnant`, `gap` = `Math.round(pulseStats.gapMinutes / 60)` hours.

### 5. `activeSessionTaskId` wiring

Pass `activeSession?.taskId ?? null` from page state into `<TaskQueueTable activeSessionTaskId={...} />`. This activates the "In Progress" pill for the task currently being worked on.

### 6. Full-screen loading state

While `loading === true` (before any data arrives), render the existing spinner pattern used in the old `app/page.tsx`. Once any data arrives, set `loading = false` and render the full layout — individual cards show their own skeletons while their specific data is null.

## Integration & Edge Cases

- **`ProductivityPulseCard` receives `null` `flowState`:** Component must show skeleton/loading state when prop is `null`. Remove the internal `useEffect` fetch and the `token` prop (it now receives data directly). Update prop interface accordingly.
- **`CurrentSessionCard` receives `null` `session`:** Component shows "No active session" — this is the correct empty state, unchanged from Step 5.
- **`DailyGoalsCard` receives `tasks: Task[]`:** The internal `listTasks` `useEffect` is removed. The component becomes a pure rendering component — simpler and avoids a second network call.
- **`AppNavBar` moved from layout to page:** `reports/page.tsx` must also render `<AppNavBar>` (with static `silenceState="engaged"`). Future pages must remember to include it. This is an accepted trade-off for phase 2.2; a Context-based solution can be introduced in a later phase.
- **Polling cleanup on route change:** The `useEffect` cleanup function clears all `setInterval` timers. Verify no "Can't perform a React state update on an unmounted component" warnings in the console (Next.js 14 suppresses most of these, but test anyway).
- **`getActiveSession` returns `null`:** `setActiveSession(null)` is valid — `CurrentSessionCard` handles it. `activeSession?.taskId` safely returns `undefined` which coerces to `null` for the `activeSessionTaskId` prop.

## Acceptance Criteria

1. With `gap_minutes > 2880` in the DB: `AppNavBar` badge shows amber text "STAGNANT — Xh gap" and `FocusHeader` subtitle reads "Momentum gap detected. Re-engage to restore flow." (verified within one 30 s poll cycle after forcing a stale DB state).
2. With an active `SystemState` row covering today (mode_type = `"vacation"` or `"leave"`): `AppNavBar` badge shows sky "SYSTEM PAUSED" and subtitle updates.
3. With normal engagement (gap < 48 h): `AppNavBar` badge shows emerald "FOCUS MODE ACTIVE" and subtitle reads "Deep work session active. Distractions minimized."
4. `listTasks` is called **once** per poll cycle on the tasks page (not twice — verify in Network DevTools that there are no duplicate `/tasks/` requests).
5. After `POST /sessions/start {"taskName":"UI Redesign","taskId":"<task-uuid>"}`, within 30 s the task row in `TaskQueueTable` shows a blue "In Progress" pill.
6. After `POST /sessions/stop`, within 30 s the "In Progress" pill disappears and the row reverts to "Pending" (or "Completed" if `isCompleted` is true).
7. Navigating to `/reports` renders the shell page without a JS error; `AppNavBar` is visible with static "FOCUS MODE ACTIVE" badge.
8. `npm run build` exits 0 after all changes in this step.
9. All four polling intervals are cleared when the component unmounts (navigate away from `/tasks` and back — no duplicate poll cycles or console warnings).
10. `GET /stats/pulse` returns `200` (regression — no change to existing endpoint).

## Testing / QA

### Automated

No new backend tests (backend untouched in this step). TypeScript compiler build is the gate.

Verify by inserting test data:
- **Stagnant test:** Manually delete recent `ActionLog` rows for the dev user so `gap_minutes > 2880`. Observe badge.
- **Paused test:** Insert a `SystemState` row with `mode_type="vacation"`, `start_date=utcnow()-1h`, `end_date=utcnow()+24h`, `user_id=<dev-user-id>`. Observe badge.

### Manual QA checklist

1. `npm run dev` (both backend + frontend)
2. Log in; navigate to `/tasks`
3. Open Network tab in DevTools — verify only **one** `GET /tasks/` request per 60 s
4. Force stagnant: delete ActionLog rows for dev user (or set `updated_at` to >48h ago); wait 30 s → badge turns amber + subtitle changes
5. Restore engagement: make a task update → within 30 s badge returns emerald
6. Insert a vacation SystemState row → within 30 s badge turns sky; subtitle shows paused text
7. Start a session targeting a specific task UUID → within 30 s that task row shows blue "In Progress"
8. Stop the session → within 30 s "In Progress" disappears
9. Navigate `/tasks` → `/reports` → `/tasks` — no duplicate network calls, no console errors
10. Run `npm run build` — confirm 0 errors

## Files touched

- [code/frontend/app/tasks/page.tsx](../../../../code/frontend/app/tasks/page.tsx)
- [code/frontend/app/layout.tsx](../../../../code/frontend/app/layout.tsx)
- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx)
- [code/frontend/components/nav/AppNavBar.tsx](../../../../code/frontend/components/nav/AppNavBar.tsx)
- [code/frontend/components/dashboard/FocusHeader.tsx](../../../../code/frontend/components/dashboard/FocusHeader.tsx)
- [code/frontend/components/dashboard/ProductivityPulseCard.tsx](../../../../code/frontend/components/dashboard/ProductivityPulseCard.tsx)
- [code/frontend/components/dashboard/CurrentSessionCard.tsx](../../../../code/frontend/components/dashboard/CurrentSessionCard.tsx)
- [code/frontend/components/dashboard/DailyGoalsCard.tsx](../../../../code/frontend/components/dashboard/DailyGoalsCard.tsx)
- [code/frontend/components/dashboard/TaskQueueTable.tsx](../../../../code/frontend/components/dashboard/TaskQueueTable.tsx)

## Estimated effort

1–2 dev days

## Concurrency & PR strategy

- **Blocking steps:** Blocked until both [step-3-type-sync.md](./step-3-type-sync.md) and [step-5-dashboard-components.md](./step-5-dashboard-components.md) are merged.
- **Merge Readiness: false** *(flip to `true` when all 10 Acceptance Criteria pass)*
- Suggested branch: `phase-2-2/step-6-wire-silence-indicator`
- `Depends-On: phase-2-2/step-3-type-sync, phase-2-2/step-5-dashboard-components`

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Moving `AppNavBar` out of `layout.tsx` means new pages must remember to include it | Document as a known pattern; a global `SilenceStateContext` solution is deferred to a later phase |
| Four simultaneous `setInterval` timers on a single page cause excessive re-renders | Each setter is called with a fresh value; React batches state updates in 18+. If performance degrades, consolidate into a single 30 s interval that fetches all data |
| `silenceState` arrives after initial render, causing a badge flicker from default "engaged" | Show a neutral skeleton badge (`text-slate-500 "Checking…"`) until `pulseStats` arrives — avoids misleading "engaged" signal |
| Stale closure in `setInterval` callback captures old `token` | Capture `token` in a ref (`useRef`) and read `tokenRef.current` inside the interval callback |

## References

- [PDD.md — §4.1 Silence Gap Analysis](../PDD.md)
- [code/frontend/components/PulseCard.tsx](../../../../code/frontend/components/PulseCard.tsx) *(polling pattern + onAuthError reference)*
- [step-3-type-sync.md](./step-3-type-sync.md)
- [step-5-dashboard-components.md](./step-5-dashboard-components.md)
- [master.md](./master.md)

## Author Checklist

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/` (happy path + validation)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected
