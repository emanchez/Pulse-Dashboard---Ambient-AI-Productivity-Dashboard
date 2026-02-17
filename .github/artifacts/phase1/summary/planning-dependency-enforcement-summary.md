# Planning: Dependency & Enforcement Summary

Date: 2026-02-17

Summary of this session:

- Discovered a dependency mismatch: Step 4 (`frontend-setup.md`) was declared in the master as depending on Step 5 (`type-sync.md`) but numeric ordering listed Step 4 before Step 5, creating potential merge confusion.
- Clarified why the dependency exists: the frontend expects a generated TypeScript client and package.json changes produced by the type-sync step.

Actions taken:

- Added strict dependency/merge clauses to planning guidance:
  - Updated `.github/artifacts/copilot-instructions.md` to require `Blocking steps:` and `Merge Readiness:` fields, rules for stubs/feature-flags, and `Depends-On:` PR metadata.
  - Updated `.github/artifacts/PLANNING.md` to mandate a `Merge Order` subsection when numeric step order differs, and require `Blocking steps:` and `Merge Readiness:` in masters/steps.
  - Updated templates: `.github/artifacts/master-template.md` (added `Merge Order` subsection) and `.github/artifacts/step-template.md` (require `Blocking steps:`, `Merge Readiness:`, and `Stub/FeatureFlag` notes).
- Applied the new fields to Phase 1 steps and master:
  - Added `Blocking steps:` and `Merge Readiness:` to the following files:
    - `.github/artifacts/phase1/plan/master.md`
    - `.github/artifacts/phase1/plan/backend-setup.md`
    - `.github/artifacts/phase1/plan/data-models.md`
    - `.github/artifacts/phase1/plan/api-skeleton.md`
    - `.github/artifacts/phase1/plan/frontend-setup.md` (marked blocked on type-sync, `Merge Readiness: false`)
    - `.github/artifacts/phase1/plan/type-sync.md`
- Created reviewer aid: `.github/artifacts/PR_CHECKLIST.md` (checks for `Merge Readiness`, `Depends-On:`, stubs, branch naming, acceptance criteria).
- Created and then removed a lightweight `scripts/validate_pr_metadata.py` validator at the user's request; no remaining references to it exist in the repo.

Verification performed:

- Ran the validator locally while it existed to scan Phase 1 step files; fixed missing metadata in step files after adding required fields.
- Confirmed all Phase 1 plan files now include required metadata and the local validator run returned OK prior to script removal.

Notes & next steps:

- Recommendation: add a CI job (or small bot) to enforce `Blocking steps:` / `Merge Readiness:` and `Depends-On:` in PRs. This is optional; for now reviewers should follow `PR_CHECKLIST.md`.
- If you want, I can open a PR with these planning changes, or add a GitHub Actions job that runs a lightweight metadata check.

Files touched (high-level):
- Updated: `.github/artifacts/copilot-instructions.md`, `.github/artifacts/PLANNING.md`, `.github/artifacts/master-template.md`, `.github/artifacts/step-template.md`
- Updated: `.github/artifacts/phase1/plan/master.md`, `backend-setup.md`, `data-models.md`, `api-skeleton.md`, `frontend-setup.md`, `type-sync.md`
- Added: `.github/artifacts/PR_CHECKLIST.md`
- Added then removed: `scripts/validate_pr_metadata.py` (removed per user request)

Author: automated assistant (pair-programming session)
