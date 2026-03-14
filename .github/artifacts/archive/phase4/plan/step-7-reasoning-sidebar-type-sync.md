# Step 7 — Reasoning Sidebar, Inference Cards, Type Sync & Integration Testing

## Purpose

Build the Reasoning Sidebar (Zone C from the PDD), integrate Ghost List visualization and Co-Planning inference cards into the Tasks dashboard, regenerate the TypeScript client for all new endpoints, and write end-to-end integration tests for the complete Phase 4 pipeline.

## Deliverables

- **Reasoning Sidebar** component integrated into the Tasks page Bento Grid
- **Inference Cards**: Co-Planning question cards, stuck-point detection, re-entry mode banner
- **Ghost List Panel**: visual list of wheel-spinning tasks with "Review" action
- **Type Sync**: regenerated `types.gen.ts` and `pulseClient.ts` covering all Phase 4 endpoints
- **API wrappers** in `lib/api.ts` for ghost list and co-planning
- **E2E integration test**: full flow from login → synthesis → accept task → ghost list
- **Co-Planning trigger** on the Reports page: "Analyze for conflicts" button on each report card

## Primary files to change (required)

- [code/frontend/components/dashboard/ReasoningSidebar.tsx](code/frontend/components/dashboard/ReasoningSidebar.tsx) (new)
- [code/frontend/components/dashboard/InferenceCard.tsx](code/frontend/components/dashboard/InferenceCard.tsx) (new)
- [code/frontend/components/dashboard/GhostListPanel.tsx](code/frontend/components/dashboard/GhostListPanel.tsx) (new)
- [code/frontend/components/dashboard/ReEntryBanner.tsx](code/frontend/components/dashboard/ReEntryBanner.tsx) (new)
- [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx) (integrate sidebar into Bento Grid)
- [code/frontend/components/reports/ReportCard.tsx](code/frontend/components/reports/ReportCard.tsx) (add co-plan button)
- [code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx) (add Zone C slot)
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts) (add ghost list and co-plan wrappers)
- [code/frontend/lib/generated/types.gen.ts](code/frontend/lib/generated/types.gen.ts) (regenerated)
- [code/frontend/lib/generated/pulseClient.ts](code/frontend/lib/generated/pulseClient.ts) (regenerated)
- [code/backend/tests/e2e/test_synthesis_flow.py](code/backend/tests/e2e/test_synthesis_flow.py) (new)

## Detailed implementation steps

1. **Regenerate TypeScript client:**
   ```bash
   cd code/frontend && bash lib/generate-client.sh
   ```
   - Verify new types include: `SynthesisResponse`, `SuggestedTask`, `TaskSuggestionResponse`, `CoPlanResponse`, `GhostTask`, `GhostListResponse`, `WeeklySummaryResponse`
   - Update `pulseClient.ts` base URL handling if needed (should use `NEXT_PUBLIC_API_BASE`)

2. **Add remaining API wrappers to `lib/api.ts`:**
   ```typescript
   // Ghost List
   export async function getGhostList(): Promise<GhostListResponse> {
     return get('/stats/ghost-list');
   }
   
   // Co-Planning
   export async function analyzeReport(reportId: number): Promise<CoPlanResponse> {
     return post('/ai/co-plan', { reportId });
   }
   
   // Weekly Summary
   export async function getWeeklySummary(): Promise<WeeklySummaryResponse> {
     return get('/stats/weekly-summary');
   }
   ```

