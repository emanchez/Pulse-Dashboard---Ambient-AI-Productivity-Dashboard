# Step 7 — Reports UX Enhancements

## Purpose

Improve the reports page UX by adding delete/archive actions to report cards, making collapsed cards expandable, and managing expanded state properly.

## Deliverables

- Delete and archive action buttons on each `ReportCard` with confirmation dialogs.
- Click-to-expand toggle on collapsed report cards.
- Expanded state managed as a set of IDs (multiple cards can be expanded simultaneously).

## Primary files to change (required)

- [code/frontend/components/reports/ReportCard.tsx](code/frontend/components/reports/ReportCard.tsx)
- [code/frontend/components/reports/ReportList.tsx](code/frontend/components/reports/ReportList.tsx)
- [code/frontend/app/reports/page.tsx](code/frontend/app/reports/page.tsx)

## Detailed implementation steps

### 7.1 — Expandable report cards

1. In [code/frontend/components/reports/ReportList.tsx](code/frontend/components/reports/ReportList.tsx):
   - Replace the current `expanded={index === 0}` single-card logic with a `Set<string>` state:
     ```typescript
     const [expandedIds, setExpandedIds] = useState<Set<string>>(
       new Set(reports.length > 0 ? [reports[0].id] : [])
     )
     ```
   - Pass `expanded={expandedIds.has(report.id)}` and `onToggle={() => toggleExpanded(report.id)}` to each `ReportCard`.
   - Implement `toggleExpanded`:
     ```typescript
     const toggleExpanded = (id: string) => {
       setExpandedIds((prev) => {
         const next = new Set(prev)
         if (next.has(id)) next.delete(id)
         else next.add(id)
         return next
       })
     }
     ```

2. In [code/frontend/components/reports/ReportCard.tsx](code/frontend/components/reports/ReportCard.tsx):
   - Add an `onToggle` prop: `onToggle?: () => void`.
   - On the collapsed card container, add `onClick={onToggle}` and `cursor-pointer` class.
   - The `ChevronRight` icon already suggests clickability — now it will actually work.
   - Optionally rotate the chevron when expanded: `className={expanded ? "rotate-90 transition-transform" : "transition-transform"}`.

### 7.2 — Delete and archive actions

1. In [code/frontend/components/reports/ReportCard.tsx](code/frontend/components/reports/ReportCard.tsx):
   - Add props: `onDelete?: (id: string) => void` and `onArchive?: (id: string) => void`.
   - In the expanded card view, alongside the existing "Edit Report" button, add:
     - An "Archive" button (amber/orange styling): calls `onArchive?.(report.id)`.
     - A "Delete" button (red styling): calls `onDelete?.(report.id)`.
   - Add a confirmation step for delete: use a simple `window.confirm("Delete this report? This cannot be undone.")` or a local `confirmDelete` state that shows inline confirm/cancel buttons.

2. In [code/frontend/components/reports/ReportList.tsx](code/frontend/components/reports/ReportList.tsx):
   - Accept `onDelete` and `onArchive` props and pass them through to each `ReportCard`.

3. In [code/frontend/app/reports/page.tsx](code/frontend/app/reports/page.tsx):
   - Import `deleteReport` and `archiveReport` from [code/frontend/lib/api.ts](code/frontend/lib/api.ts).
   - Create handler functions:
     ```typescript
     const handleDeleteReport = async (id: string) => {
       if (!token) return
       try {
         await deleteReport(token, id)
         await refreshReports()
       } catch (err) {
         console.error("Failed to delete report:", err)
         // Optionally show error
       }
     }

     const handleArchiveReport = async (id: string) => {
       if (!token) return
       try {
         await archiveReport(token, id)
         await refreshReports()
       } catch (err) {
         console.error("Failed to archive report:", err)
       }
     }
     ```
   - Pass `onDelete={handleDeleteReport}` and `onArchive={handleArchiveReport}` to `ReportList`.

## Integration & Edge Cases

- No persistence changes (backend already supports delete and archive).
- After deleting a report that was expanded, remove its ID from `expandedIds`.
- Archiving changes the report's status to "archived" — if the list is filtered by status, the archived report should disappear from the active list.
- If `deleteReport` or `archiveReport` fails, the report remains in the list (no optimistic deletion).

## Acceptance Criteria (required)

1. Clicking a collapsed report card expands it (shows full body, tags, actions).
2. Clicking an expanded report card collapses it.
3. Multiple cards can be expanded simultaneously.
4. Each expanded report card has a "Delete" action button.
5. Clicking "Delete" shows a confirmation step; confirming calls `DELETE /reports/{id}` and removes the card.
6. Each expanded report card has an "Archive" action button.
7. Clicking "Archive" calls `PATCH /reports/{id}/archive` and the report updates in the list.
8. `npm run build` passes with zero errors.

## Testing / QA (required)

**Automated:**
```bash
cd code/frontend && npm run build
```

**Manual QA checklist:**
1. Navigate to `/reports` with 3+ reports — confirm the first is expanded, others are collapsed.
2. Click a collapsed card — confirm it expands.
3. Click an expanded card — confirm it collapses.
4. Expand two cards simultaneously — confirm both show their content.
5. On an expanded card, click "Delete" — confirm a confirmation prompt appears.
6. Confirm deletion — confirm the card disappears and the report count decreases.
7. On an expanded card, click "Archive" — confirm the card updates (status changes or card moves/disappears based on filter).
8. Edit and save a report — confirm it still works alongside new actions.

## Files touched (repeat for reviewers)

- [code/frontend/components/reports/ReportCard.tsx](code/frontend/components/reports/ReportCard.tsx)
- [code/frontend/components/reports/ReportList.tsx](code/frontend/components/reports/ReportList.tsx)
- [code/frontend/app/reports/page.tsx](code/frontend/app/reports/page.tsx)

## Estimated effort

0.5–1 dev day

## Concurrency & PR strategy

- Suggested branch: `phase-3/step-7-reports-ux`
- Blocking steps: None
- Merge Readiness: false
- This step is in Concurrency Group A and can be worked/merged independently.

## Risks & Mitigations

- **Risk:** Expanding all cards makes the page long/slow with many reports. **Mitigation:** The list is already paginated (default 20); acceptable for MVP.

## References

- [code/frontend/lib/api.ts](code/frontend/lib/api.ts) — `deleteReport()`, `archiveReport()` wrappers
- [code/backend/app/api/reports.py](code/backend/app/api/reports.py) — backend delete/archive endpoints

## Author Checklist (must complete before PR)

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation) — N/A (frontend UI)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected — N/A
