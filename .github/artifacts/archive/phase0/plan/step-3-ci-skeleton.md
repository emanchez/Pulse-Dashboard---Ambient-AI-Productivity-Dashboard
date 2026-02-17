# Step 3 — CI Skeleton & Smoke Workflow

## Purpose
Provide a minimal CI workflow to validate linting, test discovery, and smoke flows so PRs can be automatically verified during Phase‑0.

## Deliverables
- `project/.github/workflows/phase0-smoke.yml`

## Owner & Due
- owner: TBD
- due: 2026-02-23

## Verification commands
- Trigger workflow via PR or manual dispatch.
- Locally, run tests discovery: `pytest -q` and inspect `frontend/assets/phase0/`.
- After run, download `phase0-smoke` artifact from Actions and check `phase0-smoke.json` contains keys `lint`, `tests`, `artifact_check`.

## Backup & Migration note
- If any CI step modifies persistence or runs migrations, include pre-merge backup command: `sqlite3 data.db .dump > backup-$(date +%F).sql`.

## Primary files to change
- `project/.github/workflows/phase0-smoke.yml`

## Detailed implementation steps
1. Detect repo runtimes conservatively (check for `pyproject.toml`, `package.json`, `tests/`).
2. Create `phase0-smoke.yml` with jobs: `lint`, `test-discovery`, and `artifact-check` that produce a `phase0-smoke.json` artifact.
3. Use conditional shell steps so jobs succeed if linters/tools are absent (echo `no linter found`).
4. Commit on `phase0/step-3-ci-skeleton` and open PR.

## Integration & Edge Cases
- Avoid hard-failing on missing language-specific toolchains; prefer discovery and structured artifact output.

## Acceptance Criteria
1. `project/.github/workflows/phase0-smoke.yml` exists.
2. Workflow writes `phase0-smoke.json` containing keys: `lint`, `tests`, `artifact_check` when run.

## Testing / QA
- Trigger workflow on a test branch to verify output artifact and job behavior.

## Files touched
- `project/.github/workflows/phase0-smoke.yml`

## Estimated effort
2–3 hours

## Concurrency & PR strategy
- Can be merged while Steps 2 and 4 are in review. Branch: `phase0/step-3-ci-skeleton`.

## Risks & Mitigations
- Risk: CI attempts to run heavy installs. Mitigation: keep steps lightweight and use discovery logic.

## Author Checklist
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] Workflow file added
