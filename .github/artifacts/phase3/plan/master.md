# Phase 3 — Qualitative Inputs & System Pauses: Master Plan

## Scope

Deliver the Manual Report and System State (Vacation/Leave) subsystems end-to-end: backend CRUD APIs with event-sourced action logging, regenerated TypeScript client types, a fully-built Reports page matching the dark bento-style design in [screen2.png](../../screen2.png), a System State management UI, and subtle state-aware palette shifting across all pages. A dedicated tech-debt cleanup step precedes all feature work to resolve correctness and quality issues surfaced in the Phase 2.2 final audit. No Ollama/AI inference is required — that is Phase 4 scope.

**Key decisions:**
- Task linking on reports uses a multi-select searchable dropdown (no drag-and-drop dependency; mobile-first).
- Report CRUD is full lifecycle: create, read, update, delete, archive, with offset pagination.
- Palette shifting is subtle — accent borders/highlights tint per silence state; base dark theme unchanged.
- Tech debt resolved in a dedicated Step 0 before new feature code.

## Phase-level Deliverables

- **Tech debt resolution:** consolidated auth helper, null-safe `get_current_user`, modern `datetime.now(UTC)`, deduplicated `_to_camel`, `.is_(None)` SQLAlchemy hygiene, hardened `ActionLogMiddleware`
- **ManualReport CRUD API:** `POST /reports`, `GET /reports` (paginated), `GET /reports/{id}`, `PUT /reports/{id}`, `DELETE /reports/{id}`, `PATCH /reports/{id}/archive` — all JWT-guarded, user-scoped, action-logged
- **SystemState CRUD API:** `POST /system-states`, `GET /system-states`, `GET /system-states/active`, `PUT /system-states/{id}`, `DELETE /system-states/{id}` — all JWT-guarded, user-scoped, action-logged
- **ManualReport model enhancement:** `user_id` column, `status` column (draft/published/archived), `tags` column (JSON)
- **Regenerated TypeScript client** with new `ManualReportSchema`, `SystemStateSchema`, and related DTOs
- **Typed API wrapper functions** in `lib/api.ts` for all new endpoints
- **Reports page** (replaces shell) — full dark bento-style page per [screen2.png](../../screen2.png): expanded latest report card, collapsed historical report cards, LATEST/ARCHIVED badges, tags box, "Edit Report" button, "Load Historical Reports" pagination, "Strategic Reports" header, creation/edit form with multi-select task linking
- **"+ Create New Report" button** in `AppNavBar` wired to report creation flow
- **SystemState management UI** — create/edit vacation/leave schedules, view active/upcoming/past states
- **State-aware palette shifting** — CSS custom property / `data-state` attribute strategy propagating `silenceState` to accent colours across all pages
- `recharts` preserved; no new charting dependencies

## Steps (ordered)

0. Step 0 — [step-0-tech-debt-cleanup.md](./step-0-tech-debt-cleanup.md) — Backend tech debt resolution
1. Step 1 — [step-1-manual-report-backend.md](./step-1-manual-report-backend.md) — ManualReport model enhancement + CRUD API
2. Step 2 — [step-2-system-state-backend.md](./step-2-system-state-backend.md) — SystemState CRUD API
3. Step 3 — [step-3-type-sync.md](./step-3-type-sync.md) — Regenerate TypeScript client + typed wrappers
4. Step 4 — [step-4-reports-page.md](./step-4-reports-page.md) — Reports page frontend (full implementation)
5. Step 5 — [step-5-system-state-ui.md](./step-5-system-state-ui.md) — SystemState management UI
6. Step 6 — [step-6-palette-shifting.md](./step-6-palette-shifting.md) — State-aware accent palette shifting

## Merge Order

Steps 1 and 2 are independent of each other but both depend on Step 0. Step 3 depends on Steps 1 + 2. Steps 4 and 5 are independent but both depend on Step 3. Step 6 depends on Steps 4 + 5.

