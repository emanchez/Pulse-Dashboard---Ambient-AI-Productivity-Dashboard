# Phase 2.2 — Tasks Dashboard UI: Master Plan

## Scope

Rebuild the main dashboard to match the "Focused Engagement" screenshot. Introduces a dark bento-box layout with two nav tabs (Tasks, Reports), a Productivity Pulse area chart, a Current Session tracker, Daily Goals checklist, Quick Access cards, and a Task Queue table. Adds a `SessionLog` backend entity, a `/stats/flow-state` endpoint (calculated from `ActionLog`), and a session management API. All new backend data is stub/calculated — no Ollama required. Silence Indicator state from PDD §4.1 is surfaced through the `AppNavBar` focus badge and `FocusHeader` subtitle copy. The Reports tab is an empty shell. Existing `PulseCard` and `TaskBoard` components are preserved untouched.

## Phase-level Deliverables

- `SessionLog` SQLAlchemy model + Pydantic schema + DB migration
- Three session management endpoints: `POST /sessions/start`, `POST /sessions/stop`, `GET /sessions/active`
- `FlowStateSchema` + `GET /stats/flow-state` endpoint (ActionLog-derived time-series)
- Regenerated `lib/generated/` TypeScript client via `@hey-api/openapi-ts`
- Typed wrapper functions in `lib/api.ts` for all new endpoints
- `AppNavBar` component — dark nav, Reports/Tasks tabs, silence-state badge, avatar
- `BentoGrid` `variant="tasks-dashboard"` (3-row responsive layout)
- `FocusHeader` component with state-aware subtitle copy
- `ProductivityPulseCard` — Recharts `AreaChart` + Flow State % headline
- `CurrentSessionCard` — active session name, elapsed ticker, progress bar
- `DailyGoalsCard` — today's tasks with completion icons + strikethrough
- `QuickAccessCard` — reusable icon + title + subtitle quick-link card
- `TaskQueueTable` — read-only task table with status pill badges
- `/app/tasks/page.tsx` — full Tasks dashboard page
- `/app/reports/page.tsx` — Reports tab shell
- `recharts` added as production dependency

## Steps (ordered)

1. Step 1 — [step-1-session-model.md](./step-1-session-model.md)
2. Step 2 — [step-2-flow-state.md](./step-2-flow-state.md)
3. Step 3 — [step-3-type-sync.md](./step-3-type-sync.md)
4. Step 4 — [step-4-layout-shell.md](./step-4-layout-shell.md)
5. Step 5 — [step-5-dashboard-components.md](./step-5-dashboard-components.md)
6. Step 6 — [step-6-wire-silence-indicator.md](./step-6-wire-silence-indicator.md)

## Merge Order

Steps 1 and 2 are independent and can be merged in either order. Step 4 is also independent of Steps 1–2 and may be merged in parallel. Step 3 is blocked until both Steps 1 and 2 are merged. Step 5 is blocked until Step 4. Step 6 is blocked until Steps 3 and 5.

1. `.github/artifacts/phase2-2/plan/step-1-session-model.md` — branch: `phase-2-2/step-1-session-model`
2. `.github/artifacts/phase2-2/plan/step-2-flow-state.md` — branch: `phase-2-2/step-2-flow-state`
3. `.github/artifacts/phase2-2/plan/step-4-layout-shell.md` — branch: `phase-2-2/step-4-layout-shell` *(parallel with 1 & 2)*
4. `.github/artifacts/phase2-2/plan/step-3-type-sync.md` — branch: `phase-2-2/step-3-type-sync` *(after 1 & 2 merged)*
5. `.github/artifacts/phase2-2/plan/step-5-dashboard-components.md` — branch: `phase-2-2/step-5-dashboard-components` *(after step 4 merged)*
6. `.github/artifacts/phase2-2/plan/step-6-wire-silence-indicator.md` — branch: `phase-2-2/step-6-wire-silence-indicator` *(after steps 3 & 5 merged)*

## Phase Acceptance Criteria

1. `GET /sessions/active` returns `200` with a valid `SessionLogSchema` JSON body (or `null` when no session is active) for an authenticated user.
2. `POST /sessions/start` with `{ "taskName": "UI Redesign", "goalMinutes": 60 }` returns `201` with a `SessionLogSchema` body; a second call to the same endpoint returns the existing active session (idempotent).
3. `POST /sessions/stop` returns `200` with the stopped session; `endedAt` is non-null and `elapsedMinutes` is a positive integer.
4. `GET /stats/flow-state` returns `200` with `{ flowPercent, changePercent, windowLabel, series }` for an authenticated user; `series` is an array of `{ time, activityScore }` objects.
5. `npm run generate:api` exits 0 and the generated `lib/generated/` files contain TypeScript types for `SessionLog`, `FlowState`, and `FlowPoint`.
6. `npm run build` exits 0 with zero TypeScript errors.
7. Opening `http://localhost:3000` redirects to `/tasks`; the Tasks page renders all bento zones matching the screenshot layout.
8. With `gap_minutes > 2880` in the DB the `AppNavBar` badge shows amber "STAGNANT" text and `FocusHeader` subtitle reads "Momentum gap detected. Re-engage to restore flow."
9. With an active `SystemState` vacation row the `AppNavBar` badge shows sky "SYSTEM PAUSED" and the subtitle updates accordingly.
10. Starting a session via `POST /sessions/start` causes `CurrentSessionCard` to display the session name and a live elapsed-minutes counter (within 30 s of polling interval).

