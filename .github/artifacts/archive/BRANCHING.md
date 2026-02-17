# BRANCHING.md

Purpose
- Document branch naming, PR process, and recommended protections for the repository.

Branch naming
- `main` — protected, only merge via PR
- `phase0/step-<n>-short-desc` — Phase‑0 feature branches
- `feature/*` — short-lived feature branches
- `hotfix/*` — urgent fixes targeting `main`

PR requirements
- All changes must be made via PR (no direct pushes to `main`).
- PR body must reference a step file or ADR where applicable.
- Include at least one reviewer and link to affected step(s).
- PR must include the acceptance checklist from the corresponding step file.

Recommended GitHub settings
- Protect `main` and require at least one approving review before merge.
- Require status checks per step (e.g., `phase0-smoke` job once available).

Example workflow
1. Create branch: `git checkout -b phase0/step-2-repo-policy`
2. Commit changes and push: `git push origin phase0/step-2-repo-policy`
3. Open PR with acceptance checklist and request reviewer.