1. `.github/artifacts/phase3/plan/step-0-tech-debt-cleanup.md` — branch: `phase-3/step-0-tech-debt-cleanup`
2. `.github/artifacts/phase3/plan/step-1-manual-report-backend.md` — branch: `phase-3/step-1-manual-report-backend` *(after Step 0)*
3. `.github/artifacts/phase3/plan/step-2-system-state-backend.md` — branch: `phase-3/step-2-system-state-backend` *(after Step 0, parallel with Step 1)*
4. `.github/artifacts/phase3/plan/step-3-type-sync.md` — branch: `phase-3/step-3-type-sync` *(after Steps 1 + 2)*
5. `.github/artifacts/phase3/plan/step-4-reports-page.md` — branch: `phase-3/step-4-reports-page` *(after Step 3)*
6. `.github/artifacts/phase3/plan/step-5-system-state-ui.md` — branch: `phase-3/step-5-system-state-ui` *(after Step 3, parallel with Step 4)*
7. `.github/artifacts/phase3/plan/step-6-palette-shifting.md` — branch: `phase-3/step-6-palette-shifting` *(after Steps 4 + 5)*

## Phase Acceptance Criteria

1. `POST /reports` with `{ "title": "Weekly Update", "body": "Progress on..." }` returns `201` with a JSON body containing `id`, `title`, `body`, `wordCount` (auto-computed), `status: "published"`, `userId`, `createdAt`.
2. `GET /reports` returns `200` with `{ "items": [...], "total": <int>, "offset": <int>, "limit": <int> }`.
3. `GET /reports/{id}` returns `200` with full report including `associatedTaskIds` and `tags`.
4. `PUT /reports/{id}` returns `200` with updated fields.
5. `PATCH /reports/{id}/archive` sets `status` to `"archived"` and returns `200`.
6. `DELETE /reports/{id}` returns `204`.
7. `POST /system-states` with `{ "modeType": "vacation", "startDate": "...", "endDate": "..." }` returns `201`.
8. `GET /system-states/active` returns `200` with the currently active state or `null`.
9. `GET /system-states` returns `200` with a list of all system states for the user.
10. `PUT /system-states/{id}` returns `200` with updated fields. `DELETE /system-states/{id}` returns `204`.
11. All existing endpoints (`/tasks`, `/sessions`, `/stats`) continue to pass their test suites with no regressions.
12. `npm run generate:api` exits 0 and `lib/generated/types.gen.ts` contains `ManualReportSchema`, `ManualReportCreate`, `SystemStateSchema`, `SystemStateCreate` types.
13. `npm run build` exits 0 with zero TypeScript errors.
14. Opening `/reports` renders the full Strategic Reports page matching [screen2.png](../../screen2.png): header, latest report card (expanded), historical cards (collapsed), LATEST/ARCHIVED badges, tags, pagination.
15. The "+ Create New Report" button triggers a creation form with title, body, multi-select task linking, and tag input.
16. A vacation/leave schedule can be created from the UI and the `AppNavBar` badge dynamically reflects "SYSTEM PAUSED" status via the pulse endpoint.
17. Accent colours (borders, highlights) shift based on `silenceState`: emerald for engaged, amber for stagnant, sky for paused — visible across both Tasks and Reports pages.
18. All `datetime.utcnow()` calls are replaced with `datetime.now(datetime.UTC)` across the backend.
19. A single `get_current_user` dependency exists in `code/backend/app/api/auth.py`; no other files define their own.

## Concurrency groups & PR strategy

**Group A (no blockers):**
- `phase-3/step-0-tech-debt-cleanup`

**Group B (blocked on Group A):**
- `phase-3/step-1-manual-report-backend`
- `phase-3/step-2-system-state-backend`

**Group C (blocked on all of Group B):**
- `phase-3/step-3-type-sync`

**Group D (blocked on Group C):**
- `phase-3/step-4-reports-page`
- `phase-3/step-5-system-state-ui`

**Group E (blocked on all of Group D):**
- `phase-3/step-6-palette-shifting`

All PRs must include `Depends-On: <branch>` in the PR description when a blocker is unmerged, and carry a `depends` label until resolved.

## Verification Plan

