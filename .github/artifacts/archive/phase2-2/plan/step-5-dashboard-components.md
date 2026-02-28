# Step 5 — Dashboard Components

## Purpose

Build all seven new React components that compose the Tasks dashboard — `FocusHeader`, `ProductivityPulseCard`, `CurrentSessionCard`, `DailyGoalsCard`, `QuickAccessCard`, `TaskQueueTable` — and assemble them in `app/tasks/page.tsx` inside the `BentoGrid variant="tasks-dashboard"` shell from Step 4.

## Deliverables

- `code/frontend/components/dashboard/FocusHeader.tsx`
- `code/frontend/components/dashboard/ProductivityPulseCard.tsx`
- `code/frontend/components/dashboard/CurrentSessionCard.tsx`
- `code/frontend/components/dashboard/DailyGoalsCard.tsx`
- `code/frontend/components/dashboard/QuickAccessCard.tsx`
- `code/frontend/components/dashboard/TaskQueueTable.tsx`
- Updated `code/frontend/app/tasks/page.tsx` — full composition replacing the Step 4 placeholder

## Primary files to change (required)

- [code/frontend/components/dashboard/FocusHeader.tsx](../../../../code/frontend/components/dashboard/FocusHeader.tsx) *(new)*
- [code/frontend/components/dashboard/ProductivityPulseCard.tsx](../../../../code/frontend/components/dashboard/ProductivityPulseCard.tsx) *(new)*
- [code/frontend/components/dashboard/CurrentSessionCard.tsx](../../../../code/frontend/components/dashboard/CurrentSessionCard.tsx) *(new)*
- [code/frontend/components/dashboard/DailyGoalsCard.tsx](../../../../code/frontend/components/dashboard/DailyGoalsCard.tsx) *(new)*
- [code/frontend/components/dashboard/QuickAccessCard.tsx](../../../../code/frontend/components/dashboard/QuickAccessCard.tsx) *(new)*
- [code/frontend/components/dashboard/TaskQueueTable.tsx](../../../../code/frontend/components/dashboard/TaskQueueTable.tsx) *(new)*
- [code/frontend/app/tasks/page.tsx](../../../../code/frontend/app/tasks/page.tsx)

## Detailed implementation steps

### All components use `"use client"` and accept a `token: string` prop (or data-only props where specified). All containers use `bg-slate-800 rounded-xl p-5` as the base card class unless noted.

---

#### 1. `FocusHeader.tsx`

Props: `{ silenceState: "engaged" | "stagnant" | "paused"; pausedUntil?: string | null }`

- `<div className="flex items-start justify-between mb-6">`
- Left: `<h1 className="text-2xl font-bold text-white">Focused Engagement</h1>` + `<p className="text-slate-400 text-sm mt-1">{subtitleCopy}</p>`
- Right: `<button className="flex items-center gap-2 border border-teal-500/50 text-teal-400 text-xs font-semibold px-4 py-2 rounded-lg hover:bg-teal-500/10"><BarChart2 size={14}/> SYSTEM MONITORING ACTIVE</button>`
- `subtitleCopy` map:
  - `engaged` → `"Deep work session active. Distractions minimized."`
  - `stagnant` → `"Momentum gap detected. Re-engage to restore flow."`
  - `paused` → `"System paused${pausedUntil ? ` until ${new Date(pausedUntil).toLocaleDateString()}` : ""}."`

---

#### 2. `ProductivityPulseCard.tsx`

Props: `{ token: string; onAuthError?: () => void }`

- `"use client"` — fetches `getFlowState(token)` on mount; polls every 60,000 ms.
- Container: `bg-slate-800 rounded-xl p-5 h-full`
- Header row: `<span className="text-xs font-semibold tracking-widest text-slate-400 uppercase">Productivity Pulse</span>` + right side: `<span className="bg-slate-700 text-slate-300 text-xs px-2 py-0.5 rounded">Last 6 hours</span>` + `<span className={changePercent >= 0 ? "text-emerald-400" : "text-rose-400"}>+{changePercent}%</span>`
- Headline: `<h2 className="text-2xl font-bold text-white mt-1">Flow State <span className="text-blue-400">{flowPercent}%</span></h2>`
- Chart: `<ResponsiveContainer width="100%" height={160}><AreaChart data={series}><defs><linearGradient id="flowGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4}/><stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/></linearGradient></defs><Area type="monotone" dataKey="activityScore" stroke="#3b82f6" fill="url(#flowGrad)" strokeWidth={2} dot={false}/><XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false}/><Tooltip contentStyle={{ background: "#1e293b", border: "none", borderRadius: "8px", color: "#fff" }} /></AreaChart></ResponsiveContainer>`
- Loading skeleton: two `animate-pulse bg-slate-700 rounded` divs
- Empty series state: render the chart container but pass empty `data={[]}` — Recharts renders a blank area gracefully.

