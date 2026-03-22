# Step 5 — Deploy Backend to Railway

## Purpose

Containerize the FastAPI backend and deploy it to Railway with all required environment variables, a health check endpoint, and auto-deploy from Git. This makes the backend accessible at a public HTTPS URL for the production frontend.

## 🔴 ABSOLUTE BLOCKERS — User Action Required

> **This step cannot begin until the user has:**
> 1. Created a **Railway account** at [railway.com](https://railway.com)
> 2. Created a **GitHub repository** for the project (Railway deploys from Git)
> 3. Obtained/generated:
>    - `DATABASE_URL` — Neon PostgreSQL connection string (from Step 3)
>    - `JWT_SECRET` — Generate with `openssl rand -hex 32`
>    - `LLM_API_KEY` — Anthropic or Groq API key (run `python scripts/setup_llm.py`)
> 4. Pushed the codebase to the GitHub repo
>
> **Agents cannot create cloud accounts, generate secrets, or push to Git.**

## Deliverables

- `code/backend/Dockerfile` for production deployment
- `code/backend/.dockerignore` to exclude dev files
- `railway.toml` (or Railway dashboard config) with health check, build settings
- All environment variables configured in Railway dashboard
- Backend accessible at `https://<app-name>.up.railway.app`
- `/health` endpoint returns 200

## Primary files to change

- [code/backend/Dockerfile](code/backend/Dockerfile) (new)
- [code/backend/.dockerignore](code/backend/.dockerignore) (new)
- [code/backend/railway.toml](code/backend/railway.toml) (new, optional)

## Detailed implementation steps

1. **🔴 USER: Create Railway project:**
   - Go to [railway.com/new](https://railway.com/new)
   - Click "Deploy from GitHub Repo"
   - Select the project repository
   - Railway will auto-detect the project structure

2. **Create `code/backend/Dockerfile`:**
   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   # Install system dependencies
   RUN apt-get update && apt-get install -y --no-install-recommends \
       curl \
       && rm -rf /var/lib/apt/lists/*

   # Install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application code
   COPY app/ ./app/
   COPY alembic/ ./alembic/
   COPY alembic.ini .

   # Set PYTHONPATH so `app` is importable
   ENV PYTHONPATH=/app

   # Run Alembic migrations on startup, then start uvicorn
   # Using a shell script to chain commands
   COPY scripts/entrypoint.sh .
   RUN chmod +x entrypoint.sh

   EXPOSE 8000

   CMD ["./entrypoint.sh"]
   ```

3. **Create `code/backend/scripts/entrypoint.sh`:**
   ```bash
   #!/bin/bash
   set -e

   echo "Running Alembic migrations..."
   alembic upgrade head

   echo "Starting uvicorn..."
   exec uvicorn app.main:app \
     --host 0.0.0.0 \
     --port ${PORT:-8000} \
     --workers 1 \
     --log-level info
   ```
   - Railway sets `PORT` env var automatically. Uvicorn must bind to `0.0.0.0` (not `127.0.0.1`).
   - `--workers 1` — single worker sufficient for single-user app; saves memory.
   - `--reload` is **NOT** used in production.
   - Alembic migrations run on every deploy to ensure schema is up-to-date.

4. **Create `code/backend/.dockerignore`:**
   ```
   .venv/
   __pycache__/
   *.pyc
   data/
   logs/
   tests/
   scripts/create_dev_user.py
   scripts/setup_llm.py
   .dev.pid
   .env
   .env.production
   *.db
   *.db.bak
   ```

5. **🔴 USER: Configure Railway environment variables:**
   In the Railway dashboard → Service → Variables:

   | Variable | Value | Notes |
   |----------|-------|-------|
   | `APP_ENV` | `prod` | Enables production guards |
   | `DATABASE_URL` | `postgresql+asyncpg://...` | From Neon (Step 3) |
   | `JWT_SECRET` | `<openssl rand -hex 32 output>` | **User must generate** |
   | `JWT_ALGORITHM` | `HS256` | |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | 1 hour in production |
   | `FRONTEND_CORS_ORIGINS` | `https://<frontend-url>` | Set after Step 6; use Railway URL initially |
   | `LLM_PROVIDER` | `anthropic` | Or `groq` for Llama free tier |
   | `LLM_API_KEY` | `<your-api-key>` | **User must provide** (Anthropic or Groq) |
   | `LLM_MODEL_ID` | `claude-3-5-haiku-latest` | Cheapest capable model |
   | `AI_ENABLED` | `true` | Set to `false` to disable AI in prod |
   | `PORT` | `8000` | Railway may auto-set this |

6. **Configure Railway settings (dashboard or `railway.toml`):**
   - **Root directory:** `code/backend` (Railway must know the Dockerfile is in this subdirectory)
   - **Health check path:** `/health`
   - **Health check timeout:** 30 seconds
   - **Restart policy:** On failure

7. **Create optional `railway.toml`** (alternative to dashboard config):
   ```toml
   [build]
   dockerfilePath = "code/backend/Dockerfile"

   [deploy]
   healthcheckPath = "/health"
   healthcheckTimeout = 30
   restartPolicyType = "ON_FAILURE"
   restartPolicyMaxRetries = 3
   ```

8. **Deploy and verify:**
   ```bash
   # Railway deploys automatically on push to the connected branch
   # Or trigger manually via Railway CLI:
   railway up

   # Verify
   curl -s https://<app-name>.up.railway.app/health
   # Expected: {"status":"ok"}
   ```

## Integration & Edge Cases

- **Railway `PORT` env var:** Railway assigns a dynamic port via `$PORT`. The entrypoint script uses `${PORT:-8000}` to respect this.
- **CORS on first deploy:** On the first deploy, `FRONTEND_CORS_ORIGINS` won't have the correct frontend URL yet (Step 6 hasn't happened). Set it to the Railway app URL temporarily, then update after Step 6.
- **Alembic on startup:** Running `alembic upgrade head` on every startup is idempotent — if migrations are already applied, it's a no-op. This ensures any new migrations are applied on deploy.
- **Memory limits:** Railway Hobby plan allows up to 0.5 GB RAM. FastAPI + uvicorn with 1 worker uses ~80–150 MB. Well within limits.
- **Startup time:** First deploy may take 2–3 minutes (Docker build + dependency install). Subsequent deploys use cached layers.
- **Production rate limits:** The `/login` endpoint is already rate-limited to `5/minute` when `APP_ENV=prod` (from `auth.py`). Verify this is active.

## Acceptance Criteria

1. 🔴 Railway project exists and is connected to the GitHub repo (user-verified).
2. `curl https://<app-name>.up.railway.app/health` returns `{"status":"ok"}`.
3. All environment variables are set in the Railway dashboard (no defaults from `.env`).
4. `APP_ENV=prod` is active (verify: `GET /health` works, `create_all()` is skipped in logs).
5. `JWT_SECRET` is NOT the default `dev-secret-change-me` (startup guard would crash if it were).
6. Login works: `POST /login` with valid credentials returns a 200 with a JWT.
7. Database queries work: `GET /tasks` (authenticated) returns data from the Neon database.
8. `--reload` is **not** used in production (verify in entrypoint.sh/Dockerfile).
9. Railway health check is configured and passing (green status in dashboard).

## Testing / QA

### Automated (pre-deploy)
```bash
cd code/backend

# Build Docker image locally to verify it works
docker build -t pulse-backend .
docker run --rm -p 8000:8000 \
  -e APP_ENV=dev \
  -e DATABASE_URL=sqlite+aiosqlite:///./data/dev.db \
  -e JWT_SECRET=test-secret-for-docker \
  pulse-backend

# Verify
curl http://localhost:8000/health
```

### Manual (post-deploy)
1. Visit `https://<app-name>.up.railway.app/health` in a browser — should show `{"status":"ok"}`.
2. Use curl to login and list tasks:
   ```bash
   TOKEN=$(curl -s -X POST https://<app-name>.up.railway.app/login \
     -H "Content-Type: application/json" \
     -d '{"username":"devuser","password":"<password>"}' | jq -r '.access_token')
   curl -s -H "Authorization: Bearer $TOKEN" https://<app-name>.up.railway.app/tasks
   ```
3. Check Railway logs for any errors or warnings.

## Files touched

- [code/backend/Dockerfile](code/backend/Dockerfile) (new)
- [code/backend/.dockerignore](code/backend/.dockerignore) (new)
- [code/backend/scripts/entrypoint.sh](code/backend/scripts/entrypoint.sh) (new)
- [code/backend/railway.toml](code/backend/railway.toml) (new, optional)

## Estimated effort

1 dev day (excluding user account/config time)

## Concurrency & PR strategy

- Branch: `phase-4.2/step-5-backend-deploy-railway`
- Blocking steps:
  - `Blocked until: .github/artifacts/phase4-2/plan/step-4-asyncpg-switchover.md`
  - **🔴 Blocked until: Railway account created by user**
  - **🔴 Blocked until: GitHub repo created and code pushed by user**
  - **🔴 Blocked until: JWT_SECRET generated by user**
  - **🔴 Blocked until: LLM_API_KEY provided by user**
- Merge Readiness: true

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Railway build fails due to missing system dependencies | Dockerfile uses `python:3.11-slim` with `curl` for health checks. Test build locally first. |
| Railway $5 credit exhausted | Monitor usage in Railway dashboard. Single-user FastAPI app uses minimal resources. |
| Environment variable misconfiguration | Use `.env.production.example` as a checklist. Startup guards catch missing `JWT_SECRET` and `LLM_API_KEY`. |
| Alembic migration fails on deploy startup | Test migrations locally against PostgreSQL before pushing. Keep rollback path tested. |
| CORS blocks frontend after backend URL changes | Update `FRONTEND_CORS_ORIGINS` in Railway whenever frontend URL changes. |

## References

- [Railway Python deployment docs](https://docs.railway.com/guides/python)
- [Railway environment variables](https://docs.railway.com/develop/variables)
- [code/backend/app/main.py](code/backend/app/main.py) — Lifespan guards
- [code/backend/app/core/config.py](code/backend/app/core/config.py) — Settings and validation

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