```bash
# 1. Backend unit + integration tests (all steps)
cd code/backend
source ../../.venv/bin/activate
pytest tests/ -v --tb=short

# 2. Smoke-test report endpoints
export TOKEN=$(curl -s -X POST localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"dev","password":"dev"}' | jq -r .access_token)

curl -s -X POST localhost:8000/reports \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Report","body":"Some content here for testing."}' | jq .

curl -s localhost:8000/reports -H "Authorization: Bearer $TOKEN" | jq .
curl -s localhost:8000/reports -H "Authorization: Bearer $TOKEN" | jq '.items | length'

# 3. Smoke-test system-state endpoints
curl -s -X POST localhost:8000/system-states \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"modeType":"vacation","startDate":"2026-03-01T00:00:00","endDate":"2026-03-07T00:00:00","description":"Spring break"}' | jq .

curl -s localhost:8000/system-states/active -H "Authorization: Bearer $TOKEN" | jq .

# 4. Verify pulse picks up new system state
curl -s localhost:8000/stats/pulse -H "Authorization: Bearer $TOKEN" | jq .silenceState

# 5. Verify existing endpoints still work
curl -s localhost:8000/tasks/ -H "Authorization: Bearer $TOKEN" | jq 'length'
curl -s localhost:8000/sessions/active -H "Authorization: Bearer $TOKEN" | jq .
curl -s localhost:8000/stats/flow-state -H "Authorization: Bearer $TOKEN" | jq .flowPercent

# 6. Type sync
cd ../frontend
npm run generate:api   # must exit 0

# 7. Frontend build gate
npm run build          # zero TS errors

# 8. Manual E2E checklist
# a. Open http://localhost:3000/reports → verify Strategic Reports page renders
# b. Click "+ Create New Report" → verify creation form appears
# c. Create a report with title, body, linked tasks, and tags → verify card appears in list
# d. Click "Edit Report" on latest → verify edit form populates → save → verify update
# e. Archive a report → verify ARCHIVED badge appears
# f. Click "Load Historical Reports" → verify pagination loads more
# g. Create a vacation state → verify AppNavBar shows "SYSTEM PAUSED"
# h. Delete the vacation → verify AppNavBar reverts to ENGAGED/STAGNANT
# i. Verify accent colour tints shift on both /tasks and /reports pages per silenceState
```

Coverage expectation: all new endpoint happy-paths, at least one validation/auth failure path per endpoint, and at least one pagination boundary test.

## Risks, Rollbacks & Migration Notes

| Risk | Mitigation |
|---|---|
| `manual_reports` table needs new columns (`user_id`, `status`, `tags`) | Additive migration via `create_all`; no existing data in table. Snapshot `data/dev.db` to `data/dev.db.bak` before merge |
| `datetime.utcnow()` migration may break timestamp consistency | Step 0 converts all at once; tests validate timestamps are still correct |
| Consolidating `get_current_user` may break imports in `tasks.py` and `sessions.py` | Step 0 updates all import sites; tests catch any missed references |
| `ActionLogMiddleware` path expansion may over-log | Only add `/reports` and `/system-states` paths to the match list; test that unrelated paths are not logged |
| Type sync may overwrite hand-written `pulseClient.ts` | Verify `pulseClient.ts` is preserved post-generation; document in Step 3 |
| Large report body size | Add backend validation: max body length (e.g., 50,000 chars) |
| Overlapping system states | Validate in service layer: reject create/update if date range overlaps an existing active state for the user |

**Rollback:** Restore `data/dev.db.bak` and revert the merge commit. All changes are additive (new tables/columns, new routes) so revert is safe.

## References

- [PDD.md — §3.3 ManualReport, §3.4 SystemState, §5 MVP Phase 3](../../PDD.md)
- [architecture.md — §2 API Design](../../architecture.md)
- [agents.md — §2 Inference Engine](../../agents.md)
- [product.md — §3.2 Manual Reporting, §3.3 System Pause](../../product.md)
- [screen2.png — Reports UI reference](../../screen2.png)
- [Phase 2.2 Final Report](../../archive/phase2-2/summary/final-report.md)
- [PLANNING.md](../../PLANNING.md)
- [step-0-tech-debt-cleanup.md](./step-0-tech-debt-cleanup.md)
- [step-1-manual-report-backend.md](./step-1-manual-report-backend.md)
- [step-2-system-state-backend.md](./step-2-system-state-backend.md)
- [step-3-type-sync.md](./step-3-type-sync.md)
- [step-4-reports-page.md](./step-4-reports-page.md)
- [step-5-system-state-ui.md](./step-5-system-state-ui.md)
- [step-6-palette-shifting.md](./step-6-palette-shifting.md)

## Author Checklist (master)

- [x] All step files created and linked
- [x] Phase-level acceptance criteria are measurable
- [x] PR/merge order documented
- [x] Tech debt triage completed (Phase 2.2 findings)
- [x] Screenshot reference included for UI steps
