# Step 1 — Pulse API

## Purpose
Provide authenticated pulse telemetry that reports the time since the last ActionLog, the current silence state, and whether a SystemState pause suppresses stagnation alerts.

## Deliverables
- `code/backend/app/api/stats.py` with a `GET /stats/pulse` route guarded by JWT and returning `PulseStatsSchema`.
- `code/backend/app/schemas/stats.py` (new) defining the response model with camelCase aliases and the 48h threshold logic.
- Tests in `code/backend/tests/test_stats.py` covering engaged, stagnant, and paused cases, plus verifying the paused override for overlapping SystemState records.
- Router registration in `code/backend/app/main.py` and relevant docs (API spec comments explaining `silenceState`).

## Primary files to change (required)
- [code/backend/app/api/stats.py](code/backend/app/api/stats.py)
- [code/backend/app/schemas/stats.py](code/backend/app/schemas/stats.py)
- [code/backend/app/main.py](code/backend/app/main.py)
- [code/backend/tests/test_stats.py](code/backend/tests/test_stats.py)

## Detailed implementation steps
1. Define `PulseStatsSchema` in `code/backend/app/schemas/stats.py` that inherits from `CamelModel`, exposes `silence_state`, `last_action_at`, `gap_minutes`, and `paused_until`, sets `alias_generator` to the camel converter, and includes `json_schema_extra` that documents the 48h threshold and paused override.
2. Add helper utilities (e.g., `get_last_action_log(session)`, `get_active_pause(session)`) in `stats.py` or a shared helper module that load the most recent `ActionLog`, calculate `gap_minutes` (now - timestamp), and search for the latest active `SystemState` where `mode_type` is `Vacation` or `Leave` and `start_date <= now <= end_date`.
3. Implement `GET /stats/pulse` in `code/backend/app/api/stats.py` using `router = APIRouter(prefix="/stats")`, reusing `get_current_user` for JWT validation, and return a `PulseStatsSchema` constructed from the helper data, selecting `silenceState` (`paused`/`stagnant`/`engaged`) as per the detection order (paused first, then gap, else engaged).
4. Update `code/backend/app/main.py` to include the new router (`from .api.stats import router as stats_router`) and mount it under the FastAPI app, ensuring it participates in JWT auth middleware and ActionLog logging if applicable.
5. Create `code/backend/tests/test_stats.py` with pytest fixtures that insert ActionLog timestamps (now, now - 2d, now - 60m) and SystemState entries; use `AsyncSession` from `get_async_session` or helper fixtures to persist data, then assert responses for paused/stagnant/engaged states and 401 when no token is supplied.

## Integration & Edge Cases
- When no ActionLog entries exist (fresh install), treat the gap as zero (engaged) until a log appears.
- If multiple SystemState entries overlap, pick the one with the latest `end_date` for the `pausedUntil` display.
- Ensure timezone-naive datetimes (UTC) are used consistently.

## Acceptance Criteria (required)
1. `GET /stats/pulse` returns 200 + JSON `{silenceState,lastActionAt,gapMinutes}` for an authenticated user with a recent ActionLog.
2. When the user has a SystemState of mode Vacation or Leave covering `now`, the response returns `silenceState: paused` and a non-null `pausedUntil` at least as late as the SystemState `endDate`.
3. A gap > 2880 minutes (48h) with no active pause yields `silenceState: stagnant`; smaller gaps yield `engaged`.
4. Tests cover engaged, stagnant, and paused branches and confirm the endpoint refuses unauthorized access with 401.

## Testing / QA (required)
- Tests to add: `code/backend/tests/test_stats.py` with fixtures for ActionLog timestamps and SystemState ranges; run via `PYTHONPATH=$(pwd)/code/backend pytest code/backend/tests/test_stats.py`.
- Manual QA checklist:
  1. Start backend, log in via `/login`, call `/stats/pulse` with the token, and verify the JSON shape and `silenceState`.
  2. Create a SystemState covering today, call `/stats/pulse`, and confirm `silenceState` flips to `paused` and `pausedUntil` matches the end date.
  3. Delete logs and assert the endpoint still returns `engaged` (fresh start state).

## Files touched (repeat for reviewers)
- [code/backend/app/api/stats.py](code/backend/app/api/stats.py)
- [code/backend/app/schemas/stats.py](code/backend/app/schemas/stats.py)
- [code/backend/app/main.py](code/backend/app/main.py)
- [code/backend/tests/test_stats.py](code/backend/tests/test_stats.py)

## Estimated effort
- 1-2 developer days

## Concurrency & PR strategy
- Blocking steps: None.
- Merge Readiness: true

## Risks & Mitigations
- Risk: SystemState ranges misaligned with UTC time. Mitigation: ensure all datetimes created in UTC and document expectations in the schema docstring.
- Risk: No ActionLog entries -> `gapMinutes` may be undefined. Mitigation: default to zero minutes when no logs exist.

## References
- [.github/artifacts/architecture.md](.github/artifacts/architecture.md)
- [.github/artifacts/PDD.md](.github/artifacts/PDD.md)
- [code/backend/models/action_log.py](code/backend/app/models/action_log.py)

## Author Checklist (must complete before PR)
- [x] Purpose filled
- [x] Deliverables listed
- [x] Primary files to change referenced
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/` (happy path + validation)
- [x] Manual QA checklist added