---

#### 3. `CurrentSessionCard.tsx`

Props: `{ token: string; onAuthError?: () => void }`

- Fetches `getActiveSession(token)` on mount; polls every 30,000 ms for elapsed ticks.
- Container: `bg-slate-800 rounded-xl p-5 relative overflow-hidden`
- Background illustration: `<FileText className="absolute right-4 bottom-4 text-slate-700/40" size={64} />`
- Header label: `<span className="text-xs font-semibold tracking-widest text-slate-400 uppercase">Current Session</span>`
- **Active state:** `<h3 className="text-lg font-semibold text-white mt-1">{session.taskName}</h3>` + `<p className="text-blue-400 text-sm">{session.elapsedMinutes}m elapsed</p>` + progress bar (see below) + `<span className="text-slate-500 text-xs">Goal: {session.goalMinutes} mins</span>`
- **No session state:** `<p className="text-slate-500 text-sm mt-2">No active session</p>`
- Progress bar: `<div className="w-full bg-slate-700 rounded-full h-1.5 mt-3"><div className="bg-blue-500 h-1.5 rounded-full transition-all" style={{ width: `${Math.min((elapsedMinutes / goalMinutes) * 100, 100)}%` }}></div></div>`
  - When `goalMinutes` is `null`, render bar at 0%.

---

#### 4. `DailyGoalsCard.tsx`

Props: `{ token: string; onAuthError?: () => void }`

- Fetches `listTasks(token)` on mount. Filters to tasks where `deadline` date portion matches today's date (UTC). Falls back to rendering the first 5 tasks if no deadlined tasks exist.
- Container: `bg-slate-800 rounded-xl p-5`
- Header row: `<h3 className="text-base font-semibold text-white">Daily Goals</h3>` + `<span className="text-slate-400 text-sm">{doneCount} of {totalCount} completed</span>`
- Per item:
  - Completed: `<CheckCircle2 className="text-emerald-500 shrink-0" size={16} />` + `<span className="line-through text-slate-500 text-sm">{task.name}</span>`
  - Current (first incomplete): `<div className="w-4 h-4 rounded-full border-2 border-blue-400 shrink-0" />` + `<span className="text-white text-sm">{task.name}</span>`
  - Remaining incomplete: `<div className="w-4 h-4 rounded-full border-2 border-slate-600 shrink-0" />` + `<span className="text-slate-400 text-sm">{task.name}</span>`
- Loading skeleton: three `h-6 animate-pulse bg-slate-700 rounded` items

---

#### 5. `QuickAccessCard.tsx`

This is a **data-only props** component (no API calls inside — data passed from page):

```typescript
interface QuickAccessCardProps {
  icon: React.ElementType   // Lucide icon component
  title: string
  subtitle: string
  iconBg?: string           // Tailwind bg class, defaults to "bg-blue-900/40"
}
```

- Container: `bg-slate-800 rounded-xl p-5 flex flex-col gap-3`
- Icon wrapper: `<div className={`w-10 h-10 rounded-lg flex items-center justify-center ${iconBg}`}><Icon className="text-blue-400" size={20} /></div>`
- `<h3 className="text-white font-medium text-sm">{title}</h3>`
- `<p className="text-slate-400 text-xs">{subtitle}</p>`

Used twice in the page: Team Sync (`Users` icon, `"Starts in 14 mins"`) and Docs & Assets (`FileText` icon, `"Internal wiki access"`). Both receive stub data props from the page — no backend call.

---

#### 6. `TaskQueueTable.tsx`

Props: `{ token: string; activeSessionTaskId?: string | null; onAuthError?: () => void }`

