# Step 5 — Test Stubs, KPIs & Budget Signoff

## Purpose
Provide minimal tests, KPI documentation, retention/budget notes, and run final smoke verification to achieve Phase‑0 signoff.

## Deliverables
- `tests/test_model_serialization.py`
- `tests/test_actionlog_write.py`
- `project/.github/artifacts/phase0/kpis.md`
- `project/.github/artifacts/phase0/retention.md`
- `project/.github/artifacts/phase0/budget.md`

## Owner & Due
- owner: TBD
- due: 2026-02-25

## Verification commands
- Run test discovery: `pytest -q` (tests should either run or be marked skipped with TODO messages).
- Confirm KPI/retention/budget docs exist: `ls -l project/.github/artifacts/phase0/`

## Primary files to change
- `tests/` directory (add stubs)
- `project/.github/artifacts/phase0/`

## Detailed implementation steps
1. Add `tests/test_model_serialization.py` with a minimal round-trip serialization test (or a skipped TODO if models missing).
2. Add `tests/test_actionlog_write.py` to simulate ActionLog write-on-save (use in-memory SQLite or mark as skipped if backend absent).
3. Draft `kpis.md`, `retention.md`, `budget.md` under `project/.github/artifacts/phase0/`.
4. Commit on `phase0/step-5-tests-kpis` and open PR referencing the CI workflow for verification.

## Integration & Edge Cases
- If backend code is not present, tests should be discovery-friendly and explicitly skipped with TODOs noted.

## Acceptance Criteria
1. Tests are discoverable by `pytest` (or are marked skipped with clear TODOs).
2. KPI, retention, and budget docs present under `project/.github/artifacts/phase0/`.

## Testing / QA
- Run CI smoke workflow to detect tests and produce report.

## Files touched
- `tests/test_model_serialization.py`
- `tests/test_actionlog_write.py`
- `project/.github/artifacts/phase0/kpis.md`
- `project/.github/artifacts/phase0/retention.md`
- `project/.github/artifacts/phase0/budget.md`

## Estimated effort
1–2 days (dependent on CI iteration)

## Concurrency & PR strategy
- Final signoff in this step should wait for Step 1 acceptance and for Step 3 CI to be available to run smoke checks.

## Risks & Mitigations
- Risk: tests fail due to missing backend. Mitigation: use test doubles and explicit skips.

## Author Checklist
- [ ] Tests added or marked skipped with TODOs
- [ ] KPI/retention/budget docs drafted
