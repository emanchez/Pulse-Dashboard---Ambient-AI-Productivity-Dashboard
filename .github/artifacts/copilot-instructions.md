# Project Context

Ambient AI Productivity Dashboard

You are an expert Full-Stack Developer assisting in the creation of a "Local-First" Productivity Dashboard. This project is a personal tool designed to combat procrastination through "Ambient" data logging and AI-driven synthesis.

## Core Tech Stack

**Frontend:** Next.js 14+ (App Router), TypeScript, Tailwind CSS, Lucide React (Icons).

**Backend:** FastAPI (Python 3.10+), Pydantic v2.

**Database:** SQLAlchemy (Async), SQLite (Dev) / PostgreSQL (Prod).

**AI/LLM:** LLM provider (Anthropic Claude or Groq) via `LLMClient` abstraction (`app/services/llm_client.py`). Provider switchable via `LLM_PROVIDER` env var.

> **Note (Phase 4.1.2):** This project previously planned to use OZ (Warp cloud agent platform) as its inference backend but did not receive beta access. All AI inference now runs directly through `LLMClient` (`anthropic` or `groq` SDK), configurable via `LLM_PROVIDER`.

**Type Sync:** openapi-ts for generating TypeScript clients from FastAPI openapi.json.

## Coding Standards & Patterns

- **Strict Typing:** All Python code must use Type Hints (def func(a: int) -> str:). All TypeScript must be strict.
- **CamelCase JSON:** The Python backend must serialize Pydantic models to camelCase JSON for the frontend, but keep snake_case for Python internal logic and Database columns.
- **Event Sourcing Lite:** We do not just update tasks; we log actions. Every "Save" operation on a task triggers a write to the ActionLog table.
- **Mobile-First UI:** The design uses a "Bento Box" grid system. Ensure responsive classes (md:col-span-2) are used for all layout components.

## Critical Rules (Do Not Break)

- **LLM Inference via LLMClient:** All AI inference runs through the `LLMClient` abstraction (`app/services/llm_client.py`). Supported providers: `anthropic` (Claude) and `groq` (Llama). Switch via `LLM_PROVIDER` env var. Do not bypass `LLMClient` or call provider SDKs directly from routes or services.
- **Auth First:** All API endpoints (except /login and /health) must be guarded by JWT Authentication.
- **Single User Assumption:** The app is currently single-user, but code should rely on `user_id` from the JWT token to ensure future scalability. Every DB query that touches user-owned data MUST include a `WHERE user_id = <jwt_sub>` filter. Never return unscoped rows.
- **user_id is sacred:** `user_id` is the primary key link for all application data. Never delete and re-create a user record. Never change a user's `id`. Any operation that would orphan rows (detach them from their owner user) is forbidden. Use upsert patterns for all seeding and user-management scripts.
- **Migrations over `create_all`:** `Base.metadata.create_all` must never be used as a migration tool in any environment that stores real data. It only creates missing tables — it does not add columns, add constraints, or fix data. Any schema change to an existing table requires an explicit Alembic migration. See architecture.md §5.
- **Seeding scripts must be idempotent:** All scripts in `code/backend/scripts/` must be safe to re-run without side effects. If a record already exists, update it in place — never delete and re-insert. Auto-generated PKs (UUIDs) must never be regenerated for existing records.
- **No unscoped data access in AI prompts:** AI inference context (prompts sent to the LLM) must only include data belonging to the authenticated user. Cross-user data must never appear in an inference payload, even inadvertently. See agents.md §4.

## Project Directory Structure

All project code is located in the `/code` directory:

```
/code
  /backend
    /app
      /api        # Routes
      /core       # Config, Security, Auth
      /db         # Models, Session
      /services   # AI Logic, Log Parsers
  /frontend
    /app          # Next.js Pages
    /components   # UI Components (BentoGrid, TaskCard)
    /lib          # API Client (generated), Utils
```

## Reference Documents for Coding Agents

To ensure organized and consistent implementation, coding agents must reference the following context files located in `/project/.github/artifacts`:

- **[PLANNING.md](PLANNING.md):** Authoritative project planning methodology. Defines canonical conventions for phase/step planning, directory organization, required document sections, acceptance criteria rules, testing matrices, backup & migration policy, concurrency & PR strategy, and verification runbooks.
- **[master-template.md](master-template.md):** Canonical master plan template for phases/versions. Required sections: Scope, Phase-level Deliverables, Steps (ordered), Phase Acceptance Criteria, Concurrency groups & PR strategy, Verification Plan, Risks/Rollbacks, References, Author Checklist.
- **[step-template.md](step-template.md):** Canonical step document template for individual development tasks. Required sections: Purpose, Deliverables, Primary files to change, Detailed implementation steps, Integration & Edge Cases, Acceptance Criteria, Testing/QA, Files touched, Estimated effort, Concurrency & PR strategy, Risks & Mitigations, References, Author Checklist.
- **[PDD.md](PDD.md):** Comprehensive Product Design Document with strategic vision, user stories, technical architecture, data models, agentic reasoning, UI/UX strategy, and MVP roadmap. Use this for feature requirements, ADRs, and overall product direction.
- **[product.md](product.md):** Condensed version of product details, including vision, personas, core features, UI specs, and roadmap. Reference for quick overviews.
- **[architecture.md](architecture.md):** Detailed technical architecture, including data schemas, API design, synchronization, and security ADRs. Essential for backend and frontend integration details.
- **[agents.md](agents.md):** Agentic reasoning prompts and logic for AI inference, including silence gap analysis, report density, and prompt engineering for Sunday Synthesis, Task Suggester, and Co-Planning.

**Archive Folder Policy:** Items stored in the `archive/` folder are deprecated or superseded. Do not reference archived documents in active planning, code decisions, or implementation unless explicitly directed.

## Planning Methodology

All feature/version/phase work must follow the master/step planning framework defined in [PLANNING.md](PLANNING.md):

1. **Create a phase master** using [master-template.md](master-template.md) located at `artifacts/<phase-name>/master.md`. The master declares scope, deliverables, ordered steps, phase-level acceptance criteria, concurrency groups, PR merge order, and verification plan.
2. **Create step documents** using [step-template.md](step-template.md) located at `artifacts/<phase-name>/step-<n>-short-title.md`. Each step is a focused development task with purpose, deliverables, primary files, acceptance criteria, testing requirements, estimated effort, and risks.
3. **Mandatory sections:** Every master and step document MUST include: Purpose, Deliverables, Primary files to change, Acceptance Criteria (numbered, testable), Testing/QA (tests + manual checklist), Estimated effort, Concurrency & PR strategy, Risks & Mitigations, and Author Checklist.
4. **Concurrency & merge strategy:** Phase masters MUST declare which steps can be parallelized and the required merge order for dependent steps. Use branch naming: `phase-<n>/step-<m>-short-desc`.
5. **Acceptance criteria rules:** All criteria must be measurable and testable. Prefer automated assertions (API paths, HTTP status codes, JSON shapes) and include at least one manual verification step.
6. **Backup & migration:** Any change affecting persistence MUST include pre-merge backup steps, transformation instructions, and rollback procedures. Use atomic-write patterns.
7. **Verification runbook:** After drafting a plan, ensure reviewers have a clear smoke-test and deployment checklist (see [PLANNING.md](PLANNING.md#verification--runbook-generic) for template).

## Guidelines for Coding Agents

- **Before Implementation:** Review relevant sections in PDD.md and architecture.md to understand requirements and constraints.
- **AI Integration:** When implementing AI features, refer to agents.md for prompt structures and inference logic.
- **Planning:** When tasked with planning features/phases, follow the master/step framework. Reference PLANNING.md for governance and concurrency rules.
- **Validation:** After changes, run builds/tests/linters and verify against the acceptance criteria and testing checklists in your step or master document.
- **Consistency:** Maintain strict typing, event sourcing, and mobile-first design as per coding standards.
- **Documentation:** Update or reference these context files if new decisions or changes arise, keeping everything intertwined and up-to-date.

## Dependency & Merge Enforcement (New)

- **Blocking steps required:** Every step document MUST include a `Blocking steps:` line in the `Concurrency & PR strategy` section when it depends on other step artifacts. Use workspace-relative paths or branch names (example: `Blocked until: .github/artifacts/phase1/plan/type-sync.md`).
- **Merge Readiness flag:** Every step document MUST include `Merge Readiness: true|false`. PRs that implement a step must only be merged when the corresponding step file shows `Merge Readiness: true`, or when an approved stub/feature-flag pattern is present (see next bullet).
- **Generated artifacts & stubs:** If a step depends on generated artifacts (for example a TypeScript client), the author must either:
  - mark the step as blocked until the generating step merges, or
  - include a clearly documented, feature-flagged stub implementation plus automated tests that assert safe fallback behavior and add `Depends-On: <branch>` metadata to the PR.
- **Branch and PR metadata:** Branches must follow `phase-<n>/step-<m>-short-desc`. If a PR depends on an unmerged step, include `Depends-On: <branch>` in the PR description and add a `depends` label. Reviewers must verify that `Depends-On` blockers are resolved before merging.

## Hard-Won Lessons (Do Not Repeat)

### `.env` paths must be relative to the service's working directory
All paths in `code/backend/.env` must be relative to `code/backend/` — the directory uvicorn runs from. Never write project-root-relative paths (e.g. `./code/backend/data/dev.db`) in a subdirectory `.env` file. When the file was previously ignored (`env_file = None`) the wrong path was harmless; enabling `.env` loading activated it and broke startup with a silent `OperationalError`.

### Enabling a previously disabled config mechanism requires auditing every value it loads
Switching from `env_file = None` to `env_file = ".env"` is a behaviour change that activates **all** keys in the file. Before enabling, review every value for path correctness, origin count, and side effects. Do not assume existing values are safe just because they were inert before.

### `pydantic-settings` v2 JSON-parses `List[str]` fields before validators run
Declaring `frontend_cors_origins: List[str]` causes pydantic-settings to attempt JSON parsing of the raw env var string. A comma-separated value like `http://localhost:3000,http://127.0.0.1:3000` is not valid JSON, causing a `SettingsError` at startup. Always declare such fields as `str` and split them in a method or property (e.g. `get_cors_origins()`) rather than relying on a `@field_validator` with `mode="before"`.

### `create_all` does not migrate existing tables — missing columns cause unhandled 500s that strip CORS headers
When a SQLAlchemy model gains new columns, `metadata.create_all` only creates the table if it does not exist; it does not add columns to an existing table. If the live `dev.db` predates the model change, every query that references the new column raises `OperationalError: no such column`, which — if unhandled — propagates as a raw 500 response before CORSMiddleware can attach the `Access-Control-Allow-Origin` header, making the bug appear as a CORS error in the browser. Always run an explicit `ALTER TABLE ... ADD COLUMN` migration script (or use Alembic) when adding columns to an ORM model, and verify the live schema matches the model with `PRAGMA table_info(<table>)` before deploying.

### Status code `(null)` in a browser CORS error means "connection refused" not a header problem
When the browser reports `CORS request did not succeed` with `Status code: (null)`, the backend process is not responding at all — it has crashed or never started. Do not spend time debugging CORS headers; check that the server process is alive first (`curl /health`).

### Silent `nohup` startup hides crashes
The `make start` target uses `>/dev/null 2>&1`, so any crash at startup is swallowed. Always verify the process is alive and `/health` returns 200 after starting via `make dev` or `make start`. A startup smoke check (curl with retry) should be added to the `start` target to surface failures immediately.

### Seeding scripts that delete + re-create users orphan all related data
`scripts/create_dev_user.py` previously deleted and re-inserted devuser on every run, generating a new UUID each time. All tasks, reports, action logs, and system states retained the old `user_id` and became invisible to the API (which scopes every query by `user_id`). The data was intact in the DB but unreachable. Fix: always upsert — if the user exists, update only mutable fields (e.g. password) and preserve the `id`. This applies to all seeding scripts for any entity with auto-generated PKs.

### JWT claim additions are a breaking change for stored tokens
Adding `iss`/`aud` claims to `create_access_token` (or any other new required claim) immediately invalidates all tokens minted before the change. Clients holding a stored token in `localStorage` or cookies will receive 401 on every request with no redirect, since the frontend has no mechanism to detect the claim mismatch. Whenever JWT structure changes: (1) bump a token `version` claim or key ID (`kid`), (2) implement server-side token validation on the frontend at mount (call `/me` and clear the stored token on 401), and (3) document the change as a breaking auth event in the phase summary.

### `user_id` filters must be explicit — never rely on joined ownership
All API endpoints that return user-owned data must include an explicit `WHERE user_id = <sub>` clause in the SQLAlchemy query. Never infer ownership through a join (e.g. "tasks linked to reports owned by this user") — always filter the root table directly. Missed filters expose other users' data in multi-tenant deployments and cause silent empty results in single-user dev when the user ID changes.

