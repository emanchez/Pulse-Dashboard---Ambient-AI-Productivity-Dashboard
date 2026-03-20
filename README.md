# Pulse Dashboard — Ambient AI Productivity Dashboard

A **local-first** personal productivity dashboard that combats procrastination through ambient data logging and AI-driven synthesis. Instead of demanding active self-reporting, the system passively observes your work patterns—task edits, silence gaps, focus sessions—and uses AI to generate weekly narratives, detect stagnation, and suggest next steps.

![Status](https://img.shields.io/badge/status-MVP%20complete-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Node](https://img.shields.io/badge/node-20.x-green)
![License](https://img.shields.io/badge/license-private-lightgrey)

---

## Core Idea

Most productivity tools demand **active data entry**, which creates friction and irony—you procrastinate on logging your procrastination. Pulse Dashboard flips this: every task edit, report submission, and session start/stop is automatically logged as an **ActionLog** event. The AI engine then analyzes these events to produce:

- **Silence Gap Analysis** — flags periods of 48+ hours without activity (unless you're on vacation).
- **Sunday Synthesis** — a weekly AI-generated narrative summarizing your theme, commitment score, and blind spots.
- **Task Suggestions** — AI-proposed next steps based on what's stale and what's moving.
- **Co-Planning** — when a report contains conflicting goals, the AI surfaces a clarifying question.

## Features (MVP)

| Feature | Description |
|---------|-------------|
| **JWT Authentication** | Login/logout with secure token handling. Single-user today; multi-user ready. |
| **Task CRUD + Event Sourcing** | Every task mutation writes an immutable ActionLog entry for analyzability. |
| **Focus Sessions** | Start/stop timed work sessions linked to tasks. |
| **Manual Reports** | Narrative "brain dump" entries with optional task linking for AI context. |
| **System States** | Vacation / leave mode that overrides stagnation detection. |
| **Silence Indicator** | Real-time pulse badge showing engaged / stagnant / paused state. |
| **Flow State Metrics** | Derived productivity metrics (actions, streaks, session time). |
| **Sunday Synthesis** | AI-generated weekly narrative with commitment scoring. |
| **Task Suggestions** | AI-proposed next actions based on open tasks and stuck points. |
| **Co-Planning** | AI-driven ambiguity detection in strategic reports. |
| **Ghost List** | Detects tasks showing signs of wheel-spinning or neglect. |
| **Bento Grid Dashboard** | Mobile-first layout with focus header, pulse card, sessions, tasks, and AI reasoning sidebar. |

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS | Bento-grid dashboard with progressive disclosure |
| **Backend** | FastAPI, Python 3.10+, Pydantic v2 | Async REST API with event-sourcing middleware |
| **Database** | SQLAlchemy (Async), SQLite (dev) / PostgreSQL (prod) | Local-first storage with migration-ready schema |
| **AI Inference** | OZ (OpenRouter) running Claude Haiku | Privacy-conscious AI synthesis and suggestions |
| **Type Sync** | @hey-api/openapi-ts | Auto-generated TypeScript client from FastAPI's OpenAPI spec |
| **Icons** | Lucide React | Consistent iconography across the UI |

## Project Structure

```
project/
├── Makefile                     # Orchestrates backend + frontend targets
├── code/
│   ├── backend/                 # FastAPI service (Python)
│   │   ├── app/
│   │   │   ├── api/             # Route handlers (auth, tasks, reports, ai, etc.)
│   │   │   ├── core/            # Config, security, rate limiting
│   │   │   ├── db/              # SQLAlchemy engine + session
│   │   │   ├── middlewares/     # ActionLog event-sourcing middleware
│   │   │   ├── models/          # ORM models (task, user, action_log, etc.)
│   │   │   ├── schemas/         # Pydantic request/response schemas
│   │   │   └── services/        # AI service, synthesis, ghost list, etc.
│   │   ├── scripts/             # Dev user seeding, migrations, OZ setup
│   │   ├── tests/               # pytest suite (136 passing)
│   │   └── data/                # SQLite dev DB + backups
│   └── frontend/                # Next.js app (TypeScript)
│       ├── app/                 # Pages (login, tasks, reports, synthesis)
│       ├── components/          # UI components (BentoGrid, nav, cards, forms)
│       └── lib/                 # API client, generated types, auth hook
└── .github/artifacts/           # Planning docs, architecture, PDD
```

## Quick Start

### Prerequisites

- **Python 3.10+** with `pip`
- **Node.js 20.x** with `npm`
- **OZ API key** (optional — AI features are disabled without it)

### 1. Clone and install dependencies

```bash
git clone <repo-url> && cd project
make deps
```

This runs `pip install -r requirements.txt` in the backend venv and `npm ci` in the frontend.

### 2. Set up the dev user

```bash
cd code/backend
python scripts/create_dev_user.py
```

Creates a default dev user (idempotent — safe to re-run).

### 3. (Optional) Configure AI

```bash
cd code/backend
python scripts/setup_oz.py
```

Follow the prompts to set your `OZ_API_KEY` in `.env`. Without this, AI endpoints return 503 but the rest of the app works normally.

### 4. Start both services

```bash
# From the project root:
make dev
```

| Service  | URL |
|----------|-----|
| Backend  | http://localhost:8000 |
| Frontend | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Health   | http://localhost:8000/health |

### 5. Stop services

```bash
make stop
```

## Makefile Reference

Run from the project root:

| Command | Description |
|---------|-------------|
| `make dev` | Start backend + frontend in background |
| `make stop` | Stop both services |
| `make restart` | Stop, wait for ports, restart |
| `make deps` | Install all dependencies |
| `make test` | Run backend pytest suite |
| `make generate-api` | Regenerate TypeScript client from OpenAPI spec |
| `make build` | Production build (frontend) |
| `make lint` | Run linters (placeholder) |
| `make fmt` | Run formatters (placeholder) |

## API Overview

**28 endpoints** (2 public, 26 authenticated). Full interactive docs at `/docs` when the backend is running.

| Group | Endpoints | Description |
|-------|-----------|-------------|
| Auth | `POST /login`, `GET /me` | JWT authentication |
| Tasks | `GET/POST /tasks`, `PUT/DELETE /tasks/{id}` | Task CRUD with event sourcing |
| Reports | `GET/POST /reports`, `PUT/DELETE /reports/{id}`, `PATCH /reports/{id}/archive` | Manual reports with archiving |
| Sessions | `POST /sessions/start`, `POST /sessions/stop`, `GET /sessions/active` | Focus session tracking |
| Stats | `GET /stats/pulse`, `GET /stats/flow-state`, `GET /stats/ghost-list`, `GET /stats/weekly-summary` | Productivity analytics |
| System States | `GET/POST /system-states`, `GET /system-states/active`, `PUT/DELETE /system-states/{id}` | Vacation/leave management |
| AI | `POST /ai/synthesis`, `POST /ai/suggest-tasks`, `POST /ai/co-plan`, `POST /ai/accept-tasks`, `GET /ai/usage` | AI-powered insights |
| Infra | `GET /health` | Health check |

## Environment Variables

Backend configuration via `code/backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/dev.db` | Database connection string |
| `JWT_SECRET` | `dev-secret-change-me` | **Must change for production** |
| `APP_ENV` | `dev` | `dev` or `prod` |
| `FRONTEND_CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed origins |
| `OZ_API_KEY` | *(empty)* | API key for OZ inference |
| `OZ_MODEL_ID` | `anthropic/claude-haiku-4` | Model for AI inference |
| `AI_ENABLED` | `true` | Toggle AI features |

## Testing

```bash
# Run the full backend test suite
make test

# Run only e2e tests
cd code/backend && make e2e
```

**Current status:** 136/136 core tests passing. Some integration tests (`test_stats`, `test_sessions`) have fixture-level issues with the test harness (subprocess vs in-process DB writes), not application bugs.

## Known Issues & Roadmap

See [MVP_FINAL_AUDIT.md](.github/artifacts/MVP_FINAL_AUDIT.md) for the full audit. Key items:

- **Ghost List action type mismatch** — ghost logic expects semantic types but ActionLog uses HTTP signatures
- **Task update can't clear nullable fields** — `None` values are skipped during partial updates
- **localStorage JWT** — should migrate to httpOnly cookies before any non-local deployment
- **No HTTPS enforcement** — must deploy behind a reverse proxy (nginx/Caddy) for production

## Architecture & Planning Docs

Detailed design documents live in `.github/artifacts/`:

- [PDD.md](.github/artifacts/PDD.md) — Product Design Document (vision, user stories, data models)
- [architecture.md](.github/artifacts/architecture.md) — Technical architecture, API design, security ADRs
- [agents.md](.github/artifacts/agents.md) — AI prompt engineering, inference isolation, rate limiting
- [MVP_FINAL_AUDIT.md](.github/artifacts/MVP_FINAL_AUDIT.md) — Post-Phase 4 audit with all known issues

---

**Built as a personal tool for ambient productivity tracking.** Not accepting external contributions at this time.
