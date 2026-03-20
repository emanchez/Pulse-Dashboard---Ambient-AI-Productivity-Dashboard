# Pulse Dashboard — Backend

FastAPI-based async REST API powering the Ambient AI Productivity Dashboard. Handles authentication, task management with event sourcing, focus sessions, manual reports, system state tracking, and AI-powered synthesis/suggestions via OZ (OpenRouter).

## Tech Stack

- **Framework:** FastAPI 0.100+ with Pydantic v2
- **Database:** SQLAlchemy 2.0 (async) — SQLite (dev) / PostgreSQL (prod)
- **Auth:** JWT (PyJWT) with bcrypt password hashing
- **AI:** OZ (OpenRouter) with configurable model (default: Claude Haiku)
- **Rate Limiting:** SlowAPI (200 req/min global, 5/min login in prod)
- **Sanitization:** Bleach for HTML input stripping
- **HTTP Client:** httpx (async, for OZ API calls)

## Directory Structure

```
app/
├── main.py              # FastAPI app, lifespan, middleware stack
├── api/                 # Route handlers
│   ├── auth.py          # POST /login, GET /me
│   ├── tasks.py         # CRUD /tasks (event-sourced)
│   ├── reports.py       # CRUD /reports + archive
│   ├── sessions.py      # Focus session start/stop/active
│   ├── stats.py         # Pulse, flow state, ghost list, weekly summary
│   ├── system_states.py # Vacation/leave CRUD + active state
│   └── ai.py            # Synthesis, suggestions, co-planning, accept-tasks
├── core/
│   ├── config.py        # Pydantic Settings (env vars, OZ config, CORS)
│   ├── security.py      # JWT create/decode, password hashing, get_current_user
│   └── limiter.py       # SlowAPI limiter instance
├── db/
│   ├── base.py          # SQLAlchemy declarative Base
│   └── session.py       # Async engine + session factory
├── middlewares/
│   └── action_log.py    # Event-sourcing middleware (logs POST/PUT/DELETE on /tasks)
├── models/              # SQLAlchemy ORM models
│   ├── user.py          # User (id, username, hashed_password)
│   ├── task.py          # Task (name, priority, tags, deadline, notes, etc.)
│   ├── action_log.py    # ActionLog (immutable event entries)
│   ├── session_log.py   # SessionLog (focus session records)
│   ├── manual_report.py # ManualReport (narrative entries with task links)
│   ├── system_state.py  # SystemState (vacation/leave periods)
│   ├── synthesis.py     # SynthesisReport (AI-generated weekly reports)
│   └── ai_usage.py      # AIUsageLog (rate limit tracking)
├── schemas/             # Pydantic v2 request/response models
│   ├── base.py          # CamelCase JSON serialization mixin
│   ├── flow_state.py    # FlowState response schema
│   ├── inference.py     # AI inference request/response schemas
│   ├── stats.py         # Pulse stats schema
│   └── synthesis.py     # Synthesis report schemas
└── services/            # Business logic layer
    ├── ai_service.py        # Orchestrates synthesis/suggest/co-plan
    ├── ai_rate_limiter.py   # Per-user AI usage enforcement
    ├── oz_client.py         # OZ API client with circuit breaker
    ├── prompt_builder.py    # Builds inference prompts from context
    ├── inference_context.py # Assembles user-scoped data for AI
    ├── synthesis_service.py # Synthesis report CRUD
    ├── report_service.py    # Report validation + queries
    ├── session_service.py   # Focus session logic
    ├── flow_state.py        # Derived flow metrics calculation
    ├── ghost_list_service.py# Stale/wheel-spinning task detection
    └── system_state_service.py # Active state + pause queries
scripts/
├── create_dev_user.py       # Idempotent dev user seeding (upsert)
├── setup_oz.py              # Interactive OZ API key configuration
├── migrate_add_indexes.py   # Add missing composite indexes to dev DB
└── migrate_task_user_id.py  # Backfill user_id on legacy tasks
tests/
├── conftest.py              # Shared fixtures (in-memory DB, test user)
├── test_api.py              # Core API endpoint tests
├── test_ai.py               # AI service unit tests
├── test_ghost_list.py       # Ghost list logic tests
├── test_inference_context.py# Context assembly tests
├── test_models.py           # ORM model tests
├── test_oz_client.py        # OZ client + circuit breaker tests
├── test_reports.py          # Report CRUD tests
├── test_sessions.py         # Session endpoint tests
├── test_stats.py            # Stats endpoint tests
├── test_system_states.py    # System state endpoint tests
└── e2e/
    ├── test_smoke.py        # Basic health + auth smoke test
    └── test_synthesis_flow.py # Full synthesis flow E2E
```

## Quick Start

### Prerequisites

- Python 3.10+
- A virtual environment tool (`python -m venv`)

### Install & Run

```bash
# Create venv and install dependencies
make deps

# Seed the dev user (idempotent)
python scripts/create_dev_user.py

# Start in foreground (with auto-reload)
make dev

# Or start in background
make start
```

The API will be available at **http://localhost:8000**. Interactive docs at **http://localhost:8000/docs**.

### Configure AI (Optional)

```bash
python scripts/setup_oz.py
```

Sets `OZ_API_KEY` in `.env`. Without it, AI endpoints return 503 but all other endpoints work normally.

## Makefile Reference

