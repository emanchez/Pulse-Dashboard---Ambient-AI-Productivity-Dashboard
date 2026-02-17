# Phase X — Master Plan

## Scope
Short summary of phase goals and boundaries.

## Phase-level Deliverables
- Bulleted list of phase deliverables (features, cross-cutting changes, releases).

## Steps (ordered)
1. Step 1 — [step-1-short-title.md](./step-1-short-title.md)
2. Step 2 — [step-2-short-title.md](./step-2-short-title.md)

## Merge Order

- When the numeric `Steps (ordered)` list does not reflect the actual merge sequence, populate this `Merge Order` subsection with the exact merge sequence (by step file path and suggested branch name). Example:
	1. `.github/artifacts/phase1/plan/step-2-db-schema.md` — branch: `phase-1/step-2-db-schema`
	2. `.github/artifacts/phase1/plan/step-3-api.md` — branch: `phase-1/step-3-api`

## Phase Acceptance Criteria
- High-level measurable outcomes and release criteria.

## Concurrency groups & PR strategy
- Group steps that can be worked on in parallel. Define merge order and blocking dependencies.

## Verification Plan
- End-to-end checks, smoke tests, and release checklist. Include commands to run and test coverage expectations.

## Risks, Rollbacks & Migration Notes
- Enumerate major risks and rollback steps. For data migrations call out required backups and migration scripts.

## References
- Links to step files, schemas, and external docs.

## Author Checklist (master)
- [ ] All step files created and linked
- [ ] Phase-level acceptance criteria are measurable
- [ ] PR/merge order documented
