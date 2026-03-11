# Step 4 — Reports Page Frontend (Full Implementation)

## Purpose

Replace the reports page shell with the full "Strategic Reports" dashboard matching the visual specification in [screen2.png](../../screen2.png), implementing report listing with expanded/collapsed card variants, LATEST/ARCHIVED badges, a tags box, report creation/editing via modal form with multi-select task linking, pagination via "Load Historical Reports", and proper auth + pulse state wiring.

## Deliverables

- Rewritten `code/frontend/app/reports/page.tsx` — full reports dashboard page
- New `code/frontend/components/reports/ReportCard.tsx` — expanded (latest) and collapsed (historical) variants
- New `code/frontend/components/reports/ReportForm.tsx` — create/edit modal with title, body textarea, multi-select task linking dropdown, tag input
- New `code/frontend/components/reports/ReportList.tsx` — paginated report list with "Load Historical Reports" footer
- Updated `code/frontend/components/nav/AppNavBar.tsx` — "+ Create New Report" button wired to open creation form
- `npm run build` passes with zero TypeScript errors

## Primary files to change (required)

- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx) *(rewrite)*
- [code/frontend/components/reports/ReportCard.tsx](../../../../code/frontend/components/reports/ReportCard.tsx) *(new)*
- [code/frontend/components/reports/ReportForm.tsx](../../../../code/frontend/components/reports/ReportForm.tsx) *(new)*
- [code/frontend/components/reports/ReportList.tsx](../../../../code/frontend/components/reports/ReportList.tsx) *(new)*
- [code/frontend/components/nav/AppNavBar.tsx](../../../../code/frontend/components/nav/AppNavBar.tsx) *(modify)*

## UI Reference

**The target UI is defined by [.github/artifacts/screen2.png](../../screen2.png).** All layout, component structure, typography, spacing, and visual styling decisions in this step must match that screenshot. Key elements from the screenshot:

- **Page header:** "Strategic Reports" (large white text), subtitle "Temporal history and narrative synthesis of your progress." (slate-400), right-aligned "Last updated X ago" with calendar icon
- **Latest report card (expanded):** Left cyan/blue border accent, title + date/time, "LATEST" badge (cyan pill), "Edit Report" button (slate-700 bg, white text), "STRATEGIC NARRATIVE" section header (cyan text), body text (slate-300), TAGS box (right side, dark bg, pill badges for each tag like "Engineering", "Strategy", "Infrastructure", "UI/UX", "Refinement")
- **Historical report cards (collapsed):** Title + date on left, 1-line description/preview, author avatar circles on right, chevron indicator, optional "ARCHIVED" badge (red/rose outline pill)
- **"Load Historical Reports" footer:** Centered, with chevron-down icon, clickable to load more
- **NavBar:** "Reports" tab highlighted, "+ Create New Report" button prominent (blue-600)

## Detailed implementation steps

1. **Create `ReportCard.tsx`** in `code/frontend/components/reports/`:
   - Two variants controlled by an `expanded` prop:
     - **Expanded (latest):** Full card with left border accent (`border-l-4 border-cyan-500`), title (`text-xl font-semibold text-white`), date + time below title (`text-sm text-slate-400`), "LATEST" badge (`bg-cyan-500/20 text-cyan-400 text-xs px-2 py-0.5 rounded`), "Edit Report" button (top right), "STRATEGIC NARRATIVE" section header (`text-cyan-400 text-xs font-bold tracking-widest`), body text (`text-slate-300 text-sm leading-relaxed`), and TAGS box (right column — dark bg card with pill badges).
     - **Collapsed (historical):** Single row — title + date left, description snippet center, right side shows optional avatar circles and chevron. If `status === "archived"`, show "ARCHIVED" badge (`border border-rose-500 text-rose-400 text-xs px-2 py-0.5 rounded`).
   - Props: `report: ManualReportSchema`, `expanded?: boolean`, `onEdit?: (id: string) => void`, `onClick?: (id: string) => void`
   - Responsive: stacks on mobile.

2. **Create `ReportForm.tsx`** in `code/frontend/components/reports/`:
   - Modal overlay with dark backdrop
   - Form fields:
     - Title: text input (max 256 chars)
     - Body: multiline textarea (large, min 6 rows)
     - Task linking: multi-select searchable dropdown populated from `listTasks(token)`. Display task names; store task IDs in `associatedTaskIds`. Use a simple custom dropdown with checkboxes — no external drag-and-drop library needed.
     - Tags: tag input field — type and press Enter/comma to add tags as pills; click X to remove
     - Status: toggle between "Draft" and "Published" (default Published)
   - Two modes: "Create" (empty form, calls `createReport`) and "Edit" (pre-populated, calls `updateReport`)
   - Props: `mode: "create" | "edit"`, `report?: ManualReportSchema` (for edit), `token: string`, `tasks: Task[]`, `onClose: () => void`, `onSave: () => void`
   - Styling: dark theme matching the page (`bg-slate-800 border border-slate-700 rounded-lg`)