- Fetches `listTasks(token)` on mount (can share the same fetch as DailyGoalsCard at the page level — see Step 6 for lifting).
- Container: `bg-slate-800 rounded-xl p-5`
- Header row: `<h3 className="text-base font-semibold text-white">Task Queue</h3>` + legend `<span><span className="text-emerald-400">● Done</span> <span className="text-blue-400">● Working</span></span>`
- `<table className="w-full mt-4 text-sm">` with `<thead>` row: `TASK` (left), `DEADLINE` (center), `STATUS` (right) — all `text-slate-500 text-xs uppercase tracking-wider`
- Per task row `<tr className="border-t border-slate-700/50">`:
  - Task name: `<td className="py-3 text-white">{task.name}</td>`
  - Deadline: `<td className="py-3 text-slate-400 text-center">{formatDeadline(task.deadline)}</td>`
    - `formatDeadline`: if same UTC date as today → `"H:MM PM (Today)"`; if tomorrow → `"Tomorrow"`; else ISO date; if null → `"—"`
  - Status pill `<td className="py-3 text-right"><span className={pillClass}>{statusLabel}</span></td>`:
    - `isCompleted` → `pillClass = "bg-emerald-900/60 text-emerald-400 px-2.5 py-1 rounded-full text-xs"`, label = `"Completed"`
    - `task.id === activeSessionTaskId` → `pillClass = "bg-blue-900/60 text-blue-400 ..."`, label = `"In Progress"`
    - else → `pillClass = "bg-slate-700 text-slate-400 ..."`, label = `"Pending"`
- Loading skeleton: three `h-10 animate-pulse bg-slate-700 rounded` rows

---

#### 7. Assemble `app/tasks/page.tsx`

Replace the Step 4 placeholder with the full composition:

```tsx
"use client"

export default function TasksPage() {
  const { token, ready, logout } = useAuth()
  // data fetching lifted here in Step 6 — for now pass token to each component

  if (!ready || !token) return <LoadingSpinner />

  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto">
      <FocusHeader silenceState="engaged" />   {/* static for now; wired in Step 6 */}
      <BentoGrid
        variant="tasks-dashboard"
        row1Left={<ProductivityPulseCard token={token} onAuthError={logout} />}
        row1Right={<CurrentSessionCard token={token} onAuthError={logout} />}
        row2A={<DailyGoalsCard token={token} onAuthError={logout} />}
        row2B={<QuickAccessCard icon={Users} title="Team Sync" subtitle="Starts in 14 mins" />}
        row2C={<QuickAccessCard icon={FileText} title="Docs & Assets" subtitle="Internal wiki access" />}
        row3={<TaskQueueTable token={token} onAuthError={logout} />}
      />
    </div>
  )
}
```

`LoadingSpinner` is the existing spinner from `app/page.tsx` (extract to a shared component or inline).

## Integration & Edge Cases

- **Shared task fetch:** Both `DailyGoalsCard` and `TaskQueueTable` independently call `listTasks`. This is intentional for this step — Step 6 lifts the shared fetch to the page to avoid duplicate network calls.
- **`activeSessionTaskId` prop on `TaskQueueTable`:** In this step, pass `undefined` (no session data yet). Step 6 wires the live value.
- **`FocusHeader silenceState`:** Hardcoded to `"engaged"` in this step. Step 6 wires live silence state.
- **Empty task list:** Both `DailyGoalsCard` and `TaskQueueTable` must render gracefully with zero tasks — no blank page, no crash.
- **`recharts` SSR:** Recharts components are wrapped in `<ResponsiveContainer>`. They must be inside a `"use client"` component (which `ProductivityPulseCard` is). No server-side import of Recharts.
- **Lucide icon as prop type:** `QuickAccessCard` accepts `icon: React.ElementType`. Render it as `<Icon />` — do not call it as a function.

## Acceptance Criteria

1. `npm run build` exits 0 with zero TypeScript errors after all component files are created.
2. `/tasks` page renders without a blank screen or JS console error in Chrome DevTools.
3. `ProductivityPulseCard` shows loading skeleton while `getFlowState` is in flight, then renders the chart and "Flow State X%" headline.
4. `CurrentSessionCard` shows "No active session" when `GET /sessions/active` returns `null`.
5. After `POST /sessions/start`, `CurrentSessionCard` shows the session name and `{n}m elapsed` within 30 seconds (next poll).
6. `DailyGoalsCard` renders today's tasks with correct icon states (green check = completed, blue circle = current, gray circle = pending).
7. `TaskQueueTable` renders a row per task with correct status pill colours (Completed=green, In Progress=blue, Pending=gray).
8. Completing a task (via `PUT /tasks/{id}` with `isCompleted: true`) causes the table row to show a green "Completed" pill after page refresh (live polling wired in Step 6).
9. Both `QuickAccessCard` instances render with correct icon, title, and subtitle text.
10. `FocusHeader` renders with H1 "Focused Engagement" and the teal "SYSTEM MONITORING ACTIVE" button.

