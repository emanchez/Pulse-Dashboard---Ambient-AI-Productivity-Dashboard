# Phase 4.2 — Production Deployment

## Scope

Migrate the Ambient AI Productivity Dashboard from local-dev (SQLite, `localhost`, `make dev`) to a production deployment. This phase covers database migration to managed PostgreSQL, backend deployment to a cloud PaaS, frontend deployment to a CDN-backed host, security hardening (HTTPS, httpOnly cookie auth, CSRF), environment configuration, CI/CD pipeline setup, and DNS/domain configuration.

### Explicitly Out of Scope

| Item | Reason |
|------|--------|
| Multi-user features (user registration, admin panel) | Post-MVP; app is single-user |
| Custom domain email (e.g. noreply@pulse.app) | Not needed for single-user |
| CDN for static assets beyond what Vercel provides | Vercel includes global CDN |
| Monitoring/alerting (Datadog, Sentry, PagerDuty) | Phase 4.3; basic platform metrics suffice for launch |
| Load testing / performance benchmarking | Single-user; not needed yet |
| Blue-green / canary deployment strategy | Single-user; simple deploys are fine |

---

## Service Selection — Recommended Stack

After evaluating free/cost-effective hosting options, the following stack is recommended for a single-user personal productivity app:

### Recommended Services

| Component | Service | Plan | Est. Monthly Cost | Rationale |
|-----------|---------|------|-------------------|-----------|
| **Frontend** | **Vercel** | Hobby (Free) | $0 | Native Next.js support, automatic CI/CD from Git, global CDN, free SSL, preview deployments. Best-in-class for Next.js. |
| **Backend** | **Railway** | Hobby ($5 w/ credits) | $0–5 | Usage-based billing (pay only for active CPU/memory), Docker support, built-in secrets management, auto-deploy from Git. A FastAPI app serving one user will stay well within the $5 credit. Alternative: Render Free (but Render free services spin down after 15 min inactivity, causing cold-start delays). |
| **Database** | **Neon** | Free | $0 | Serverless PostgreSQL with connection pooling, scale-to-zero, 0.5 GB storage per project, 100 CU-hours/month. Perfect for a single-user app. No server to manage. Compatible with `asyncpg`/SQLAlchemy async. |
| **AI Inference** | **LLMClient** (Anthropic/Groq) | Existing | Per-use | Already integrated via `LLMClient`. `LLM_API_KEY` and `LLM_PROVIDER` required. Claude Haiku is the cheapest capable model. |
| **DNS/Domain** | **Cloudflare** | Free | $0 (+ domain cost) | Free DNS, free SSL, DDoS protection. Domain registration ~$10–15/year via any registrar. |

### Alternatives Considered

| Component | Alternative | Why Not Primary |
|-----------|------------|-----------------|
| Frontend | Render Static | Less optimized for Next.js SSR/ISR; Vercel is purpose-built |
| Frontend | Railway | No built-in CDN; would need to serve Next.js as a Node service |
| Backend | Render Free | 15-min spindown on inactivity; /health pings would be needed to keep alive. Acceptable if $0 is hard requirement |
| Backend | Fly.io | Good option but requires credit card upfront, no free tier for new orgs, more DevOps overhead (Dockerfile + fly.toml) |
| Database | Supabase | Free tier has 500 MB + 30-day project limit; Neon's serverless model and scale-to-zero are better for intermittent single-user usage |
| Database | Render Postgres | Free tier expires after 30 days; paid starts at $6/mo |
| Database | Railway Postgres | Cheap but eats into the $5 credit alongside the backend compute |

### Required Accounts & API Keys

> **🔴 USER ACTION REQUIRED** — The following accounts and credentials must be obtained by the user. Agents cannot create accounts or purchase domains.

