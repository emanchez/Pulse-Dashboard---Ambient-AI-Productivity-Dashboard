# Step 6 — Sunday Synthesis Modal & Task Suggestion UI

## Purpose

Build the frontend for the Sunday Synthesis experience: a dedicated page (or modal overlay) that displays the AI-generated weekly narrative, theme, commitment score, and task suggestions with accept/reject interactions. This is the primary user-facing surface for Phase 4's AI features.

## Deliverables

- `/synthesis` page route (new Next.js page)
- `SynthesisPage` component — orchestrates the synthesis experience
- `SynthesisCard` component — shows narrative, theme, and commitment score using the existing `data-state` / CSS variable theming system (`engaged` / `stagnant` / `paused`)
- `CommitmentGauge` component — 10-segment horizontal bar using `var(--accent-primary)` for filled segments and `bg-slate-700` for empty, matching the accent-transition pattern
- `TaskSuggestionList` component — task suggestions with Accept/Dismiss using the same priority-color tokens as `TaskQueueTable` (`text-red-400` / `text-amber-400` / `text-emerald-400`)
- `SynthesisTrigger` component — `bg-blue-600 hover:bg-blue-700` primary CTA with loading skeleton state
- Navigation link in `AppNavBar` to `/synthesis` using the existing `tabClass` pattern and `Brain` Lucide icon
- API wrappers in `lib/api.ts` for synthesis and task suggestion endpoints
- Loading skeletons (`animate-pulse bg-slate-700 rounded`), error, and empty states for all components

## Primary files to change (required)

- [code/frontend/app/synthesis/page.tsx](code/frontend/app/synthesis/page.tsx) (new)
- [code/frontend/components/synthesis/SynthesisCard.tsx](code/frontend/components/synthesis/SynthesisCard.tsx) (new)
- [code/frontend/components/synthesis/CommitmentGauge.tsx](code/frontend/components/synthesis/CommitmentGauge.tsx) (new)
- [code/frontend/components/synthesis/TaskSuggestionList.tsx](code/frontend/components/synthesis/TaskSuggestionList.tsx) (new)
- [code/frontend/components/synthesis/SynthesisTrigger.tsx](code/frontend/components/synthesis/SynthesisTrigger.tsx) (new)
- [code/frontend/components/nav/AppNavBar.tsx](code/frontend/components/nav/AppNavBar.tsx) (add link)
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts) (add AI endpoint wrappers)

## Design System Reference (Required Reading before coding)

This page must feel like a native extension of the existing app. Do **not** introduce new colors, shadows, or layout primitives. Use only what is already in the codebase.

**Page shell:** `<div className="bg-slate-900 min-h-screen">`. Content area: `max-w-3xl mx-auto px-4 py-8 md:px-6`.

**Standard card:** `bg-slate-800 rounded-xl p-5` — used by `DailyGoalsCard`, `TaskQueueTable`, `ProductivityPulseCard`.

**Featured / expanded card (synthesis result):** `bg-slate-800/50 border border-slate-700 rounded-xl p-6 border-l-4 border-l-accent-primary accent-transition` — identical to `ReportCard`'s expanded state. The left border is driven by `var(--accent-primary)` so it shifts color with `data-state`.

**State-aware theming via `data-state` attribute:** Wrap `SynthesisCard` in a container with `data-state={scoreToState(commitmentScore)}`. Do NOT hardcode `emerald-`, `amber-`, or `red-` utility classes for state-driven colors — instead use the CSS variable tokens defined in `globals.css`:
- `text-accent-light accent-transition` — colored text (score number, section label)
- `bg-accent-bg` / `border-accent-border` / `border-l-accent-primary` — fills and borders
- `data-state="engaged"` (score 7–10) → emerald palette
- `data-state="stagnant"` (score 4–6) → amber palette
- `data-state="paused"` (score 1–3) → sky-blue palette (not red — the design system has no red state)

**Section labels:** `text-accent-light text-xs font-bold tracking-widest uppercase mb-3 accent-transition` — matches "STRATEGIC NARRATIVE" in `ReportCard`.

**Badge pills:** `bg-accent-bg text-accent-light text-xs font-medium px-2 py-0.5 rounded accent-transition` — matches the "LATEST" badge in `ReportCard`.

**Priority color tokens** (from `TaskQueueTable`):
- High: `text-red-400`, `bg-red-500/20 border border-red-500/30`
- Medium: `text-amber-400`, `bg-amber-500/20 border border-amber-500/30`
- Low: `text-emerald-400`, `bg-emerald-500/20 border border-emerald-500/30`

