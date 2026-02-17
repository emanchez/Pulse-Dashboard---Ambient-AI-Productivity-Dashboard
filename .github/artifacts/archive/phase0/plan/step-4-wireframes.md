# Step 4 — Wireframes & Frontend Assets

## Purpose
Produce three Phase‑0 wireframe PNGs and commit them so visual intent is captured for Phase‑1.

## Deliverables
- `frontend/assets/phase0/pulse.png`
- `frontend/assets/phase0/tasks.png`
- `frontend/assets/phase0/synthesis.png`

## Owner & Due
- owner: TBD
- due: 2026-02-20

## Verification commands
- List assets: `ls -lh frontend/assets/phase0/`
- Check file sizes and previews in PR.

## Binary asset guidance
- Keep placeholder PNGs under 1MB each; consider Git LFS only if designers provide large files later.

## Primary files to change
- `frontend/assets/phase0/` (new directory)

## Detailed implementation steps
1. Create directory `frontend/assets/phase0/`.
2. Generate three 1200x800 PNG placeholders (SVG→PNG or Pillow) with labeled regions and footer `placeholder — replace in Phase‑1`.
3. Commit on `phase0/step-4-wireframes` and open PR.

## Integration & Edge Cases
- If no designer assets are available, placeholders are acceptable; include instructions for replacing with Figma exports.

## Acceptance Criteria
1. All three PNGs exist under `frontend/assets/phase0/` and have non-zero file size.
2. PR shows image previews.

## Testing / QA
- Verify images render locally and check commit previews in PR.

## Files touched
- `frontend/assets/phase0/pulse.png`
- `frontend/assets/phase0/tasks.png`
- `frontend/assets/phase0/synthesis.png`

## Estimated effort
0.5–1.5 hours

## Concurrency & PR strategy
- Can be produced in parallel with Steps 1–3. Branch: `phase0/step-4-wireframes`.

## Risks & Mitigations
- Risk: large binary files. Mitigation: keep placeholders optimized and small.

## Author Checklist
- [ ] Purpose filled
- [ ] Deliverables listed