| Item | Where to Get | Used By | Blocking Steps |
|------|-------------|---------|----------------|
| **Vercel account** | [vercel.com/signup](https://vercel.com/signup) | Frontend deployment | Steps 6, 8 |
| **Railway account** | [railway.com/login](https://railway.com/login) | Backend deployment | Steps 5, 8 |
| **Neon account** | [console.neon.tech](https://console.neon.tech) | PostgreSQL database | Steps 3, 4 |
| **LLM API key** | Run `python scripts/setup_llm.py` or configure manually in `.env` | AI inference | Step 5 |
| **Domain name** (optional) | Any registrar (Namecheap, Cloudflare, etc.) | Custom domain | Step 7 |
| **Cloudflare account** (optional) | [cloudflare.com](https://cloudflare.com) | DNS management | Step 7 |
| **GitHub repo** | [github.com](https://github.com) | CI/CD for Vercel + Railway | Steps 5, 6, 8 |
| **Strong JWT_SECRET** | Generate locally: `openssl rand -hex 32` | Backend auth | Step 5 |

---

## Phase-level Deliverables

1. **Alembic migration framework** initialized with a baseline migration capturing the full current schema.
2. **Schema hardening migrations** — `user_id` NOT NULL constraints, foreign key constraints, composite indexes on `ai_usage_logs`.
3. **Neon PostgreSQL database** provisioned and seeded with data migrated from `dev.db`.
4. **SQLAlchemy async engine** switched from `aiosqlite` to `asyncpg` with connection pooling.
5. **Security hardening** — JWT moved to httpOnly cookies, CSRF protection, HTTPS-only enforcement, production rate limits.
6. **Backend deployed** on Railway with environment variables, health check, and auto-deploy from Git.
7. **Frontend deployed** on Vercel with `NEXT_PUBLIC_API_BASE` pointing to the production backend URL.
8. **DNS and domain** (optional) configured with Cloudflare for custom domain on both frontend and backend.
9. **CI/CD pipeline** — automated test run on push, deploy-on-merge to `main`.
10. **Production smoke test** — full end-to-end verification of login, task CRUD, AI inference, and report creation.

---

## Steps (ordered)

1. Step 1 — [step-1-alembic-init.md](./step-1-alembic-init.md) — Initialize Alembic, create baseline migration from current models
2. Step 2 — [step-2-schema-hardening.md](./step-2-schema-hardening.md) — Add FK constraints, NOT NULL on `user_id`, composite indexes, fix `start_date` nullability
3. Step 3 — [step-3-neon-provision-migrate.md](./step-3-neon-provision-migrate.md) — Provision Neon database, migrate data from SQLite `dev.db` to PostgreSQL
4. Step 4 — [step-4-asyncpg-switchover.md](./step-4-asyncpg-switchover.md) — Switch SQLAlchemy engine from `aiosqlite` to `asyncpg`, add connection pooling
5. Step 5 — [step-5-backend-deploy-railway.md](./step-5-backend-deploy-railway.md) — Dockerize backend, deploy to Railway, configure env vars and health check
6. Step 6 — [step-6-frontend-deploy-vercel.md](./step-6-frontend-deploy-vercel.md) — Deploy Next.js frontend to Vercel, configure `NEXT_PUBLIC_API_BASE`
7. Step 7 — [step-7-security-hardening.md](./step-7-security-hardening.md) — httpOnly cookie auth, CSRF protection, HTTPS enforcement, production rate limits
8. Step 8 — [step-8-cicd-pipeline.md](./step-8-cicd-pipeline.md) — GitHub Actions for test + deploy, branch protection rules
9. Step 9 — [step-9-dns-domain.md](./step-9-dns-domain.md) — Custom domain setup with Cloudflare DNS (optional but recommended)
10. Step 10 — [step-10-prod-smoke-test.md](./step-10-prod-smoke-test.md) — End-to-end production verification and go-live checklist

---

## Merge Order

Steps are **strictly sequential** due to cascading dependencies (each step's output is the next step's input):

1. `.github/artifacts/phase4-2/plan/step-1-alembic-init.md` — branch: `phase-4.2/step-1-alembic-init`
2. `.github/artifacts/phase4-2/plan/step-2-schema-hardening.md` — branch: `phase-4.2/step-2-schema-hardening` (after step 1)
3. `.github/artifacts/phase4-2/plan/step-3-neon-provision-migrate.md` — branch: `phase-4.2/step-3-neon-provision-migrate` (after step 2; **BLOCKED on Neon account**)
4. `.github/artifacts/phase4-2/plan/step-4-asyncpg-switchover.md` — branch: `phase-4.2/step-4-asyncpg-switchover` (after step 3; **BLOCKED on Neon DATABASE_URL**)
5. `.github/artifacts/phase4-2/plan/step-5-backend-deploy-railway.md` — branch: `phase-4.2/step-5-backend-deploy-railway` (after step 4; **BLOCKED on Railway account + LLM_API_KEY + JWT_SECRET**)
6. `.github/artifacts/phase4-2/plan/step-6-frontend-deploy-vercel.md` — branch: `phase-4.2/step-6-frontend-deploy-vercel` (after step 5; **BLOCKED on Vercel account + production backend URL**)
7. `.github/artifacts/phase4-2/plan/step-7-security-hardening.md` — branch: `phase-4.2/step-7-security-hardening` (after step 6; needs both deploys live to test cookie flow)
8. `.github/artifacts/phase4-2/plan/step-8-cicd-pipeline.md` — branch: `phase-4.2/step-8-cicd-pipeline` (after step 5+6; **BLOCKED on GitHub repo**)
9. `.github/artifacts/phase4-2/plan/step-9-dns-domain.md` — branch: `phase-4.2/step-9-dns-domain` (after step 6+7; **BLOCKED on domain purchase + Cloudflare account**)
10. `.github/artifacts/phase4-2/plan/step-10-prod-smoke-test.md` — branch: `phase-4.2/step-10-prod-smoke-test` (last; validates everything)

---

## Phase Acceptance Criteria

1. `alembic upgrade head` runs cleanly against a fresh Neon PostgreSQL database and produces a schema matching all SQLAlchemy models.
2. All `user_id` columns on user-owned tables are `NOT NULL` with `FOREIGN KEY` references to `users.id`.
3. `dev.db` data (user, tasks, reports, action logs, system states, synthesis reports) is present and queryable in the Neon production database.
4. Backend health check (`GET /health`) returns `{"status":"ok"}` on the Railway production URL.
5. Frontend loads at the Vercel production URL and successfully communicates with the backend (login, task list, AI features).
6. JWT is stored in an `httpOnly` cookie with `Secure` and `SameSite=Lax` flags — no `localStorage` token storage.
7. CSRF protection is active on all state-mutating endpoints when cookie auth is enabled.
8. All API responses are served over HTTPS only.
9. `CORS` origins are configured to allow only the production frontend domain (no `localhost`).
10. `npm run build` and `pytest -q` pass in CI before any deploy to `main`.
11. Production login → create task → create report → trigger synthesis → verify results end-to-end.

---

## Concurrency Groups & PR Strategy

### Group A — Database & Migration (Steps 1–4)
- **Strictly sequential:** Each step depends on the prior step's output.
- Step 1 must merge before Step 2 (Alembic must exist before hardening migrations).
- Step 3 requires a Neon account (user action).
- Step 4 requires the Neon `DATABASE_URL` from Step 3.

### Group B — Deployment (Steps 5–6)
- **Strictly sequential:** Backend must deploy first (Step 5) to get a production URL before frontend (Step 6) can configure `NEXT_PUBLIC_API_BASE`.
- Step 5 is **BLOCKED** on: Railway account, `LLM_API_KEY`, `JWT_SECRET`, Neon `DATABASE_URL`.
- Step 6 is **BLOCKED** on: Vercel account, Step 5 completion (need backend URL).

### Group C — Security & Infrastructure (Steps 7–9)
- Step 7 (security hardening) depends on both deploys being live.
- Step 8 (CI/CD) can begin after Steps 5+6 but benefits from Step 7 being complete.
- Step 9 (DNS) is independent of Step 7/8 but requires a domain + Cloudflare account.
- **Steps 7 and 9 can be parallelized** if both deploys are live and the domain is purchased.

### Group D — Verification (Step 10)
- **Merge last.** Validates all prior steps against production.

---

## Verification Plan

### Automated (CI)
```bash
# Backend test suite (run against test SQLite — not production)
cd code/backend && python -m pytest -q --tb=short

# Frontend build verification
cd code/frontend && npm run build && npx tsc --noEmit
```

### Manual Smoke Test (Production)
```bash
# 1. Health check
curl -s https://<backend-url>/health
# Expected: {"status":"ok"}

# 2. Login (cookie returned in Set-Cookie header)
curl -s -c cookies.txt -X POST https://<backend-url>/login \
  -H "Content-Type: application/json" \
  -d '{"username":"devuser","password":"<password>"}'
# Expected: 200 + Set-Cookie header with httpOnly, Secure flags

# 3. List tasks (using cookie)
curl -s -b cookies.txt https://<backend-url>/tasks
# Expected: 200 + JSON array of tasks

# 4. Frontend loads
curl -s -o /dev/null -w "%{http_code}" https://<frontend-url>
# Expected: 200

# 5. CORS check
curl -s -I -X OPTIONS https://<backend-url>/tasks \
  -H "Origin: https://<frontend-url>" \
  -H "Access-Control-Request-Method: GET"
# Expected: Access-Control-Allow-Origin: https://<frontend-url>
```

---

## Risks, Rollbacks & Migration Notes

| Risk | Impact | Mitigation |
|------|--------|------------|
| Neon free tier compute limits (100 CU-hrs/mo) exceeded | DB becomes unresponsive | Scale-to-zero is enabled by default; single-user usage is well under 100 CU-hrs. Monitor in Neon dashboard. Upgrade to Launch ($15/mo) if needed. |
| Railway $5 credit exhausted mid-month | Backend goes offline | FastAPI serving one user uses ~0.1 vCPU and <256 MB RAM. At Railway rates (~$0.000463/min for 256 MB), $5 covers ~10,800 minutes (7.5 days 24/7). With scale-to-zero and intermittent use, should last the month. Monitor usage. |
| SQLite → PostgreSQL data migration loses data | Data loss | Step 3 includes a mandatory `dev.db` backup before any migration. Validate row counts post-migration. Keep `dev.db.pre-deploy.bak` permanently. |
| httpOnly cookie auth breaks existing frontend token flow | Auth broken, app unusable | Step 7 implements cookie auth behind the `APP_ENV=prod` flag. Dev mode retains `localStorage` flow. Both paths are tested. |
| Alembic migration fails on Neon | Cannot deploy schema | Test all migrations locally against a PostgreSQL Docker container before running on Neon. Keep `alembic downgrade` path tested. |
| LLM API key invalid or expired in production | AI features fail with 503 | `ServiceDisabledError` handling (from Phase 4.1.2 LLMClient) returns a clean 503. UI degrades gracefully. Non-blocking for core task/report functionality. |
| DNS propagation delay on custom domain | Site unreachable via domain for hours | Use platform-provided URLs (.vercel.app / .up.railway.app) as primary until DNS propagates. Domain is optional. |

### Rollback Plan
1. **Frontend:** Vercel supports instant rollback to any previous deployment via the dashboard.
2. **Backend:** Railway supports instant rollback to any previous deployment.
3. **Database:** Keep `dev.db.pre-deploy.bak`. Neon supports branching for instant snapshots. If schema migration breaks, `alembic downgrade` to previous revision.
4. **Full rollback:** Revert `DATABASE_URL` to local SQLite, revert `NEXT_PUBLIC_API_BASE` to `localhost:8000`, run `make dev` locally.

---

## References

- [MVP_FINAL_AUDIT.md](../../MVP_FINAL_AUDIT.md) — Audit findings driving this deployment phase
- [architecture.md](../../architecture.md) — Data schema, API design, security ADRs, migration discipline
- [agents.md](../../agents.md) — AI inference data privacy requirements
- [copilot-instructions.md](../../copilot-instructions.md) — Project coding standards and hard-won lessons
- Phase 4.1 summaries: [step1-5](../summary/step1-5-summary.md), [step6-8](../summary/step6-8-frontend-summary.md), [step9](../summary/step9-test-harness-summary.md)
- [CORS bug report](../summary/cors-null-status-bug-report.md) — Hard-won lessons on deployment debugging

---

## Author Checklist (master)
- [x] All step files created and linked
- [x] Phase-level acceptance criteria are measurable
- [x] PR/merge order documented
- [x] Blocking dependencies (user-provided credentials) explicitly called out
- [x] Service selection rationale documented with alternatives
- [x] Cost estimates provided for all services
- [x] Rollback plan documented for each component
- [x] Required accounts and API keys listed with "where to get" links
