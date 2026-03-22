# Phase 4.2 Pre-Deployment Work (Action Items)

This is a new non-overwriting summary file containing the required personal tasks and blockers for Phase 4.2 deployment.

## Required accounts & credentials (user must supply)
- GitHub repo (code push, actions)
- Railway account + service
- Vercel account + project
- Neon account + PostgreSQL database
- LLM provider API key (Anthropic/Groq)
- JWT secret generation (e.g. `openssl rand -hex 32`)
- Optional: custom domain + Cloudflare DNS

## Absolute blockers
1. Neon `DATABASE_URL` not available -> stops Step 3/4
2. Railway project not created -> stops Step 5/8
3. Vercel project not created -> stops Step 6/8
4. Domain/Cloudflare not configured -> Step 9 blocked, cookie domain issue for production
5. GitHub secrets absent (`RAILWAY_TOKEN`, `RAILWAY_SERVICE_ID`, `VERCEL_TOKEN`) -> Step 8 blocked

## Step-level actions
1. Step 1: Alembic init (local). 2. Step 2: schema hardening (migration scripts).
2. Step 3: Neon migration (backup `dev.db`, migrate data, verify row counts).
3. Step 4: Switch backend to asyncpg connection string.
4. Step 5: Railway backend deploy (env vars: Neon URL, JWT secret, LLM key).
5. Step 6: Vercel frontend deploy (`NEXT_PUBLIC_API_BASE=backend URL`).
6. Step 7: Security hardening (cookie auth/CSRF/HSTS).
7. Step 8: GitHub Actions CI pipeline + branch protections.
8. Step 9: DNS/domain Cloudflare; ensure app/api subdomains and same cookie domain.
9. Step 10: Prod smoke test and go-live sign-off.

## Quick verification
- `GET /health` returns `{"status":"ok"}`
- `curl -i POST /login` sets `pulse_token` httpOnly Secure SameSite=Lax
- Task CRUD persists to Neon
- `pytest -q` + `npm run build` pass

## References
- .github/artifacts/phase4-2/plan/master.md
- .github/artifacts/phase4-2/plan/step-1-alembic-init.md ... step-10-prod-smoke-test.md