**Buttons:**
- Primary action: `bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded-md transition-colors`
- Secondary/Dismiss: `bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-1.5 rounded-md transition-colors`
- Destructive inline: `text-slate-500 hover:text-red-400 transition-colors text-sm`

**Loading skeleton:** `<div className="h-6 w-1/3 animate-pulse bg-slate-700 rounded" />` — same pattern as `ProductivityPulseCard`'s null state.

**Re-entry banner:** `bg-sky-500/10 border border-sky-500/30 rounded-lg px-4 py-3 text-sky-300 text-sm` — consistent with the `paused` badge in `AppNavBar`.

**Inline success feedback (after Accept):** Replace row content with a `text-emerald-400 text-sm flex items-center gap-2` with a `CheckCircle2` icon — same pattern as `DailyGoalsCard`. No external toast library.

**Icons (Lucide React only):** `Brain` (page header + nav), `Sparkles` (trigger button), `CheckCircle2` (inline accept success), `ChevronRight` (expandable rationale), `Loader2` (spinner with `animate-spin`), `AlertTriangle` (error state).

## Detailed implementation steps

1. **Add API wrappers to `lib/api.ts`:**
   ```typescript
   // Synthesis
   export async function triggerSynthesis(): Promise<{ id: number; status: string }> {
     return post('/ai/synthesis', {});
   }
   
   export async function getLatestSynthesis(): Promise<SynthesisResponse> {
     return get('/ai/synthesis/latest');
   }
   
   export async function getSynthesis(id: number): Promise<SynthesisResponse> {
     return get(`/ai/synthesis/${id}`);
   }
   
   // Task Suggestions
   export async function suggestTasks(focusArea?: string): Promise<TaskSuggestionResponse> {
     return post('/ai/suggest-tasks', { focusArea });
   }
   
   export async function acceptTasks(tasks: AcceptedTask[]): Promise<{ createdTaskIds: number[] }> {
     return post('/ai/accept-tasks', { tasks });
   }
   ```

