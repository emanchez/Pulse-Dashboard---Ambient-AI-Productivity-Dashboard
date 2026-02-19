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
