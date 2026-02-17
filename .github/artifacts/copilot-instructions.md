# Project Context

Ambient AI Productivity Dashboard

You are an expert Full-Stack Developer assisting in the creation of a "Local-First" Productivity Dashboard. This project is a personal tool designed to combat procrastination through "Ambient" data logging and AI-driven synthesis.

## Core Tech Stack

**Frontend:** Next.js 14+ (App Router), TypeScript, Tailwind CSS, Lucide React (Icons).

**Backend:** FastAPI (Python 3.10+), Pydantic v2.

**Database:** SQLAlchemy (Async), SQLite (Dev) / PostgreSQL (Prod).

**AI/LLM:** Ollama (Local inference), running Llama 3 or Mistral.

**Type Sync:** openapi-ts for generating TypeScript clients from FastAPI openapi.json.

## Coding Standards & Patterns

- **Strict Typing:** All Python code must use Type Hints (def func(a: int) -> str:). All TypeScript must be strict.
- **CamelCase JSON:** The Python backend must serialize Pydantic models to camelCase JSON for the frontend, but keep snake_case for Python internal logic and Database columns.
- **Event Sourcing Lite:** We do not just update tasks; we log actions. Every "Save" operation on a task triggers a write to the ActionLog table.
- **Mobile-First UI:** The design uses a "Bento Box" grid system. Ensure responsive classes (md:col-span-2) are used for all layout components.

## Critical Rules (Do Not Break)

- **No External AI APIs:** Do not suggest OpenAI or Anthropic SDKs. All inference is local via ollama.
- **Auth First:** All API endpoints (except /login and /health) must be guarded by JWT Authentication.
- **Single User Assumption:** The app is currently single-user, but code should rely on user_id from the JWT token to ensure future scalability.

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