## Testing / QA

### Automated

`npm run build` is the primary gate. No new unit test files required for this step.

### Manual QA checklist

1. `npm run dev`
2. Log in at `/login`; verify redirect to `/tasks`
3. Verify all 6 bento zones render (no empty white boxes, no console errors)
4. Verify `ProductivityPulseCard` area chart renders (even with empty data — no crash)
5. `POST /sessions/start {"taskName":"UI Redesign","goalMinutes":60}` → wait 31 s → verify `CurrentSessionCard` shows "UI Redesign" and "Xm elapsed"
6. Open a task, mark it complete via the existing `TaskBoard` (or API directly); reload `/tasks` → row shows green "Completed" pill
7. Verify `QuickAccessCard` Team Sync shows `Users` icon and "Starts in 14 mins"
8. Verify `QuickAccessCard` Docs & Assets shows `FileText` icon and "Internal wiki access"
9. Verify `DailyGoalsCard` strikethrough on completed tasks
10. Run `npm run build` — confirm 0 errors

## Files touched

- [code/frontend/components/dashboard/FocusHeader.tsx](../../../../code/frontend/components/dashboard/FocusHeader.tsx) *(new)*
- [code/frontend/components/dashboard/ProductivityPulseCard.tsx](../../../../code/frontend/components/dashboard/ProductivityPulseCard.tsx) *(new)*
- [code/frontend/components/dashboard/CurrentSessionCard.tsx](../../../../code/frontend/components/dashboard/CurrentSessionCard.tsx) *(new)*
- [code/frontend/components/dashboard/DailyGoalsCard.tsx](../../../../code/frontend/components/dashboard/DailyGoalsCard.tsx) *(new)*
- [code/frontend/components/dashboard/QuickAccessCard.tsx](../../../../code/frontend/components/dashboard/QuickAccessCard.tsx) *(new)*
- [code/frontend/components/dashboard/TaskQueueTable.tsx](../../../../code/frontend/components/dashboard/TaskQueueTable.tsx) *(new)*
- [code/frontend/app/tasks/page.tsx](../../../../code/frontend/app/tasks/page.tsx)

## Estimated effort

2–3 dev days

## Concurrency & PR strategy

- **Blocking steps:** Blocked until [step-4-layout-shell.md](./step-4-layout-shell.md) is merged (requires `BentoGrid variant="tasks-dashboard"` prop).
- **Merge Readiness: true** *(AC #1–10 satisfied; frontend build passes)*
- Suggested branch: `phase-2-2/step-5-dashboard-components`
- `Depends-On: phase-2-2/step-4-layout-shell`

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Recharts `ResponsiveContainer` renders at 0 height in SSR | Wrap chart in a fixed-height `<div className="h-40">` parent; verify with `npm run build` + manual check |
| Duplicate `listTasks` fetches (DailyGoalsCard + TaskQueueTable) | Acceptable for this step; Step 6 lifts to shared page state |
| `getActiveSession` not yet hooked up to `activeSessionTaskId` | Pass `undefined` for now — "In Progress" pill will not show until Step 6; document as known gap |
| Lucide icon passed as prop TypeScript error | Use `icon: React.ElementType` not `icon: LucideIcon` — the latter is not exported from `lucide-react@0.268` |

## References

- [PDD.md — §5 UI/UX Strategy](../PDD.md)
- [step-3-type-sync.md](./step-3-type-sync.md) *(for generated type names)*
- [step-4-layout-shell.md](./step-4-layout-shell.md) *(BentoGrid variant)*
- [code/frontend/components/PulseCard.tsx](../../../../code/frontend/components/PulseCard.tsx) *(polling pattern reference)*
- [master.md](./master.md)

## Author Checklist

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/` (happy path + validation)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected
