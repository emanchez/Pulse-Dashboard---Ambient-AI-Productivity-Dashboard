# Planning Guide (Generic)

Purpose
-------
This document is a reusable, project-agnostic planning guide for organizing phase/version/feature work. It defines canonical conventions for phase- and step-level planning documents, mandates directory organization for artifacts, and supplies an author checklist, verification/runbook, and governance rules to ensure consistent, reviewable plans.

Directory convention
--------------------
- Create a dedicated directory for each phase, version, or feature under a centralized `artifacts/` area (example: `artifacts/<phase-name>/`).
- Each phase directory SHOULD contain a single phase-level master file and one or more step files. Authors may add related artifacts (diagrams, test matrices, migration scripts) into the same directory.

Templates and authority
-----------------------
- The project-level master and step templates (the canonical templates) are normative: authors must copy and populate those templates when creating phase masters and step documents.
- Required sections in the templates are mandatory; do not remove them. Authors may add optional appendices for diagrams or large data migration plans.

Required sections (master & step documents)
-----------------------------------------
Every phase master and every step document MUST include the following sections (or explicitly note why any required section is omitted):
- Purpose
- Deliverables (explicit, tangible outputs)
- Primary files to change (workspace-relative links or clear placeholders)
- Detailed implementation steps
- Integration & edge cases
- Acceptance criteria (numbered, measurable, testable)
- Testing / QA (tests to add/modify and a manual QA checklist)
- Backup & migration notes (required when persistence/data is affected)
- Files touched
- Estimated effort
- Concurrency & PR strategy (merge order, blocking deps)
- Risks & mitigations
- References
- Author checklist (completed before PR)

Acceptance criteria rules
-------------------------
- Criteria must be measurable and testable. Prefer automated assertions (example: an API path + expected status + JSON shape) and include at least one concise manual verification step.
- Number and label each acceptance criterion for traceability.

Testing matrix
--------------
- Each step must map to specific tests to add or update. Provide exact test file paths and commands where applicable, or indicate the test runner and example command (placeholder). Include at least one happy-path test and one validation/negative test for any endpoint or data change.

Backup & migration policy
-------------------------
- Any change that modifies persistence, data formats, or performs destructive operations MUST include:
  - A documented pre-merge backup step (how to take a backup).
  - The migration or transformation steps to be executed.
  - Restore and rollback instructions.
  - A note that atomic-write patterns must be followed when writing data.

Concurrency & PR strategy
-------------------------
- Phase masters MUST list concurrency groups and a suggested merge order for dependent steps.
- Recommend focused PRs: separate schema/persistence changes into their own PRs with explicit backup/migration steps.
- Suggested branch naming convention: `phase-<n>/step-<m>-short-desc` (adjust to project conventions).

### Merge Order and Blocking Rules (Required)

- Numeric `Steps (ordered)` MUST reflect the intended merge sequence. If the intended merge sequence differs from numeric ordering, the phase master MUST include a `Merge Order` subsection immediately after `Steps (ordered)` that lists the exact merge sequence (by step filename and suggested branch name).
- Each phase master and step document MUST include the following fields in their `Concurrency & PR strategy` section:
  - `Blocking steps:` (workspace-relative paths of step files or branch names that must be merged first)
  - `Merge Readiness: true|false`
- If merging a step prior to its blockers would break CI or the build, the step MUST either be blocked until blockers are merged or include a feature-flagged stub implementation with automated tests that assert safe fallback behavior. Acceptance criteria must verify the safe fallback.

Author checklist (to complete before opening PR)
-----------------------------------------------
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] Primary files to change referenced (workspace-relative links or placeholders)
- [ ] Detailed implementation steps enumerated
- [ ] Acceptance criteria numbered and testable
- [ ] Tests listed (happy-path + validation)
- [ ] Manual QA checklist provided
- [ ] Backup/Migration notes present if persistence affected
- [ ] Estimated effort provided
- [ ] Concurrency & PR notes provided
- [ ] Author signoff

Verification & runbook (generic)
-------------------------------
Provide a short runbook that reviewers and CI can follow before merging. Example placeholders to adapt per project:

Run tests

```bash
pytest -q
```

Start local runtime & smoke tests

```bash
# Start the application in development mode (project-specific)
# Then run basic smoke checks (placeholders)
curl -sS "http://localhost:<port>/health" | jq .
curl -sS "http://localhost:<port>/<important-endpoint>?limit=1&offset=0" | jq .
```

Backup validation

- Execute the documented backup procedure and verify a timestamped backup artifact exists in the designated backup location.

Governance & review guidance
---------------------------
- Phase master documents should declare which steps can be worked on in parallel and which steps block others.
- Require CI to pass for all modified tests before merging any PR referenced by a step.
- Ensure at least one reviewer with domain knowledge signs off on changes that affect that layer (e.g., data, API, UI).

Usage notes
-----------
- Keep planning documents focused on the WHAT and the HOW at a high level — avoid detailed implementation code in the plan itself.
- Use exact file paths, function names, and test file paths in step documents to make reviews efficient.
- When a step requires large scripts (migration, import/export), store those scripts inside the same phase directory and reference them from the step doc.

FAQ / common examples
---------------------
- Q: Where do I put diagrams or test fixtures?  
  A: Place them inside the phase directory alongside the master and step files.
- Q: What if a step doesn't touch persistent data?  
  A: Still include a short 'Backup & migration notes' section stating that no persistence is affected.

Contact & stewardship
---------------------
- Assign a phase owner in the phase master who is responsible for keeping step docs updated and coordinating merges.

Appendix: minimal acceptance criterion example
--------------------------------------------
1. GET /items returns 200 with a JSON object containing `items` (array) and `total` (integer).  
   Manual verify: request the endpoint locally and inspect the JSON shape.
