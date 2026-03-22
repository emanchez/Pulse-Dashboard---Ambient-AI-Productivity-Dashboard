# Project Summary — Ambient AI Productivity Dashboard

Date: 2026-02-22

## Elevator pitch
This is a local-first Ambient AI Productivity Dashboard that passively logs user activity and uses OZ (Warp's cloud agent platform) to generate high‑level syntheses and co‑planning suggestions. It targets a single-user MVP but is architected to use `user_id` for future multi-user support.

## Working directory
Primary code: `/code` (backend + frontend). Key paths:
- Backend: `code/backend`
- Frontend: `code/frontend`
- Project docs & planning: `.github/artifacts`

## Tech stack
- Frontend: Next.js (App Router), TypeScript, Tailwind CSS, Lucide React icons
- Backend: FastAPI (Python 3.10+), Pydantic v2, Async SQLAlchemy
- Database: SQLite for dev (Postgres intended for prod)
- LLM / inference: OZ (Warp cloud agent platform; no local model required)
- Type sync: `@hey-api/openapi-ts` (generator pinned; a generated stub is committed)
- Auth: JWT (all endpoints except `/login` and `/health` require a token)

## High-level repo layout
- `code/backend` — FastAPI app
  - `app/main.py` — app startup / router wiring
  - `app/api/*` — route modules (auth, tasks, stats)
  - `app/core/*` — config, security, CORS
  - `app/db/*` — SQLAlchemy base & session
  - `app/models/*` — ORM models (`Task`, `ActionLog`, `ManualReport`, `SystemState`, `User`)
  - `app/schemas/*` — Pydantic schemas (camelCase JSON aliases)
  - `app/middlewares/action_log.py` — event-sourcing middleware writing `ActionLog` entries
  - `scripts/create_dev_user.py` — create a local dev user
  - `tests/` — pytest suites (unit + e2e smoke)

- `code/frontend` — Next.js app
  - `app/` — pages (login, dashboard)
  - `components/` — `BentoGrid`, `PulseCard`, `TaskBoard`
  - `lib/generated/` — committed typed client stubs
  - `lib/api.ts` — lightweight fetch helpers + re-exports

- `.github/artifacts` — planning artifacts, PDD, ADRs, step & phase docs (authoritative project guidance)

## What we have implemented (status snapshot)
- Backend
  - JWT auth (`/login`, `/me`) and user model
  - Task CRUD endpoints with ActionLog middleware (every save emits an event)
  - `GET /stats/pulse` (pulse telemetry: `silenceState`, `lastActionAt`, `gapMinutes`, `pausedUntil`) with tests
  - Pydantic camelCase alias generator for FE JSON compatibility
  - Unit & e2e smoke tests covering auth, task create, and ActionLog

- Frontend
  - Next.js App Router scaffold, `login` page, `BentoGrid`, `PulseCard`, `TaskBoard`
  - Mobile-first styling (Tailwind) and UX bugfixes (merge diff before PUT, save-state handling)
  - Minimal generated client stub committed to `lib/generated` to avoid blocking FE work

- Type sync & CI
  - `generate-client.sh` helper and CI step to run the generator; generator pinned as a devDependency
  - CI workflow updated to run generation, tests, and frontend build

## How this maps to the PDD roadmap
- Phase 1 (Skeleton & Agentic Prototyping): Completed — backend skeleton, auth, models, initial frontend scaffold, and type-sync tooling present.
- Phase 2 (Ambient Sensing & Dashboard Experience): In progress — pulse API, event logging, and task save flow complete and tested; remaining items are UI polish, component tests, and finalizing generated TypeScript client integration.
- Later phases (Manual Reports, SystemState orchestration, OZ-driven Sunday Synthesis): Partially scaffolded (models present), but full OZ orchestration and synthesis agents remain to be implemented and validated.

## Key decisions & constraints (ADRs)
- OZ-only inference posture: all AI inference runs through OZ (Warp cloud agent platform). No local models or external LLM APIs.
- Auth-first: all endpoints except `/login` and `/health` require JWT and must use `user_id` for scoping.
- Event sourcing: every Task save must write an `ActionLog` entry (implemented).
- Strict typing enforced: Python type hints and TypeScript strict mode.

## Demonstration script (quick live demo)
1. (Optional) Create dev user:
   ```bash
   PYTHONPATH=$(pwd)/code/backend .venv/bin/python code/backend/scripts/create_dev_user.py
   ```
2. Start both services (dev):
   ```bash
   make dev
   ```
   - Backend: http://localhost:8000
   - Frontend: http://localhost:3000
3. In browser: visit `/login`, sign in with `devuser` (or token), open dashboard — PulseCard and TaskBoard should render.
4. Create or edit a task, save, then verify network calls (`PUT /tasks/{id}`) and that `ActionLog` entries appear in the backend.
5. Run backend tests:
   ```bash
   PYTHONPATH=$(pwd)/code/backend .venv/bin/pytest -q
   ```

## Open issues & risks
- OZ integration: orchestration for synthesis is wired via `OZClient`; requires OZ API key and agent configuration (see `.agents/skills/dashboard-assistant/SKILL.md`).
- Generated TypeScript client: a stub is committed; decide whether to commit full generator output or require CI to enforce regeneration.
- Migration & backups: schema changes (e.g., adding `user_id`) require pre-merge backup guidance and migration runbooks before prod migration.

## Next recommended steps
1. Decide on generated client policy: commit generator output vs CI-only generation and enforce diffs in PRs.
2. Add component tests (PulseCard, TaskBoard) and an E2E Playwright smoke test in CI.
3. Complete OZ agent deployment (configure environment, register skill, validate end-to-end synthesis pipeline).
4. Polish UI error/retry UX and add automated tests for the previously fixed 422 and auth edge cases.

## Closing summary
We have a working local-first backend and frontend scaffold with JWT auth, event-sourced task logging, pulse telemetry, and type-sync tooling in place. The immediate priorities are finalizing the generated TypeScript client, adding component tests, and completing the OZ agent deployment for the advanced synthesis features.

---
_Generated summary by project automation — ready for copy into slides or speaker notes._
