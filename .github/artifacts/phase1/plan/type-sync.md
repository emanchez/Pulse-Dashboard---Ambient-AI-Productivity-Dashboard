# Step 5 — Type Sync

## Purpose
Automate generation of TypeScript clients from FastAPI openapi.json using @hey-api/openapi-ts.

## Deliverables
- code/frontend/lib/api.ts: Generated TypeScript client.
- code/frontend/package.json: Add @hey-api/openapi-ts script.
- Script to regenerate client after API changes.

## Primary files to change
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts)
- [code/frontend/package.json](code/frontend/package.json)

## Detailed implementation steps
1. Add @hey-api/openapi-ts to package.json.
2. Create script to fetch openapi.json from backend and generate api.ts.
3. Run script to generate initial client.

## Integration & Edge Cases
- Regenerate after API changes.

## Acceptance Criteria
1. api.ts generated without errors.
2. Frontend can import and use client functions.

## Testing / QA
- Manual QA: Import client in component.

## Files touched
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts)
- [code/frontend/package.json](code/frontend/package.json)

## Estimated effort
0.5 dev days

## Concurrency & PR strategy
- Branch: phase-1/step-5-type-sync
- Depends on step 3 (API skeleton).

## Risks & Mitigations
- Generation failures; check openapi spec.

## References
- [architecture.md](../architecture.md)

## Author Checklist
- [x] Purpose filled
- [x] Deliverables listed
- [x] Primary files to change contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable</content>
<parameter name="filePath">/home/manny/Documents/projects/personalDash2026/project/.github/artifacts/phase1/plan/type-sync.md