## Concurrency groups & PR strategy

**Group A (parallel — no blockers):**
- `phase-2-2/step-1-session-model`
- `phase-2-2/step-2-flow-state`
- `phase-2-2/step-4-layout-shell`

**Group B (blocked on Group A Step 1 + Step 2):**
- `phase-2-2/step-3-type-sync`

**Group C (blocked on Group A Step 4):**
- `phase-2-2/step-5-dashboard-components`

**Group D (blocked on Group B + Group C):**
- `phase-2-2/step-6-wire-silence-indicator`

All PRs must include `Depends-On: <branch>` in the PR description when a blocker is unmerged, and carry a `depends` label until resolved.

## Verification Plan

```bash
# 1. Backend unit + integration tests
cd code/backend
source ../../.venv/bin/activate
pytest tests/ -v --tb=short

# 2. Smoke-test new endpoints (TOKEN must be a valid JWT)
curl -s localhost:8000/health
curl -s -X POST localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"dev","password":"dev"}' | jq .access_token

export TOKEN=<value from above>

curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/stats/flow-state | jq .
curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/sessions/active | jq .
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"taskName":"UI Redesign","goalMinutes":60}' \
  localhost:8000/sessions/start | jq .
curl -s -X POST -H "Authorization: Bearer $TOKEN" localhost:8000/sessions/stop | jq .

# 3. Type sync
cd code/frontend
npm run generate:api   # must exit 0

# 4. Frontend build gate
npm run build          # zero TS errors, zero missing module errors

# 5. Manual E2E
# a. Start both servers (backend :8000, frontend :3000)
# b. Open http://localhost:3000 → should redirect to /tasks
# c. Verify all bento zones render (no blank panels)
# d. Verify AppNavBar badge colour changes with DB state changes per Phase AC #8 and #9
# e. Start a session; verify CurrentSessionCard updates within 30 s
# f. Complete a task; verify TaskQueueTable shows green "Completed" pill
```

Coverage expectation: all new endpoint happy-paths and at least one validation/auth failure path per endpoint covered by `pytest` assertions.

## Risks, Rollbacks & Migration Notes

| Risk | Mitigation |
|---|---|
| `session_logs` table requires a DB migration | Run `alembic revision --autogenerate -m "add_session_logs"` before merge; test on a copy of `data/dev.db` first |
| `@hey-api/openapi-ts@0.27.0` generates files that conflict with hand-written stubs | Hand-written stubs are fully replaced; commit old stubs to a backup branch before running the generator |
| Recharts bundle size | Tree-shaking is automatic with Next.js; only import used components (`AreaChart`, `Area`, `XAxis`, `Tooltip`) |
| `elapsedMinutes` computed property on `SessionLogSchema` requires UTC-awareness | Use `datetime.utcnow()` consistently; add a unit test asserting `elapsedMinutes ≥ 0` immediately after `start` |
| Flow State endpoint slow with large `ActionLog` tables | Add `index on action_logs(user_id, timestamp)` in the migration; query limited to last 6 hours |

**Rollback:** If the migration breaks `dev.db`, restore from `data/dev.db.bak`. The `data/dev.db.bak` snapshot must be refreshed immediately before applying the migration.

## References

- [PDD.md — §4.1 Silence Gap Analysis](./../PDD.md)
- [PDD.md — §5 UI/UX Strategy](./../PDD.md)
- [architecture.md](./../architecture.md)
- [agents.md](./../agents.md)
- [step-1-session-model.md](./step-1-session-model.md)
- [step-2-flow-state.md](./step-2-flow-state.md)
- [step-3-type-sync.md](./step-3-type-sync.md)
- [step-4-layout-shell.md](./step-4-layout-shell.md)
- [step-5-dashboard-components.md](./step-5-dashboard-components.md)
- [step-6-wire-silence-indicator.md](./step-6-wire-silence-indicator.md)

## Author Checklist (master)

- [x] All step files created and linked
- [x] Phase-level acceptance criteria are measurable
- [x] PR/merge order documented
