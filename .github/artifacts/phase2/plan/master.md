# Phase 2 — Ambient Sensing & Tactical CRUD

## Scope
Expand Phase 1 skeleton into the ambient sensing experience described in the PDD by adding a pulse telemetry endpoint, turning the Bento dashboard into a manual-save task surface, and locking in the supporting documentation, type-sync, and CI runbook so the full stack tracks silence gaps and tactical edits.

## Phase-level Deliverables
- Backend pulse telemetry endpoint that reports silence state, last action timestamp, and respects SystemState pauses.
- Frontend Bento layout wired to the pulse API with a manual “Save changes” flow that batches visible edits until the user confirms them and uses the PDD-defined priority palette.
- Updated docs/type-sync/CI coverage that show how to regenerate API types, document the manual-save flow, and surface the pulse contract to reviewers.

## Steps (ordered)
1. Step 1 — [step-1-pulse-api.md](./step-1-pulse-api.md)
2. Step 2 — [step-2-dashboard.md](./step-2-dashboard.md)
3. Step 3 — [step-3-docs-and-ci.md](./step-3-docs-and-ci.md)

## Merge Order
1. `.github/artifacts/phase2/plan/step-1-pulse-api.md` — branch: `phase2/step-1-pulse-api`
2. `.github/artifacts/phase2/plan/step-2-dashboard.md` — branch: `phase2/step-2-dashboard`
3. `.github/artifacts/phase2/plan/step-3-docs-and-ci.md` — branch: `phase2/step-3-docs-ci`

## Phase Acceptance Criteria
- **AC1:** `GET /stats/pulse` is available, authenticated, and reports `silenceState`, `lastActionAt`, and `gapMinutes` in camelCase JSON with the correct logic for engaged/stagnant/paused states.
- **AC2:** Dashboard UI shows the Silence Indicator (Zone A) with paused/stagnant/engaged badges, and the Task List (Zone B) supports deferred saves until the user clicks “Save changes” plus PDD-compliant colors per priority.
- **AC3:** CI/runbook includes steps to regenerate the TypeScript client, rerun backend tests, and build the frontend so future analytics or UI changes are covered.

## Concurrency groups & PR strategy
- Step 1 is foundational; no blockers and can merge as soon as AC1 is met.
- Step 2 requires Step 1 so it remains blocked until the pulse API is merged (`phase2/step-1-pulse-api`). Merge Readiness remains `false` until that happens.
- Step 3 depends on both Step 1 and Step 2 because the regenerated client and documentation need the final API contract and UI flows. Blocked until `.github/artifacts/phase2/plan/step-1-pulse-api.md` and `.github/artifacts/phase2/plan/step-2-dashboard.md` are merged.

## Verification Plan
1. Run backend tests: `PYTHONPATH=$(pwd)/code/backend pytest code/backend/tests/test_stats.py`.
2. Start the backend, obtain a JWT, and curl `GET http://localhost:8000/stats/pulse` to confirm the JSON shape and silenceState logic.
3. In `code/frontend`, run `npm install && npm run dev`, visit the dashboard, edit a task, and ensure “Save changes” persists edits and the Silence Indicator matches the pause data.
4. Regenerate API client: `./code/frontend/lib/generate-client.sh http://127.0.0.1:8000/openapi.json ./code/frontend/lib/generated` and verify the generated types cover `/stats/pulse`.
5. Run `cd code/frontend && npm run build` and confirm the generated frontend bundle passes.

## Risks, Rollbacks & Migration Notes
- Risk: `stats/pulse` logic mis-evaluates `SystemState` ranges. Mitigation: add tests that seed overlapping SystemState records and assert the response stays `paused`.
- Risk: Frontend “Save changes” misfires and triggers unwanted API calls. Mitigation: throttle button state, keep local edit cache, and add logging for failed requests.
- Rollback: If the pulse endpoint regresses, temporarily revert `code/backend/app/api/stats.py` and disable frontend consumption by defaulting `silenceState` to `engaged` until fixes land.

## References
- [.github/artifacts/PDD.md](.github/artifacts/PDD.md)
- [.github/artifacts/architecture.md](.github/artifacts/architecture.md)
- [.github/artifacts/agents.md](.github/artifacts/agents.md)
- [code/backend/app/api/tasks.py](code/backend/app/api/tasks.py)
- [code/frontend/app/page.tsx](code/frontend/app/page.tsx)

## Author Checklist (master)
- [ ] All step files created and linked
- [ ] Phase-level acceptance criteria are measurable
- [ ] PR/merge order documented
