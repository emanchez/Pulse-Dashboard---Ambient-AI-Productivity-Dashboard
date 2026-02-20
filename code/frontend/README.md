# PersonalDash Frontend (scaffold)

Requirements
- Node: 20.x recommended
- npm: 8+

Quick start (local)

1. Install backend deps and start the backend (from repo root):

```bash
cd code/backend
python -m pip install -r requirements.txt
export PYTHONPATH=$(pwd)
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
```

2. Generate the TypeScript client (defaults to http://localhost:8000/openapi.json):

```bash
cd code/frontend
npm ci
./lib/generate-client.sh http://localhost:8000/openapi.json ./lib/generated
```

3. Start the frontend dev server:

```bash
npm run dev
```

Makefile (developer shortcuts)

The repository includes simple Makefiles to speed local development:

- `make deps` — install backend Python deps and frontend npm packages
- `make dev` — start backend (127.0.0.1:8000) and frontend (localhost:3000) in background; PIDs stored under `.tmp/`
- `make stop` — stop background dev servers started with `make dev`
- `make test` — runs backend tests (pytest); frontend currently has no test runner
- `make generate-api` — runs the TypeScript client generator
- `make build` — builds the frontend

Examples:

```bash
# install both services' deps
make deps

# start dev servers (background)
make dev

# stop dev servers
make stop

# run backend tests
make test

# regenerate the frontend API client
make generate-api
```

Notes
- The generator script accepts an optional OPENAPI URL and output dir: `./lib/generate-client.sh [OPENAPI_URL] [OUT_DIR]`.
- CI runs the generator and build; ensure your local Node version matches CI (Node 20 recommended).

---

## Regenerating the API Client

Run this whenever a backend schema or endpoint changes (including `/stats/pulse` or any Task field):

```bash
# 1. Start the backend (repo root)
cd code/backend
export PYTHONPATH=$(pwd)
nohup python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
until curl -sS http://127.0.0.1:8000/openapi.json > /dev/null; do sleep 1; done

# 2. Regenerate from code/frontend
cd code/frontend
npm ci
npm run generate:api          # writes to lib/generated (pinned output path)

# 3. Commit the updated stubs
git add lib/generated
git commit -m "chore(frontend): regenerate API client"
```

`lib/generated/types.ts` holds the `Task` type; `lib/generated/pulseClient.ts` holds `PulseStats` and `getPulse`. Both are **canonical** — do not edit them by hand after running the generator. `lib/api.ts` re-exports them so components import from a single stable path.

> **CI note:** the CI workflow runs `npm run generate:api` before `npm run build`. If the backend contract changes and the stubs are not updated, the build step will fail as a safety gate.

---

## Manual Save Workflow

The `TaskBoard` component uses a **deferred save** pattern:

1. Every field edit (name, priority, deadline, notes, completion) is stored in an in-memory `Map<id, Partial<Task>>` — no API call is made.
2. Rows with pending changes display an amber **Unsaved** pill. The "Save changes" button is active only while the map is non-empty.
3. Clicking **Save changes** iterates the map and issues a `PUT /tasks/:id` for each dirty row. On full success, the unsaved map is cleared and the task list re-fetched.
4. Mid-session browser refresh discards all pending edits by design — unsaved state is intentionally ephemeral.

This pattern prevents accidental partial saves and keeps the action log clean (one log entry per intentional user commit).

---

## Silence Indicator States

The `PulseCard` polls `GET /stats/pulse` every 30 seconds and displays one of three states:

| State | Badge colour | Meaning |
|----------|-------------|----------------------------------------------------------|
| `engaged` | Emerald | Last action was ≤ 48 hours ago and no active pause. |
| `stagnant` | Amber | No action logged for > 48 hours (gap > 2 880 minutes) and no active pause. |
| `paused` | Sky blue | A `SystemState` record with `modeType` of **Vacation** or **Leave** covers the current timestamp. Overrides stagnant regardless of gap size. |

`pausedUntil` is populated only in the `paused` state and shows the `SystemState.endDate`. A null `pausedUntil` means the pause has no scheduled end.

Zero action logs → `gapMinutes = 0`, state is `engaged` (system is fresh, not stagnant).

Commit policy for generated client

- Current policy: a canonical generated client is committed to the repo under `code/frontend/lib/generated` to avoid blocking frontend work. Regenerate when the API surface changes.
- Regeneration steps:

```bash
# Start backend (from repo root)
cd code/backend
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
export PYTHONPATH=$(pwd)
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# Generate client (from code/frontend)
cd code/frontend
npm ci
./lib/generate-client.sh http://127.0.0.1:8000/openapi.json ./lib/generated

# Commit if acceptable
git add code/frontend/lib/generated && git commit -m "chore(frontend): update generated API client"
```

- CI policy: CI runs `npm run generate:api` before `npm run build` as a verification step; CI Node is set to 20.
