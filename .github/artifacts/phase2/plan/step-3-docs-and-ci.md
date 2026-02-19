# Step 3 — Docs, Type Sync & CI

## Purpose
Lock in the new pulse contract and dashboard behavior by regenerating the TypeScript client, updating documentation, and extending CI/runbooks so the stack stays synchronized and verifiable.

## Deliverables
- Regenerated client output under `code/frontend/lib/generated` that includes the `stats/pulse` contract plus any new helper types.
- `code/frontend/README.md` sections describing the manual-save workflow, priority color rules, and how the Silence Indicator interprets `silenceState` values.
- CI workflow updates (e.g., `.github/workflows/phase2-ci.yml` or extensions to the Phase 1 workflow) that run backend tests, regenerate the client, and build the frontend when Phase 2 branches are opened.
- Documentation or metadata (step files, PR checklist entries) that mention the need to rerun the generator whenever backend models change.

## Primary files to change (required)
- [code/frontend/lib/generate-client.sh](code/frontend/lib/generate-client.sh)
- [code/frontend/lib/generated/index.ts](code/frontend/lib/generated/index.ts)
- [code/frontend/README.md](code/frontend/README.md)
- [.github/workflows/phase1-ci.yml](.github/workflows/phase1-ci.yml) *(if extending)* or a new `[.github/workflows/phase2-ci.yml](.github/workflows/phase2-ci.yml)`

## Detailed implementation steps
1. Start the backend via the existing dev script, then run `./code/frontend/lib/generate-client.sh http://127.0.0.1:8000/openapi.json ./code/frontend/lib/generated`, confirm the output includes schemas such as `PulseStats`, and commit the new files (or note stubs if auto-generation occurs only in CI).
2. Adjust `code/frontend/lib/api.ts` to import from `code/frontend/lib/generated/index.ts` (or a new helper) so the Pulse card and Task board use the generated `Task`, `PulseStats`, and `Client` types, ensuring camelCase alignment with the backend.
3. Update `code/frontend/README.md` with step-by-step regeneration instructions, a section describing the manual “Save changes” guard rails, and an explanation of when the Silence Indicator shows `engaged`, `stagnant`, or `paused` (including how pauses relate to `SystemState`).
4. Modify `.github/workflows/phase1-ci.yml` (or add `phase2-ci.yml`) so Phase 2 branches run backend tests (`pytest`), regenerate the client with `generate-client.sh`, and build the frontend; document the dependency on the running backend so the workflow includes a step to start the FastAPI server before generation.
5. Add a note to `.github/artifacts/PR_CHECKLIST.md` reminding reviewers to verify `phase2/step-3-docs-and-ci.md` updates and ensuring the generated client is fresh whenever backend models change, including `stats/pulse` and any future endpoints.

## Integration & Edge Cases
- If CI cannot start the backend (e.g., port conflicts), the workflow should fail fast and log the failure; consider reusing the existing backend startup approach from Phase 1 CI.
- When the generator output is large, limit diffs by only committing `index.ts` and optional `schemas.ts`; keep the script idempotent.

## Acceptance Criteria (required)
1. The generated TypeScript client checked into `code/frontend/lib/generated` exposes the `/stats/pulse` response interface and is referenced by the frontend (not just the stubbed helper).
2. README contains clear instructions for running the generator, the manual save semantics, and the silence state meanings (engaged/stagnant/paused).
3. CI workflow runs backend tests, generates the client, and builds the frontend on Phase 2 branches or PRs.
4. The Phase 2 plan references the regeneration requirement so reviewers know to rerun `generate-client.sh` before merge.

## Testing / QA (required)
- Tests to add: run `PYTHONPATH=$(pwd)/code/backend pytest` (already part of Step 1) and ensure that `npm run build` succeeds after the generator runs.
- Manual QA checklist:
  1. Start backend, run the generator, and confirm the generated client exports `PingStats`/`PulseStats` types.
  2. Rebuild the frontend and verify the dashboard still compiles and the Silence Indicator uses the generated types.
  3. Confirm README instructions are accurate by following them from a clean checkout.

## Files touched (repeat for reviewers)
- [code/frontend/lib/generate-client.sh](code/frontend/lib/generate-client.sh)
- [code/frontend/lib/generated/index.ts](code/frontend/lib/generated/index.ts)
- [code/frontend/README.md](code/frontend/README.md)
- [.github/workflows/phase1-ci.yml](.github/workflows/phase1-ci.yml)

## Estimated effort
- 1 developer day

## Concurrency & PR strategy
- Blocking steps:
  - Blocked until: `.github/artifacts/phase2/plan/step-1-pulse-api.md`
  - Blocked until: `.github/artifacts/phase2/plan/step-2-dashboard.md`
- Merge Readiness: false

## Risks & Mitigations
- Risk: CI run fails to regenerate the client due to missing backend dependencies. Mitigation: reuse Phase 1 backend startup script and log instructions for replicating locally.
- Risk: README instructions drift. Mitigation: include a note reminding authors to update the README whenever the manual-save flow changes.

## References
- [.github/artifacts/phase1/summary/step-4-5-frontend-type-sync-summary.md](.github/artifacts/archive/phase1/summary/step-4-5-frontend-type-sync-summary.md)
- [code/frontend/lib/generate-client.sh](code/frontend/lib/generate-client.sh)
- [.github/workflows/phase1-ci.yml](.github/workflows/phase1-ci.yml)

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] Primary files to change referenced
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests noted or manual QA defined
- [ ] Manual QA checklist added