3. **Create `ReportList.tsx`** in `code/frontend/components/reports/`:
   - Renders a list of `ReportCard` components
   - First card is `expanded={true}` with "LATEST" badge; subsequent cards are collapsed
   - "Load Historical Reports" footer button: calls `listReports(token, offset + limit)` and appends results
   - Tracks `offset`, `limit`, `total` from `PaginatedReportsResponse`
   - Shows "No reports yet. Create your first report to get started." when empty
   - Props: `token: string`, `onEdit: (id: string) => void`
   - Internal state: `reports`, `total`, `offset`, `loading`

4. **Rewrite `reports/page.tsx`**:
   - Use `useAuth()` hook for token (redirect to `/login` if missing)
   - Fetch pulse stats on mount for navbar `silenceState` (replaces hardcoded `"engaged"`)
   - Page structure:
     ```
     <AppNavBar silenceState={pulse?.silenceState} gapMinutes={pulse?.gapMinutes} onCreateReport={openForm} />
     <main className="max-w-4xl mx-auto px-6 py-8">
       <header> "Strategic Reports" + subtitle + "Last updated" </header>
       <ReportList token={token} onEdit={handleEdit} />
     </main>
     <ReportForm ... />  {/* modal, conditionally rendered */}
     ```
   - State: `showForm: boolean`, `editingReport: ManualReportSchema | null`, `pulse: PulseStats | null`
   - Polling: pulse every 30s (same pattern as tasks page)

5. **Update `AppNavBar.tsx`**:
   - Add `onCreateReport?: () => void` prop
   - Wire the existing "+ Create Report" button's `onClick` to call `onCreateReport` when provided:
     ```tsx
     <button onClick={onCreateReport} className="...">
       + Create New Report
     </button>
     ```
   - Update the button text from "Create Report" to "+ Create New Report" to match [screen2.png](../../screen2.png)

6. **"Last updated" timestamp**:
   - Compute from the `createdAt` of the most recent report, displayed as relative time ("2 hours ago", "3 days ago")
   - Use a simple relative time formatter (no external library; a small utility function)

7. **Verify build**:
   ```bash
   cd code/frontend
   npm run build
   ```
   Must exit 0.

## Integration & Edge Cases

- **Empty state:** When no reports exist, show centered placeholder text.
- **Large body text:** Expanded card truncates body after ~3 paragraphs with a "Read more" link or expands inline.
- **Task linking data flow:** `ReportForm` fetches `listTasks(token)` on mount to populate the dropdown. Task names displayed; IDs stored.
- **Optimistic updates:** After creating/editing/archiving a report, refresh the list (simple refetch, not optimistic).
- **Form validation:** Title required, body required. Show inline error messages.
- **Mobile layout:** Cards stack full-width. Tags box moves below body on narrow screens. Form modal fills screen on mobile.
- **Nav consistency:** The Tasks page also uses `AppNavBar`. Adding the `onCreateReport` prop is optional — when not provided (Tasks page), the button remains inert or navigates to `/reports` with create intent.

## Acceptance Criteria

1. Opening `/reports` renders the Strategic Reports page with header "Strategic Reports", subtitle, and "Last updated" timestamp.
2. The `AppNavBar` shows the correct `silenceState` badge (not hardcoded).
3. The latest report displays in expanded format with left cyan border, title, date, LATEST badge, STRATEGIC NARRATIVE header, body text, and tags box.
4. Historical reports display as collapsed cards with title, date, description preview, and optional ARCHIVED badge.
5. Clicking "+ Create New Report" opens a modal form with title, body, task linking dropdown, and tag input.
6. Submitting the form creates a report (visible in list after close) with auto-computed word count.
7. Clicking "Edit Report" on the latest card opens the form pre-populated for editing.
8. "Load Historical Reports" loads additional reports (pagination).
9. Tags appear as pill badges in the report card, matching the screenshot layout.
10. Mobile breakpoint: cards and form are responsive (full-width stack on narrow screens).
11. `npm run build` exits 0 with zero TypeScript errors.

## Testing / QA

### Automated checks

