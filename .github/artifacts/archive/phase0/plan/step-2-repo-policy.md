# Step 2 — Repo Policy & Templates

## Purpose
Create repository governance and maintainer command templates to make contribution flow repeatable for Phase‑0.

## Deliverables
- `BRANCHING.md` at repo root
- `project/.github/copilot-commands.yaml`

## Owner & Due
- owner: TBD
- due: 2026-02-22

## Verification commands
- Check `BRANCHING.md`: `cat BRANCHING.md`
- Validate copilot commands file: `yq eval . .github/copilot-commands.yaml` (or open file manually)
- Ensure PR template links to step file and acceptance checklist.

## CI/Secrets checklist
- Ensure any deploy keys or secrets are stored in GitHub Secrets; do not store credentials in code.

## Primary files to change
- `BRANCHING.md`
- `project/.github/copilot-commands.yaml`

## Detailed implementation steps
1. Draft `BRANCHING.md` at repo root with branch naming, PR process, `main` protection recommendations, and examples.
2. Create `project/.github/copilot-commands.yaml` with templates: `scaffold`, `run-tests`, `run-smoke`, `generate-docs` and sample outputs.
3. Commit on branch `phase0/step-2-repo-policy` and open PR referencing Step 1 ADRs where relevant.

## Integration & Edge Cases
- Reference ADRs from Step 1 for auth and CI guidance.

## Acceptance Criteria
1. `BRANCHING.md` exists at repo root and documents naming and PR requirements.
2. `project/.github/copilot-commands.yaml` exists and contains the listed templates.
3. PR opened and at least one reviewer assigned.

## Testing / QA
- Manual review of YAML examples; CI smoke should validate schema in Step 3.

## Files touched
- `BRANCHING.md`
- `project/.github/copilot-commands.yaml`

## Estimated effort
1–2 hours

## Concurrency & PR strategy
- Can be worked in parallel with Step 4. Branch: `phase0/step-2-repo-policy`.

## Risks & Mitigations
- Risk: policy contradicts ADRs. Mitigation: link Step 1 ADRs in PR description.

## Author Checklist
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] PR branch created
