# Step N — Short Title

## Purpose
One-sentence statement of intent. (Required)

## Deliverables
- Bullet list of tangible outputs (files, endpoints, UI elements, assets).

## Primary files to change (required)
- List exact workspace-relative file links for reviewers. e.g. [code/frontend/app.js](code/frontend/app.js)

## Detailed implementation steps
1. Numbered developer tasks. Include exact function/handler names, DOM locations, and small code snippets if helpful.
2. Example: Update `renderReports()` in [code/frontend/app.js](code/frontend/app.js) to call `renderTaskDropdown()`.

## Integration & Edge Cases
- Notes on compatibility, migrations, and behavior with existing features.
- If this touches persistence, include a mandatory backup/atomic-write note.

## Acceptance Criteria (required)
- Numbered, testable statements. Prefer automated assertions (HTTP path, status code, JSON shape) and a short manual verification step.
- Example: "`GET /stats/pulse` returns 200 with `{lastWrite: <iso>}`"

## Testing / QA (required)
- Tests to add (file paths under `code/backend/tests/`), minimal assertions, and `pytest` commands.
- Manual QA checklist with numbered steps and expected visible behavior.

## Files touched (repeat for reviewers)
- Repeat workspace-relative links to files changed in this step.

## Estimated effort
- e.g. 1-2 dev days

## Concurrency & PR strategy
- Suggested branch names, merge order, and any dependent steps. Link other step files by path.

- **Required fields (add below):**

	- `Blocking steps:`  
		- List workspace-relative paths or branch names that must be merged first. Example: `Blocked until: .github/artifacts/phase1/plan/type-sync.md`

	- `Merge Readiness: true|false`  
		- Authors must set this to `false` while blockers remain, and flip to `true` when the step is safe to merge.

	- `Stub/FeatureFlag:` (optional)  
		- If a step uses a stubbed implementation because a dependency hasn't merged, describe the feature flag, the stub behavior, and link tests that assert safe fallback.

## Risks & Mitigations
- Short list of risks. If data/storage is modified: "BEFORE MERGE: call `backup_snapshot()` and follow atomic-write pattern in `code/backend/app/storage.py`."

## References
- Links to related artifacts, schemas, and docs (workspace-relative links).

## Appendix (optional)
- Minimal request/response examples, short code snippets, or screenshot mockups.

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected

## Dos & Don'ts (short)
- Do: Be specific — exact file paths, function names, and test locations.
- Do: Use imperative, checklist-oriented language.
- Don’t: Leave vague scope or skip error/validation acceptance criteria.