```bash
cd code/frontend
npm run build   # zero errors
```

**Note:** Frontend unit/integration tests are not in scope for Phase 3 (deferred tech debt). Acceptance is via manual QA and build gate.

### Manual QA checklist

1. Start backend + frontend servers
2. Login → navigate to `/reports`
3. Verify page header matches [screen2.png](../../screen2.png): "Strategic Reports", subtitle, "Last updated"
4. Verify navbar badge reflects actual pulse state (not hardcoded)
5. Click "+ Create New Report" → form modal appears
6. Fill title + body + link 2 tasks + add 3 tags → submit → verify card appears in list
7. Verify the new report shows as expanded (latest) with LATEST badge, body, tags
8. Click "Edit Report" → verify form pre-populates → change title → save → verify update
9. Create 3+ reports → verify first is expanded, rest are collapsed
10. Archive a report via backend (`PATCH /reports/{id}/archive`) → refresh → verify ARCHIVED badge on collapsed card
11. Click "Load Historical Reports" → verify more reports load
12. Resize browser to mobile width → verify responsive layout
13. Verify no console errors in browser dev tools

## Files touched (repeat for reviewers)

- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx)
- [code/frontend/components/reports/ReportCard.tsx](../../../../code/frontend/components/reports/ReportCard.tsx)
- [code/frontend/components/reports/ReportForm.tsx](../../../../code/frontend/components/reports/ReportForm.tsx)
- [code/frontend/components/reports/ReportList.tsx](../../../../code/frontend/components/reports/ReportList.tsx)
- [code/frontend/components/nav/AppNavBar.tsx](../../../../code/frontend/components/nav/AppNavBar.tsx)

## Estimated effort

2–3 dev days

## Concurrency & PR strategy

- **Suggested branch:** `phase-3/step-4-reports-page`
- **Blocking steps:** `phase-3/step-3-type-sync` must be merged first (type-safe API wrapper functions required).
- **Merge Readiness:** false
- Can be developed in parallel with Step 5 (SystemState UI) after Step 3 merges.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Multi-select task dropdown UX is complex without a library | Build a minimal custom component; avoid external deps for now |
| Report body rendering may need markdown support | For Phase 3 MVP, render as plain text with whitespace preserved. Markdown rendering can be added later. |
| Screenshot pixel-perfect matching is subjective | Match structural layout, spacing proportions, and color palette; exact pixel dimensions are secondary |
| `AppNavBar` `onCreateReport` prop breaks Tasks page | Prop is optional (`?:`) — Tasks page doesn't pass it; button remains inert there (can navigate to `/reports?create=true` as fallback) |

## References

- [screen2.png — Reports UI visual spec](../../screen2.png)
- [PDD.md — §5 UI/UX Strategy, §3.2 Manual Reporting](../../PDD.md)
- [product.md — §4 UI/UX Specification](../../product.md)
- [Phase 3 Master](./master.md)
- [Step 3 — Type Sync](./step-3-type-sync.md)

## Appendix: Screenshot breakdown

Key visual elements from [screen2.png](../../screen2.png) for implementer reference:

| Element | Location | Styling |
|---|---|---|
| "Strategic Reports" | Top left, below nav | `text-3xl font-bold text-white` |
| Subtitle | Below title | `text-slate-400 text-sm` |
| "Last updated 2 hours ago" | Top right, with calendar icon | `text-slate-400 text-sm` |
| Latest report card | Full width, below header | `bg-slate-800/50 border border-slate-700 rounded-xl p-6`, left `border-l-4 border-cyan-500` |
| "LATEST" badge | Next to title | `bg-cyan-500/20 text-cyan-400 text-xs font-medium px-2 py-0.5 rounded` |
| "Edit Report" button | Top right of card | `bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-1.5 rounded-md`, pencil icon |
| "STRATEGIC NARRATIVE" label | Above body text | `text-cyan-400 text-xs font-bold tracking-widest` |
| TAGS box | Right column of expanded card | `bg-slate-800 border border-slate-700 rounded-lg p-4`, tag pills `bg-slate-700 text-slate-300 text-xs px-2.5 py-1 rounded` |
| Collapsed card | Below latest | `bg-slate-800/50 border border-slate-700 rounded-xl px-6 py-4`, single row |
| "ARCHIVED" badge | Right side of collapsed card | `border border-rose-500 text-rose-400 text-xs px-2 py-0.5 rounded` |
| "Load Historical Reports" | Bottom center | `text-slate-400 text-sm`, chevron-down icon |

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added (build gate)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
- [ ] Author signoff