3. **Create `ReasoningSidebar` component:**
   ```tsx
   // Zone C of the Bento Grid — right sidebar on desktop, bottom section on mobile
   interface ReasoningSidebarProps {
     userId: number; // for data fetching
   }
   
   export function ReasoningSidebar() {
     // Fetches on mount (independently, per-section error handling):
     // 1. Ghost list (/stats/ghost-list)
     // 2. Latest synthesis summary (/ai/synthesis/latest)
     // 3. AI usage caps (/ai/usage) — drives rate limit badges on action buttons
     
     // Renders:
     // - ReEntryBanner (conditional on synthesis context)
     // - InferenceCard(s) from latest synthesis insights
     // - GhostListPanel
     // - AI usage summary line: e.g. "Synthesis: 1/3 this week · Tasks: 2/5 today"
     //   rendered as text-xs text-slate-500 at the bottom of the sidebar
   }
   ```
   - Responsive layout: hidden on mobile (`hidden md:block`), appears as a right column (`md:col-span-1`) on desktop within the Bento Grid.
   - On mobile: accessible via a bottom sheet or collapsible section.

4. **Create `InferenceCard` component:**
   ```tsx
   interface InferenceCardProps {
     type: 'insight' | 'question' | 'warning';
     title: string;
     body: string;
     action?: { label: string; onClick: () => void };
   }
   ```
   - Use the existing design system palette — **no new color tokens**:
     - `insight`: `bg-slate-800 border border-slate-700 rounded-xl p-4` with `Lightbulb` Lucide icon in `text-slate-400`
     - `question`: `bg-amber-500/10 border border-amber-500/30 rounded-xl p-4` with `HelpCircle` icon in `text-amber-400` — matches the stagnant state palette already in `globals.css`
     - `warning`: `bg-red-500/10 border border-red-500/30 rounded-xl p-4` with `AlertTriangle` icon in `text-red-400`
   - Dismissable: "X" button stores dismissed state in `localStorage` (keyed by card content hash)

5. **Create `GhostListPanel` component:**
   - Displays ghost tasks as a compact list within the sidebar
   - Each item shows: task name, days open, ghost reason badge
   - "Review" action opens the task in the existing task editor
   - Empty state: "No wheel-spinning tasks detected. Keep it up!"
   - Header with `Ghost` icon (Lucide) and count badge

6. **Create `ReEntryBanner` component:**
   - Conditional banner at the top of the sidebar (or full-width on mobile)
   - Shows when the latest context indicates `is_returning_from_leave == True`
   - Sky Blue background, hand wave icon
   - Text: "Welcome back! Here are some low-friction tasks to ease you in."
   - Dismissable for the session

7. **Integrate into Tasks page Bento Grid:**
   - Current Tasks page uses a Bento Grid with Zones A (Pulse) and B (Tasks).
   - Add Zone C (Reasoning Sidebar) as a new grid column on desktop:
     ```tsx
     // Current: md:grid-cols-3 layout
     // Updated: md:grid-cols-4 with sidebar taking the rightmost column
     // Or: md:grid-cols-3 with sidebar below on smaller screens
     ```
   - The sidebar should be a separate grid area, not nested inside an existing card.

8. **Add Co-Plan button to `ReportCard`:**
   - Add an "Analyze" button (Lucide: `GitBranch`) to each report card using the secondary button style: `bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-1.5 rounded-md transition-colors`
   - On click: calls `POST /ai/co-plan` with the report ID
   - **Disabled with tooltip when co-plan daily limit is exhausted:** read current usage from the shared `usageData` state (fetched by `ReasoningSidebar` via `GET /ai/usage`). When `coplan.used >= coplan.limit`, render the button as `opacity-50 cursor-not-allowed` with `title="Daily co-plan limit reached. Resets tomorrow."` — no click handler fires.
   - Loading state while OZ processes: replace icon with `Loader2 animate-spin`, button disabled
   - Result displayed as an `InferenceCard` rendered inline below the report card (type: `question` if conflict, `insight` if no conflict)
   - If `hasConflict: false`: `InferenceCard` type `insight`, body "No conflicts detected."
   - If `hasConflict: true`: `InferenceCard` type `question`, body contains `conflictDescription` and `resolutionQuestion`