2. **Create `SynthesisCard` component:**
   - Root element: `<div data-state={scoreToState(commitmentScore)} className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 border-l-4 border-l-accent-primary accent-transition">`
   - `scoreToState` helper: `(s: number) => s >= 7 ? 'engaged' : s >= 4 ? 'stagnant' : 'paused'`
   - Top row: title `text-xl font-bold text-white` + state badge `bg-accent-bg text-accent-light text-xs font-medium px-2 py-0.5 rounded accent-transition` ("ENGAGED" / "NEEDS ATTENTION" / "LOW MOMENTUM") + `createdAt` date in `text-slate-400 text-sm`
   - Section label: `text-accent-light text-xs font-bold tracking-widest uppercase mb-3 accent-transition` with text "WEEKLY SYNTHESIS"
   - Narrative body: `text-slate-300 text-sm leading-relaxed`
   - Theme: rendered as a pill below the narrative — `bg-slate-700 text-slate-300 text-xs px-2 py-0.5 rounded` (neutral, no state color — matches the "Last 6 hours" chip in `ProductivityPulseCard`)
   - Below theme: `CommitmentGauge` component
   - Layout: single column on mobile, `grid grid-cols-3 gap-6` on `md:` — narrative spans `col-span-2`, theme+gauge in `col-span-1` sidebar (mirrors `ReportCard`'s 2/1 split)

3. **Create `CommitmentGauge` component:**
   - The gauge sits inside a `data-state` container (inherited from `SynthesisCard`) so CSS variable resolution happens automatically.
   - Structure: `<div role="meter" aria-valuemin={1} aria-valuemax={10} aria-valuenow={score} aria-label={`Commitment score: ${score} out of 10`}>`
   - 10 segment divs in a `flex gap-1` row. Each: `h-2 flex-1 rounded-full transition-colors duration-300`
   - Filled segments (index < score): `bg-[var(--accent-primary)]`
   - Empty segments: `bg-slate-700`
   - Below segments: `<span className="text-accent-light text-2xl font-bold accent-transition">{score}</span><span className="text-slate-400 text-sm">/10</span>` — same visual weight as the "94%" in `ProductivityPulseCard`
   - No external animation library — CSS `transition-colors duration-300` is sufficient.

4. **Create `TaskSuggestionList` component:**
   ```tsx
   interface TaskSuggestionListProps {
     suggestions: SuggestedTask[];
     isReEntryMode: boolean;
     onAccept: (task: SuggestedTask) => Promise<void>;
     onDismiss: (index: number) => void;
   }
   ```
   - Container: `bg-slate-800 rounded-xl p-5` (standard card)
   - Section header row: `<h3 className="text-base font-semibold text-white">Task Suggestions</h3>`
   - **Re-entry banner (when `isReEntryMode` is true):** `<div className="bg-sky-500/10 border border-sky-500/30 rounded-lg px-4 py-3 text-sky-300 text-sm mb-4">` with `Brain` icon — identical palette to the `paused` nav badge in `AppNavBar`.
   - Each suggestion row: `flex items-start gap-3 py-3 border-b border-slate-700 last:border-0`
     - Priority pill: same `PRIORITY_COLORS` map as `TaskQueueTable` but rendered as background pill: `bg-red-500/20 text-red-400 text-xs border border-red-500/30 px-2 py-0.5 rounded` (High), amber/low equivalents
     - `isLowFriction` badge: `bg-sky-500/20 text-sky-400 text-xs border border-sky-500/30 px-2 py-0.5 rounded` — visually distinct, no state collision
     - Rationale: collapsed by default, toggled by a `ChevronRight` icon that rotates on expand (`transition-transform`). Content: `text-slate-400 text-sm mt-1`
     - **Accept button:** `bg-blue-600 hover:bg-blue-700 text-white text-sm px-3 py-1.5 rounded-md transition-colors`
     - **Dismiss button:** `bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-1.5 rounded-md transition-colors`
     - **After accept (row success state):** Replace Accept/Dismiss with `<span className="flex items-center gap-1.5 text-emerald-400 text-sm"><CheckCircle2 size={14} /> Added to queue</span>` — no external toast library
   - "Accept All" button: `bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-md transition-colors mt-4 w-full` — shown only when ≥ 2 pendingsuggestions remain
   - Empty state: `<p className="text-slate-400 text-sm text-center py-4">Trigger a synthesis to generate task recommendations.</p>`

5. **Create `SynthesisTrigger` component:**
   - Idle: `<button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-md transition-colors">` with `<Sparkles size={16} />` icon and "Generate Weekly Synthesis" label
   - Loading: button disabled + `opacity-75 cursor-not-allowed`. Replace icon with `<Loader2 size={16} className="animate-spin" />`. Label: "Analyzing your week…". Below the button: `<p className="text-slate-400 text-xs mt-2 text-center">This usually takes 30–60 seconds.</p>`
   - Timeout (> `oz_max_wait_seconds`): replace loading with `<p className="text-amber-400 text-sm flex items-center gap-2"><AlertTriangle size={14} /> Synthesis is taking longer than expected. Check back shortly.</p>` — uses `text-amber-400` consistent with stagnant-state accents
   - Error: `<p className="text-red-400 text-sm">{errorMessage}</p>` + a secondary "Try again" link-button (`text-slate-400 hover:text-slate-200 underline text-sm`)
   - Disabled when `status === 'INPROGRESS'` on the latest synthesis poll result (prevent double-trigger)
   - Wrap in `bg-slate-800 rounded-xl p-5 flex flex-col items-center gap-2` so it renders as its own Bento card

6. **Create `/synthesis` page:**
   ```tsx
   export default function SynthesisPage() {
     // Same auth pattern as tasks/reports pages:
     // const { token, ready, logout } = useAuth()
     // const { silenceState, gapMinutes } = useSilenceState()
     // if (!ready) return <LoadingSpinner />
     // if (!token) { redirect('/login'); return null }
     
     // On mount: fetch latest synthesis via getLatestSynthesis()
     // If exists: display SynthesisCard + TaskSuggestionList
     // If none: show first-time empty state with prominent SynthesisTrigger
     // Always render SynthesisTrigger below/after the SynthesisCard for re-generation
   }
   ```
   - Page shell: `<div className="bg-slate-900 min-h-screen">` → `<AppNavBar />` → `<main className="max-w-3xl mx-auto px-4 py-8 md:px-6">`
   - Page header: `<div className="flex items-center gap-3 mb-6"><Brain className="text-accent-light accent-transition" size={24} /><div><h1 className="text-2xl font-bold text-white">Sunday Synthesis</h1><p className="text-sm text-slate-400">AI-generated weekly narrative and task recommendations.</p></div></div>` — matches the "Strategic Reports" header style from the concept
   - Loading state (initial fetch): render 3 `animate-pulse bg-slate-700 rounded-xl h-32` skeleton divs in a `space-y-4` stack — mirrors `ProductivityPulseCard`'s null branch
   - First-time empty state (no synthesis ever): `bg-slate-800 rounded-xl p-8 text-center` with `<Brain className="text-slate-600 mx-auto mb-4" size={40} />`, `<p className="text-slate-400 mb-4">No synthesis yet. Generate your first weekly report.</p>` and the `SynthesisTrigger` centered inside
   - Normal state: vertical `space-y-4` stack — `SynthesisTrigger` → `SynthesisCard` → `TaskSuggestionList`
   - AI usage status bar: small `text-xs text-slate-500` line beneath the trigger showing `{used}/{limit} synthesis runs used this week` — sourced from `GET /ai/usage` (Step 1). Keeps the developer aware of credit spend.

7. **Add nav link in `AppNavBar.tsx`:**
   - Import `Brain` from `lucide-react` alongside the existing imports.
   - In the Center tabs `div`, add a `<Link>` using the **exact same `tabClass(path)` helper** as the existing Tasks/Reports links:
     ```tsx
     <Link href="/synthesis" className={tabClass("/synthesis")}>
       Synthesis
     </Link>
     ```
   - Position: between "Tasks" and "Reports" to reflect the workflow order.
   - Do **not** add an icon inside the tab itself — existing tabs (Tasks, Reports) are text-only. Keep it consistent.
   - The `AppNavBar` props interface and render logic do not change — no new props needed.

## Integration & Edge Cases

- **Auth redirect:** `useAuth()` + redirect to `/login` if no token — same pattern as `app/tasks/page.tsx` and `app/reports/page.tsx`.
- **503 from backend (AI disabled):** Catch HTTP 503 and show `<div className="bg-slate-800 rounded-xl p-6 text-center"><p className="text-slate-400">AI features are currently disabled.</p></div>` — no raw error object exposed to the UI.
- **429 from backend (rate limit):** Catch HTTP 429 and display the reset message from the response body in `text-amber-400 text-sm` — the backend returns `"Synthesis limit reached (3/week). Next reset: <date>."` as per Step 1.
- **OZ timeout (> 90s):** Frontend polls `GET /ai/synthesis/{id}` every 5s after triggering. If status remains non-terminal after `oz_max_wait_seconds`, show the `AlertTriangle` timeout message in `SynthesisTrigger` and stop polling.
- **Stale data:** After accepting a task suggestion, `/tasks` page reflects it on next visit — no real-time sync needed.
- **No new CSS or libraries:** All styling uses only existing `globals.css` CSS variables and Tailwind tokens already in the project. No new Tailwind plugins or animation libraries.
- **Re-entry banner:** Uses `bg-sky-500/10 border border-sky-500/30 text-sky-300` — the exact same palette as the `paused` state badge in `AppNavBar`, so no new color token is introduced.
- **`data-state` scoping:** Apply `data-state` only on `SynthesisCard`'s root div. Do not apply it on the page wrapper — it would incorrectly re-theme the nav badge.

## Acceptance Criteria (required)

1. `/synthesis` route renders without errors when navigated to while authenticated.
2. `SynthesisTrigger` renders a `bg-blue-600` button with a `Sparkles` icon in idle state.
3. `SynthesisTrigger` shows a `Loader2 animate-spin` spinner and disables itself during loading.
4. After synthesis completes, `SynthesisCard` displays `summary`, `theme`, and `commitmentScore`.
5. `SynthesisCard` root element has `data-state="engaged"` when score ≥ 7, `data-state="stagnant"` when 4–6, `data-state="paused"` when ≤ 3.
6. `SynthesisCard` left border color changes with `data-state` (emerald / amber / sky-blue) via `border-l-accent-primary`.
7. `CommitmentGauge` renders 10 segments; segments ≤ score use `bg-[var(--accent-primary)]`, rest use `bg-slate-700`.
8. `CommitmentGauge` has `role="meter"` with correct `aria-valuenow`, `aria-valuemin`, `aria-valuemax`.
9. `TaskSuggestionList` renders suggestions with priority pills matching the `PRIORITY_COLORS` token map (red/amber/emerald).
10. Clicking "Accept" calls `POST /ai/accept-tasks`, then replaces the row with a `CheckCircle2 text-emerald-400` inline success state.
11. Clicking "Dismiss" removes the item client-side without an API call.
12. Re-entry mode renders a `bg-sky-500/10 border-sky-500/30 text-sky-300` banner (no raw `#` hex colors).
13. Empty state uses a standard `bg-slate-800 rounded-xl p-8 text-center` card identical in structure to `TaskQueueTable`'s empty state.
14. A "Synthesis" link appears in `AppNavBar` between Tasks and Reports using `tabClass("/synthesis")`.
15. AI usage status (`{used}/{limit}` this week) is shown beneath `SynthesisTrigger` from `GET /ai/usage`.
16. HTTP 429 response shows the reset-date message in `text-amber-400`.
17. HTTP 503 response shows a friendly disabled message — no raw error string exposed.
18. `npm run build` exits 0 with no TypeScript errors.

## Testing / QA (required)

**No automated frontend tests** (consistent with Phase 1–3 pattern; frontend testing debt acknowledged in master plan).

**Manual QA checklist:**
1. Navigate to `/synthesis` while logged in → verify page renders with `bg-slate-900` background and "Sunday Synthesis" header with `Brain` icon.
2. Click "Generate Weekly Synthesis" → verify `Sparkles` icon replaced by `Loader2 animate-spin`, button disabled, and "Analyzing your week…" text visible.
3. Wait for completion → verify `SynthesisCard` appears with left colored border and state badge (e.g., "ENGAGED" in emerald).
4. Verify commitment gauge shows correct filled segments with `var(--accent-primary)` color matching the left border.
5. Verify theme rendered as a `bg-slate-700 text-slate-300` neutral pill.
6. Check task suggestions render with priority pills (red/amber/emerald) and expand/collapse rationale via `ChevronRight`.
7. Click "Accept" on a suggestion → verify row changes to `CheckCircle2 text-emerald-400 "Added to queue"` (no modal/toast).
8. Click "Dismiss" → verify item removed with no API call (check Network tab).
9. Navigate to `/tasks` → verify accepted task appears.
10. Resize to 375px width → verify layout is single-column and all buttons are finger-friendly (≥ 40px tap target).
11. Navigate to `/synthesis` without auth token → verify redirect to `/login`.
12. Set `AI_ENABLED=false` in backend `.env`, restart → verify friendly `text-slate-400` disabled message, not a stack trace.
13. With rate limit exhausted (3 synthesis entries this week in DB): click trigger → verify `text-amber-400` message with reset date.
14. Verify `AppNavBar` shows "Synthesis" tab with correct active underline (`border-b-2 border-blue-500`) when on `/synthesis`.

## Files touched (repeat for reviewers)

- [code/frontend/app/synthesis/page.tsx](code/frontend/app/synthesis/page.tsx) (new)
- [code/frontend/components/synthesis/SynthesisCard.tsx](code/frontend/components/synthesis/SynthesisCard.tsx) (new)
- [code/frontend/components/synthesis/CommitmentGauge.tsx](code/frontend/components/synthesis/CommitmentGauge.tsx) (new)
- [code/frontend/components/synthesis/TaskSuggestionList.tsx](code/frontend/components/synthesis/TaskSuggestionList.tsx) (new)
- [code/frontend/components/synthesis/SynthesisTrigger.tsx](code/frontend/components/synthesis/SynthesisTrigger.tsx) (new)
- [code/frontend/components/nav/AppNavBar.tsx](code/frontend/components/nav/AppNavBar.tsx)
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts)

