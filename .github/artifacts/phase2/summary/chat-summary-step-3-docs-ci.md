## Step 3 — Docs, Type Sync & CI — Implementation Summary

Purpose
- Finalize Phase 2 by ensuring frontend/backend type-sync, documentation, and CI coverage for the new `stats/pulse` contract and the manual-save dashboard flow.

What I changed (high level)
- Fixed frontend `generate:api` script to write generated output into `code/frontend/lib/generated`.
- Pinned `@hey-api/openapi-ts` as a devDependency so the generator is reproducible in CI.
- Added `code/frontend/lib/generated/types.ts` containing the canonical `Task` type.
- Updated `code/frontend/lib/generated/index.ts` to barrel-export `PulseStats` and `Task`.
- Updated `code/frontend/lib/api.ts` to import and re-export `Task` from the generated stubs (removed the inline duplicate type).
- Extended `.github/workflows/phase1-ci.yml` to trigger on `phase-2/**` branches and fixed the E2E pytest path.
- Expanded `code/frontend/README.md` with explicit sections: Regenerating the API Client, Manual Save Workflow, and Silence Indicator States.
- Appended an API-contract-regeneration reminder to `.github/artifacts/PR_CHECKLIST.md`.
- Marked the Step 3 plan file as `Merge Readiness: true`.

Why these changes
- Ensures the frontend and CI use the same canonical types and enforces regeneration in CI as a safety gate.
- Keeps the `code/frontend/lib/generated` directory as the committed, authoritative contract surface so reviewers and CI can validate changes.

Verification performed
- Ran `cd code/frontend && npm ci && npm run build` — Next build completed successfully and type-checks passed.
- Confirmed CI workflow now includes `phase-2/**` push trigger and the generator step.

Next recommended steps
- Optionally run the actual `@hey-api/openapi-ts` generator against a running backend to produce a fuller machine-generated client (currently `pulseClient.ts` is the canonical stub and the generator is pinned).
- Consider adding a CI job requirement that the generated client be committed when changes affect API schemas (or fail the PR if diffs are present).

Files changed (summary)
- code/frontend/package.json (script + devDependency)
- code/frontend/lib/generated/types.ts (new)
- code/frontend/lib/generated/index.ts (updated)
- code/frontend/lib/api.ts (updated)
- .github/workflows/phase1-ci.yml (updated)
- code/frontend/README.md (updated)
- .github/artifacts/PR_CHECKLIST.md (updated)
- .github/artifacts/phase2/plan/step-3-docs-and-ci.md (updated Merge Readiness)

Author note
- Created by an automated implementation pass; if you want the generator to replace the handwritten `pulseClient.ts`, I can run the generation against a live backend and update the committed files accordingly.