| Command | Description |
|---------|-------------|
| `make deps` | Create venv + install requirements |
| `make dev` | Start with `--reload` (foreground, Ctrl+C to stop) |
| `make start` | Start in background (PID saved to `.dev.pid`) |
| `make stop` | Stop background server |
| `make test` | Run pytest suite |
| `make e2e` | Run E2E tests only |

## API Endpoints

**28 total** — 2 public, 26 require `Authorization: Bearer <token>`.

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | `/login` | Returns JWT access token (rate-limited) |
| GET | `/me` | Current user profile |

### Tasks
| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks/` | List tasks for authenticated user |
| POST | `/tasks/` | Create task → triggers ActionLog |
| PUT | `/tasks/{id}` | Update task → triggers ActionLog |
| DELETE | `/tasks/{id}` | Delete task → triggers ActionLog |

### Reports
| Method | Path | Description |
|--------|------|-------------|
| GET | `/reports` | List reports (paginated, filterable) |
| POST | `/reports` | Create report |
| GET | `/reports/{id}` | Get single report |
| PUT | `/reports/{id}` | Update report |
| PATCH | `/reports/{id}/archive` | Archive report |
| DELETE | `/reports/{id}` | Delete report |

### Sessions
| Method | Path | Description |
|--------|------|-------------|
| POST | `/sessions/start` | Start focus session |
| POST | `/sessions/stop` | Stop active session |
| GET | `/sessions/active` | Get current active session |

### Stats
| Method | Path | Description |
|--------|------|-------------|
| GET | `/stats/pulse` | Silence state + gap analysis |
| GET | `/stats/flow-state` | Derived productivity metrics |
| GET | `/stats/ghost-list` | Stale/wheel-spinning tasks |
| GET | `/stats/weekly-summary` | This week's aggregated stats |

### System States
| Method | Path | Description |
|--------|------|-------------|
| GET | `/system-states` | List all states |
| POST | `/system-states` | Create state (vacation/leave) |
| GET | `/system-states/active` | Current active state |
| PUT | `/system-states/{id}` | Update state |
| DELETE | `/system-states/{id}` | Delete state |

### AI
| Method | Path | Description |
|--------|------|-------------|
| GET | `/ai/usage` | Current usage counts vs. caps |
| POST | `/ai/synthesis` | Trigger weekly synthesis (3/week) |
| GET | `/ai/synthesis/latest` | Latest completed synthesis |
| GET | `/ai/synthesis/{id}` | Specific synthesis report |
| POST | `/ai/suggest-tasks` | AI task suggestions (5/day) |
| POST | `/ai/co-plan` | Report ambiguity analysis (3/day) |
| POST | `/ai/accept-tasks` | Accept suggestions into task list |

### Infrastructure
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `{"status": "ok"}` |

## Environment Variables

Configured via `.env` (gitignored) in this directory:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/dev.db` | Async DB connection string |
| `JWT_SECRET` | `dev-secret-change-me` | **Change for production** — startup guard blocks default in non-dev |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` (8h) | Token TTL |
| `APP_ENV` | `dev` | `dev` or `prod` — controls CORS, error detail, rate limits |
| `FRONTEND_CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed origins |
| `OZ_API_KEY` | *(empty)* | OZ / OpenRouter API key |
| `OZ_MODEL_ID` | `anthropic/claude-haiku-4` | Model for inference |
| `AI_ENABLED` | `true` | Master toggle for AI endpoints |
| `OZ_MAX_WAIT_SECONDS` | `90` | Inference timeout |
| `OZ_MAX_CONTEXT_CHARS` | `8000` | Max context payload size |

## Security Features

- **JWT with `iss`/`aud`/`sub` claims** — 8-hour TTL, startup guard blocks default secret in prod
- **bcrypt password hashing** — no plaintext storage
- **User-scoped queries** — every DB query includes `WHERE user_id = <jwt_sub>`
- **Rate limiting** — 200 req/min global (SlowAPI), 5/min on `/login` in prod
- **Request body size limit** — 512 KB max (middleware)
- **Sanitized validation errors** — field names hidden in prod 422 responses
- **CORS fail-closed** — localhost origins rejected in non-dev environments
- **AI data isolation** — inference payloads only contain authenticated user's data

## Testing

```bash
# Full suite (136 passing)
make test

# E2E only
make e2e

# Specific test file
python -m pytest tests/test_ai.py -v
```

Tests use an in-memory SQLite database and mock external services (OZ). Some integration tests (`test_stats`, `test_sessions`) have known fixture issues related to the background subprocess test harness.

## Development Notes

### Event Sourcing

Every `POST`, `PUT`, `DELETE` on `/tasks` is intercepted by `ActionLogMiddleware`, which writes an immutable `ActionLog` entry. This creates a high-fidelity timeline used by the AI inference engine for silence gap analysis and weekly synthesis.

### CamelCase JSON Convention

Pydantic models use a `CamelCaseModel` base that serializes to camelCase JSON for the frontend while keeping snake_case internally. The OpenAPI spec reflects camelCase field names.

### Database Migrations

`Base.metadata.create_all` is used in development for convenience. **Production schema changes require Alembic migrations.** See [architecture.md](../../.github/artifacts/architecture.md) §5 for the migration discipline policy.

### Seeding Scripts

All scripts in `scripts/` are idempotent (upsert pattern). They never delete+recreate records, preserving UUIDs and foreign key relationships. See the seeding safety contract in the architecture docs.