## Estimated effort

2–3 dev days

## Concurrency & PR strategy

- **Blocking steps:**
  - `Blocked until: .github/artifacts/phase4/plan/step-3-sunday-synthesis.md` (synthesis endpoints must exist)
- **Merge Readiness:** false (draft)
- **Branch:** `phase-4/step-6-synthesis-ui`
- **Parallelizable with:** Step 5 (Ghost List) — no dependency between them.
- Step 7 depends on this step being merged or near-final (nav patterns, API wrapper patterns).

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| OZ response takes too long, user abandons | Loading state with time estimate. Synthesis result is stored — user can return later to see it. |
| Task acceptance fails (API error) | Per-item error handling. Failed accept shows inline error with retry. Other items remain actionable. |
| Commitment gauge is not accessible | Add `aria-label`, role="meter", `aria-valuemin/max/now` attributes. |

## References

- [product.md](../../product.md) — UI zones, state-aware styling (Engaged/Stagnant/Paused), Bento Grid
- [PDD.md](../../PDD.md) — §5 UI/UX Strategy, §3.4 Sunday Synthesis, §4.2 Dynamic Ambiguity Guard
- [step-3-sunday-synthesis.md](./step-3-sunday-synthesis.md) — Backend endpoints consumed by this step
- [step-4-task-suggester-co-planning.md](./step-4-task-suggester-co-planning.md) — Task suggestion and accept endpoints

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
