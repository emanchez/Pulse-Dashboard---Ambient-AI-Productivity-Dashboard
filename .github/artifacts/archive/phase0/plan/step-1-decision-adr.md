# Step 1 — Decision & ADR Consolidation

## Purpose
Collect and formalize operational decisions required for Phase‑0 (Ollama posture, auth, retention, CI/hosting defaults) and produce ADR-style records.

## Deliverables
- `project/.github/artifacts/phase0/summary/decision-records.md` (ADR entries)

## Owner & Due
- owner: TBD
- due: 2026-02-24

## Verification commands
- Review ADR file: `cat project/.github/artifacts/phase0/summary/decision-records.md`
- Ensure CI and code reference JWT requirement: run `pytest -q` (Step 5) and inspect `phase0-smoke.json` after CI run.

## Primary files to change
- `project/.github/artifacts/phase0/summary/decision-records.md`

## Detailed implementation steps
1. Review `misc/PDD.md` and `project/.github/architecture.md` for existing decisions.
2. Create `decision-records.md` with ADR entries: Ollama inference posture, OAuth/JWT strategy (single-user phase), data retention & backups, CI/CD posture, budget bounds.
3. Add metadata for each ADR: `status: proposed`, `owner: TBD`, `date: YYYY-MM-DD`, `acceptance:` list.
4. Open PR on branch `phase0/step-1-decision-adr` and request reviewers.

## Integration & Edge Cases
- Ensure ADRs reference any existing artifacts and do not contradict `architecture.md`.

## Acceptance Criteria
1. `decision-records.md` exists under `project/.github/artifacts/phase0/summary/`.
2. Each ADR includes decision, context, alternatives, consequences, owner, date, and at least one measurable acceptance item.
3. PR opened and at least one reviewer assigned.

## Testing / QA
- Manual review of ADR content by reviewer; acceptance criteria checked during review.

## Files touched
- `project/.github/artifacts/phase0/summary/decision-records.md`

## Estimated effort
2–4 hours

## Concurrency & PR strategy
- Can be authored in parallel with Step 2 and Step 4; final signoff should precede Step 5.

## Risks & Mitigations
- Risk: conflicting choices with `architecture.md`. Mitigation: reference and reconcile differences in ADRs.

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] Acceptance Criteria are measurable/testable
- [ ] PR branch `phase0/step-1-decision-adr` created