9. **Write E2E integration test:**
   ```python
   # tests/e2e/test_synthesis_flow.py
   async def test_full_synthesis_flow(client, auth_headers):
       """End-to-end: login → create tasks → create report → trigger synthesis → get result → accept task."""
       # 1. Create 3 tasks
       # 2. Create a manual report
       # 3. POST /ai/synthesis (mock OZ)
       # 4. GET /ai/synthesis/latest → assert narrative, theme, score
       # 5. POST /ai/suggest-tasks (mock OZ)
       # 6. POST /ai/accept-tasks with one suggestion
       # 7. GET /tasks/ → assert accepted task appears
       # 8. GET /stats/ghost-list → assert response shape
   ```

## Integration & Edge Cases

- **Sidebar data loading:** Ghost list, synthesis, and AI usage data load independently. If one fails, the other sections still render. Use per-section loading/error states (`animate-pulse bg-slate-700 rounded` skeletons).
- **Co-plan on short reports:** Backend returns `hasConflict: false` for reports < 20 words without calling OZ. Frontend shows `InferenceCard` type `insight` with "Report too short for conflict analysis." — no OZ call means no rate limit slot consumed.
- **429 on co-plan button:** If the user somehow triggers co-plan when at the daily limit (e.g. race condition where `usageData` was stale), the API returns 429. Catch it and show an `InferenceCard` type `warning` with the reset message from the response body (`"Daily co-plan limit reached (3/day). Resets: <date>."`). Do not show a raw HTTP error.
- **AI usage display in sidebar:** The `GET /ai/usage` response (`{ synthesis, suggest, coplan }`) is fetched once on mount and stored in component state. It is not auto-refreshed — a page reload gets fresh data. This is acceptable; the sidebar is informational, not a live billing dashboard.
- **Dismissable cards:** Card dismiss state is per-session (`useState`), not persisted. On page refresh, cards reappear. This is intentional — insights should be re-surfaceable.
- **Bento Grid breakpoint considerations:** The sidebar changes the existing grid breakpoints. Test on common widths: 375px (mobile), 768px (tablet), 1024px (desktop), 1440px (wide).
- **Type sync conflicts:** If `types.gen.ts` has manual edits (it shouldn't), they will be overwritten. Verify the generated types match the backend schemas.

## Acceptance Criteria (required)

1. Tasks page renders a Reasoning Sidebar on desktop viewports (≥768px).
2. Reasoning Sidebar shows Ghost List with task names, days open, and ghost reason.
3. Ghost List empty state shows "No wheel-spinning tasks detected."
4. `InferenceCard` renders correctly for `insight`, `question`, and `warning` types using palette tokens only (no raw hex colors).
5. Re-entry banner appears when the user is returning from leave.
6. Re-entry banner is dismissable and does not reappear until page refresh.
7. "Analyze" button on `ReportCard` triggers `POST /ai/co-plan` and shows result as an inline `InferenceCard`.
8. Co-plan result with conflict shows `conflictDescription` and `resolutionQuestion`.
9. "Analyze" button is `opacity-50 cursor-not-allowed` when `coplan.used >= coplan.limit` (from `GET /ai/usage`).
10. Reasoning Sidebar shows AI usage summary line at the bottom (e.g. "Synthesis: 1/3 this week").
11. Regenerated `types.gen.ts` includes all Phase 4 schema types.
12. `npm run build` exits 0 with no TypeScript errors.
13. E2E test `test_synthesis_flow.py` passes with mocked OZ responses.
14. All existing 100+ backend tests pass with zero regressions.
15. Manual QA smoke test passes (see checklist below).
16. `grep -r "ollama" code/` returns zero results.

## Testing / QA (required)

**New E2E test:** `code/backend/tests/e2e/test_synthesis_flow.py`

Tests:
- `test_full_synthesis_flow` — complete pipeline as described above.
- `test_synthesis_flow_ai_disabled` — `AI_ENABLED=false` → all AI endpoints return 503.
- `test_synthesis_flow_rate_limits` — exhaust synthesis weekly limit (insert 3 `ai_usage_logs`) → assert `POST /ai/synthesis` returns 429 → assert `GET /ai/usage` reflects the exhausted count → assert `POST /ai/suggest-tasks` is unaffected (separate limit bucket).

```bash
cd code/backend && python -m pytest tests/e2e/ -v
```

**Manual QA checklist:**
1. Login → Tasks page → verify Reasoning Sidebar appears on desktop.
2. Resize to mobile → verify sidebar collapses appropriately.
3. Ghost List shows correct tasks (or empty state).
4. Navigate to Reports → click "Analyze" on a report → verify co-plan result displays.
5. Navigate to Synthesis page → trigger synthesis → accept a task → verify it appears in task list.
6. Re-entry test: set SystemState with `requiresRecovery=True`, end date = now → refresh Tasks page → verify Re-entry banner appears.
7. Dismiss the Re-entry banner → verify it's gone. Refresh page → verify it reappears.
8. Run `npm run build` in frontend directory → verify 0 errors.
9. Run full backend test suite → verify ≥100 tests pass.
10. `grep -r "ollama" code/` → verify 0 results.

## Files touched (repeat for reviewers)

- [code/frontend/components/dashboard/ReasoningSidebar.tsx](code/frontend/components/dashboard/ReasoningSidebar.tsx) (new)
- [code/frontend/components/dashboard/InferenceCard.tsx](code/frontend/components/dashboard/InferenceCard.tsx) (new)
- [code/frontend/components/dashboard/GhostListPanel.tsx](code/frontend/components/dashboard/GhostListPanel.tsx) (new)
- [code/frontend/components/dashboard/ReEntryBanner.tsx](code/frontend/components/dashboard/ReEntryBanner.tsx) (new)
- [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx)
- [code/frontend/components/reports/ReportCard.tsx](code/frontend/components/reports/ReportCard.tsx)
- [code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx)
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts)
- [code/frontend/lib/generated/types.gen.ts](code/frontend/lib/generated/types.gen.ts)
- [code/frontend/lib/generated/pulseClient.ts](code/frontend/lib/generated/pulseClient.ts)
- [code/backend/tests/e2e/test_synthesis_flow.py](code/backend/tests/e2e/test_synthesis_flow.py) (new)

