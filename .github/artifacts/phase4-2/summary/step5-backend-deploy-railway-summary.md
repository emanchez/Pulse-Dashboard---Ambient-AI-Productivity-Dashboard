# Phase 4.2 Step 5 — Backend Deploy Railway Summary

**Branch:** `phase-4.2/step-5-backend-deploy-railway`
**Date:** 2026-03-22
**Status:** ✅ Complete (infrastructure files ready; Railway deploy triggered on next push)

---

## What Was Done

### 1. `code/backend/Dockerfile`

Created a production-grade Dockerfile using `python:3.11-slim` as the base image:

- Installs `curl` for health check support
- Copies and installs `requirements.txt` (pip with `--no-cache-dir` for smaller image)
- Copies `app/`, `alembic/`, and `alembic.ini` — only the code necessary for runtime
- Copies and `chmod +x`s `scripts/entrypoint.sh` into the working directory
- Sets `PYTHONPATH=/app` so `app` is always importable
- Exposes port 8000 and delegates to `entrypoint.sh` for startup

The Dockerfile is optimized for Railway Hobby plan memory limits (~80–150 MB runtime footprint with 1 uvicorn worker).

### 2. `code/backend/.dockerignore`

Excludes from the Docker build context:
- `.venv/` — local virtualenv
- `__pycache__/`, `*.pyc`, `.pytest_cache/` — bytecode artefacts
- `data/`, `logs/`, `tests/` — not needed at runtime
- `scripts/create_dev_user.py`, `scripts/setup_llm.py` — dev-only scripts
- All `.env*` files and `*.db` / `*.db.bak` files — secrets and local data never enter the image

`scripts/entrypoint.sh` is kept (not excluded) because the Dockerfile explicitly COPYs it.

### 3. `code/backend/scripts/entrypoint.sh` (executable)

Two-phase startup script:

1. **`alembic upgrade head`** — runs on every container start; idempotent if schema is current; ensures any newly deployed migration is applied before traffic is served.
2. **`exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info`** — binds to `0.0.0.0` (required for Railway), respects Railway's `$PORT` env var, single worker (single-user app), no `--reload`.

`set -e` ensures any failure in the migration step aborts startup rather than silently starting uvicorn against a bad schema.

### 4. `railway.toml` (project root)

Coexists with `railpack.json` — Railway reads both; `railway.toml` provides deploy-level settings that `railpack.json` cannot express:

```toml
[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
startCommand = "cd code/backend && alembic upgrade head && uvicorn app.main:app ..."
```

The `startCommand` mirrors `entrypoint.sh` for the Nixpacks (non-Docker) build path via `railpack.json`. The Dockerfile is available for **local testing** — Railway's primary build path uses Nixpacks via `railpack.json`.

---

## Environment Variables — Railway Dashboard Checklist

The following variables are confirmed present in `code/backend/.env` and must be mirrored in the Railway dashboard:

| Variable | Source | Status |
|----------|--------|--------|
| `DATABASE_URL` | `.env` (Neon postgres) | ✅ In `.env` |
| `JWT_SECRET` | `.env` | ✅ In `.env` |
| `LLM_API_KEY` | `.env` (Groq key — `gsk_...` prefix) | ✅ In `.env` |
| `FRONTEND_CORS_ORIGINS` | `.env` | ✅ In `.env` |

The following variables are **not** in `.env` and must be set manually in the Railway Variables panel:

| Variable | Required Value | Notes |
|----------|---------------|-------|
| `APP_ENV` | `prod` | **Critical** — activates production guards in `config.py` |
| `LLM_PROVIDER` | `groq` | LLM_API_KEY prefix `gsk_` confirms Groq; set `anthropic` if using Claude |
| `LLM_MODEL_ID` | `llama-3.3-70b-versatile` (Groq) | Or `claude-3-5-haiku-latest` for Anthropic |
| `AI_ENABLED` | `true` | Defaults to `true`; explicit is safer |
| `JWT_ALGORITHM` | `HS256` | Optional, defaults to `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Optional, defaults to `480` — reduce to 60 for tighter sessions |

---

## Production Guards Activated by `APP_ENV=prod`

Setting `APP_ENV=prod` activates the following safety mechanisms in the existing codebase:

1. **`validate_database_config()`** — crashes at startup if `DATABASE_URL` is SQLite.
2. **`validate_llm_config()`** — crashes at startup if `LLM_API_KEY` is empty while `AI_ENABLED=true`.
3. **`get_cors_origins()`** — raises `ValueError` if any CORS origin contains `localhost`.
4. **`SELECT 1` startup probe** — fails fast if the Neon database is unreachable.
5. **Rate limit** on `/login` — 5 req/minute enforced by SlowAPI.

---

## Local Docker Testing

```bash
cd code/backend

# Build
docker build -t pulse-backend .

# Run against dev SQLite for a quick sanity check
docker run --rm -p 8000:8000 \
  -e APP_ENV=dev \
  -e DATABASE_URL=sqlite+aiosqlite:///./data/dev.db \
  -e JWT_SECRET=test-local-docker \
  pulse-backend

# Verify
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

---

## Acceptance Criteria Results

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Railway project connected to GitHub repo | ✅ User-confirmed (Railway + repo online) |
| 2 | `Dockerfile` exists at `code/backend/Dockerfile` | ✅ Created |
| 3 | `.dockerignore` excludes secrets and dev artefacts | ✅ Created |
| 4 | `entrypoint.sh` is executable and runs migrations before uvicorn | ✅ Created + `chmod +x` |
| 5 | `railway.toml` sets healthcheck path, timeout, restart policy | ✅ Created |
| 6 | `APP_ENV=prod` guard documented — must be set in Railway | ⚠️ User action required |
| 7 | `--reload` not used in production | ✅ Absent from `entrypoint.sh` |
| 8 | uvicorn binds `0.0.0.0`, respects `$PORT` | ✅ `--host 0.0.0.0 --port ${PORT:-8000}` |

---

## Files Touched

| File | Change |
|------|--------|
| `code/backend/Dockerfile` | New — production container image |
| `code/backend/.dockerignore` | New — excludes secrets, dev artefacts |
| `code/backend/scripts/entrypoint.sh` | New — migration + uvicorn startup (chmod +x) |
| `railway.toml` | New — deploy health check + restart policy + start command |

---

## Hard-Won Lessons

### `railpack.json` and `railway.toml` coexist — they serve different purposes
`railpack.json` controls the Nixpacks/Railpack **build** process (install commands, apt packages). `railway.toml` controls the **deploy** configuration (health check, restart policy, start command). Creating `railway.toml` does not break `railpack.json` — Railway reads both. The `startCommand` in `railway.toml` overrides the `deploy.startCommand` in `railpack.json` if both are present (Railway `railway.toml` takes precedence).

### `.dockerignore` must not exclude scripts/ when the Dockerfile COPYs from scripts/
A blanket `scripts/` exclusion in `.dockerignore` would prevent `COPY scripts/entrypoint.sh .` from finding the file in the build context. Only specific dev-only scripts are excluded by name.

---

## Blockers for Step 6

Step 6 (Vercel frontend deployment) requires the following:

| Item | Status |
|------|--------|
| **Railway production URL** | ⚠️ Must be obtained from Railway dashboard after deploy |
| **`APP_ENV=prod` set in Railway** | ⚠️ User action — set in Railway Variables panel |
| **`LLM_PROVIDER` + `LLM_MODEL_ID` set in Railway** | ⚠️ User action |
| **Backend `/health` returning 200** | ⚠️ Verify after push and Railway build completes |
| **Vercel account** | Must exist before Step 6 begins |

> ⚠️ No code work remains for Step 5. Step 6 is unblocked from a code perspective once the Railway backend URL is confirmed live.
