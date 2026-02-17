# Phase‑0 — Master Plan

## Purpose
Provide a Phase‑0 master plan that follows the new master/step planning framework. This document lists ordered steps, deliverables, verification criteria, concurrency guidance, and next actions for Phase‑0.

## Phase-level Deliverables
- Decision & ADR records for runtime posture, auth, retention, CI/hosting defaults
- Repository policy and contributor command templates
- CI skeleton and a Phase‑0 smoke workflow
- Three Phase‑0 wireframe PNGs under `frontend/assets/phase0/`
- Test stubs plus KPI, retention, and budget documents

## Steps (ordered)
1. Step 1 — [step-1-decision-adr.md](./step-1-decision-adr.md)
2. Step 2 — [step-2-repo-policy.md](./step-2-repo-policy.md)
3. Step 3 — [step-3-ci-skeleton.md](./step-3-ci-skeleton.md)
4. Step 4 — [step-4-wireframes.md](./step-4-wireframes.md)
5. Step 5 — [step-5-tests-kpis.md](./step-5-tests-kpis.md)

## Phase Acceptance Criteria
- All five step documents exist and include measurable acceptance criteria.
- `project/.github/workflows/phase0-smoke.yml` present and able to produce a `phase0-smoke.json` artifact.
- Wireframes committed to `frontend/assets/phase0/` and renderable.
- Test stubs and artifact docs present under `project/.github/artifacts/phase0/` and discoverable by CI.

## Concurrency groups & PR strategy
- Steps 2 and 4 can be worked in parallel. Steps 1 should be reviewed before final signoff in Step 5.
- Branch naming for Phase‑0 feature work: `phase0/step-<n>-short-desc`.

## Verification Plan
- Each step document includes testable acceptance criteria. Example: "`GET /health` returns 200" or "`phase0-smoke.json` contains keys `lint`, `tests`, `artifact_check`."
- CI workflow runs lint/test-discovery and writes JSON artifact summarizing results.

## Risks, Rollbacks & Migration Notes
- Any change to persistence MUST include a pre-merge backup step and atomic-write migration notes in the step that changes storage.

## References
- See step files listed above under `./`.

## Author Checklist (master)
- [ ] All step files created and linked
- [ ] Phase-level acceptance criteria are measurable
- [ ] PR/merge order documented

Recorded on: 2026-02-17
