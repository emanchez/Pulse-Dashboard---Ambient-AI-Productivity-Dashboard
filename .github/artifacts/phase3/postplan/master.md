# Phase 3 Postplan — Production Readiness Fixes

## Scope

Address 17 confirmed issues (critical through medium severity) surfaced by manual testing and a comprehensive code audit of the Phase 3 deliverables. The three user-reported observations — white-on-white login inputs, silent report save failures, and missing task CRUD — are the anchoring priorities. The audit additionally uncovered missing session management controls, absent logout functionality, task model missing `user_id` scoping, dead code, navbar inconsistencies, and silent error swallowing across multiple components.

**Out of scope:** Low-severity items (redundant `PulseStatsSchema` alias declarations, naive datetime in JWT `exp`, inconsistent `TaskSchema` import paths, hardcoded avatar letter, non-functional bell icon) are deferred to a future phase.

## Phase-level Deliverables

- Login page fully restyled to dark theme with readable form inputs.
- Visible error feedback on all frontend forms (ReportForm, SystemStateManager).
- `Task` model extended with `user_id` column, migration script, scoped queries, `TaskCreate` schema, and field validation.
- Regenerated TypeScript client reflecting backend schema changes.
- Full task CRUD UI (create, edit, delete) on the tasks page.
- Session start/stop controls in the CurrentSessionCard.
- Reports UX improvements: delete/archive actions, expandable cards.
- Navigation polish: logout button, conditional "Create Report" rendering, dead code removal, placeholder cleanup.

## Steps (ordered)

1. Step 1 — [step-1-login-dark-theme.md](./step-1-login-dark-theme.md)
2. Step 2 — [step-2-error-handling.md](./step-2-error-handling.md)
3. Step 3 — [step-3-backend-task-hardening.md](./step-3-backend-task-hardening.md)
4. Step 4 — [step-4-type-sync-regen.md](./step-4-type-sync-regen.md)
5. Step 5 — [step-5-task-crud-ui.md](./step-5-task-crud-ui.md)
6. Step 6 — [step-6-session-mgmt-ui.md](./step-6-session-mgmt-ui.md)
7. Step 7 — [step-7-reports-ux.md](./step-7-reports-ux.md)
8. Step 8 — [step-8-nav-polish-cleanup.md](./step-8-nav-polish-cleanup.md)

## Merge Order

Steps 1, 2, 6, 7, 8 have no cross-dependencies and may merge in any order. Steps 3 → 4 → 5 form a serial chain.

Exact merge sequence for the serial chain:

1. `.github/artifacts/phase3/postplan/step-3-backend-task-hardening.md` — branch: `phase-3/step-3-backend-task-hardening`
2. `.github/artifacts/phase3/postplan/step-4-type-sync-regen.md` — branch: `phase-3/step-4-type-sync-regen`
3. `.github/artifacts/phase3/postplan/step-5-task-crud-ui.md` — branch: `phase-3/step-5-task-crud-ui`

## Phase Acceptance Criteria

1. Login page inputs have visible text on dark background; the entire login form uses the app's dark palette.
2. ReportForm and SystemStateManager display user-visible error messages when API calls fail.
3. `Task` model includes a `user_id` column; all task queries are user-scoped; `TaskCreate` schema rejects empty names and invalid priorities.
4. Generated TypeScript client includes `TaskCreate` type and updated `TaskUpdate` usage.
5. Users can create, edit, and delete tasks from the tasks page UI.
6. Users can start and stop focus sessions from the CurrentSessionCard.
7. Report cards are expandable/collapsible; delete and archive actions are available per report.
8. A logout option is accessible from the navbar; "Create New Report" button only renders when a handler is provided.
9. Dead code (`PulseCard.tsx`) is removed; hardcoded QuickAccess placeholders are addressed.
10. `npm run build` produces zero TypeScript errors.
11. `pytest -q` passes all tests (existing 90 + new task-scoping/validation tests).

## Concurrency groups & PR strategy

| Group | Steps | Notes |
|-------|-------|-------|
| A (parallel) | 1, 2, 6, 7, 8 | No cross-dependencies; may be worked and merged in any order |
| B (serial) | 3 → 4 → 5 | Type sync (4) depends on backend changes (3); Task UI (5) depends on both |

Branch naming: `phase-3/step-<n>-<short-desc>`

PRs in Group A can merge independently. Within Group B, each PR must wait for its predecessor to merge.

## Verification Plan

### Automated

```bash
# Backend
cd code/backend && pytest -q

# Frontend build
cd code/frontend && npm run build
```

### Manual smoke tests

1. Navigate to `/login` — confirm inputs show text on dark background.
2. Create a report with an empty title — confirm a visible validation error appears in the form.
3. Create, edit (name + priority), and delete a task from `/tasks`.
4. Start a focus session from the tasks page, confirm the active session card updates, then stop it.
5. Expand and collapse report cards on `/reports`. Delete a report and confirm it disappears.
6. Click the user avatar in the navbar — confirm logout redirects to `/login`.
7. Visit `/tasks` — confirm there is no orphaned "Create New Report" button (or it navigates to `/reports`).

## Risks, Rollbacks & Migration Notes

| Risk | Severity | Mitigation |
|------|----------|------------|
| `user_id` column addition requires data migration | Medium | Step 3 includes a backfill script (`scripts/migrate_task_user_id.py`). Pre-merge: backup `data/dev.db`. Rollback: restore backup. |
| TypeScript client regen may break compilation | Medium | Step 4 runs `npm run build` as acceptance gate; revert regen if build fails. |
| Task CRUD UI changes touch shared components | Low | Step 5 scoped to tasks page + TaskQueueTable; no shared component modifications. |
| Removing `PulseCard.tsx` | Low | Component is confirmed unused — grep for imports before deletion. |

**Backup requirement (Step 3):** Before merging the `user_id` migration, run:
```bash
cp code/backend/data/dev.db code/backend/data/dev.db.bak
```

## References

- [Phase 3 Final Report](../summary/final-report.md)
- [User Observations](./observations.txt)
- [PDD](../../PDD.md)
- [Architecture](../../architecture.md)
- [PLANNING.md](../../PLANNING.md)
- [Master Template](../../master-template.md)
- [Step Template](../../step-template.md)

## Author Checklist (master)

- [x] All step files created and linked
- [x] Phase-level acceptance criteria are measurable
- [x] PR/merge order documented
- [x] Concurrency groups defined
- [x] Verification plan includes automated + manual checks
- [x] Risks and rollback procedures documented
- [x] Backup requirement for persistence changes noted
