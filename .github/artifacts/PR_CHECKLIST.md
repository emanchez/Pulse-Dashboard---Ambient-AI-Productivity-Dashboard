# PR Review Checklist (Planning & Step merges)

Use this checklist when reviewing PRs that implement phase masters or step files.

- Confirm `Merge Readiness: true` present in the related step file(s), or confirm an explicit `Blocking steps:` list and that blockers are merged.
- Confirm PR description contains `Depends-On:` entries for any blockers (branch names) referenced in the step file.
- If a dependency artifact is missing (e.g., generated client), confirm the PR includes a feature-flagged stub and tests proving safe fallback.
- Confirm branch name follows `phase-<n>/step-<m>-short-desc`.
- Confirm acceptance criteria include at least one automated check that would fail if the dependency is missing (or confirm CI will gate the PR).
- If the PR updates templates or planning docs, ensure existing open plans are annotated or migrated to the new fields.