## Estimated effort

2–3 dev days

## Concurrency & PR strategy

- **Blocking steps:**
  - `Blocked until: .github/artifacts/phase4/plan/step-4-task-suggester-co-planning.md` (co-plan endpoint)
  - `Blocked until: .github/artifacts/phase4/plan/step-5-ghost-list-analytics.md` (ghost list endpoint)
  - `Blocked until: .github/artifacts/phase4/plan/step-6-synthesis-ui.md` (synthesis UI patterns, API wrappers)
- **Merge Readiness:** false (draft)
- **Branch:** `phase-4/step-7-reasoning-sidebar-type-sync`
- This is the final step. All other steps must merge before this one.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Bento Grid layout changes break existing responsive design | Test all breakpoints before/after. Keep existing Zone A and B unchanged; Zone C is additive. |
| Type sync regeneration breaks existing API calls | Run `npm run build` after regeneration. Existing types should be backward-compatible (new types added, none removed). |
| Ghost list + co-plan + synthesis overload the sidebar | Progressive disclosure: show top 3 ghost tasks with "Show all" link. Inference cards are dismissable. |
| E2E test flakiness with mocked OZ | Use deterministic mock responses. Avoid timing-dependent assertions. |

## References

- [product.md](../../product.md) — Zone C (Reasoning Sidebar), state-aware styling, Bento Grid layout
- [PDD.md](../../PDD.md) — §5 UI/UX Strategy, §4.2 Ambiguity Guard, Ghost List
- [step-4-task-suggester-co-planning.md](./step-4-task-suggester-co-planning.md) — Co-plan endpoint
- [step-5-ghost-list-analytics.md](./step-5-ghost-list-analytics.md) — Ghost list endpoint
- [step-6-synthesis-ui.md](./step-6-synthesis-ui.md) — Synthesis page patterns and API wrappers
- [architecture.md](../../architecture.md) — Type Sync workflow with `@hey-api/openapi-ts`

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
