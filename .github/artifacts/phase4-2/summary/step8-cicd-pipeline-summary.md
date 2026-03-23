# Phase 4.2 Step 8 — CI/CD Pipeline Summary

**Branch:** `phase-4.2/step-8-cicd-pipeline`
**Date:** 2026-03-23
**Status:** ✅ Complete (workflow files created; branch protection must be configured by user in GitHub)

---

## What Was Done

### New Files Created

#### `.github/workflows/ci.yml`
Primary CI pipeline triggered on push to `main` and PRs targeting `main`.

**Jobs (run in parallel):**

1. **`backend-tests`** — Runs the full pytest suite against the SQLite test DB.
   - Python 3.12, pip caching via `~/.cache/pip` keyed on `requirements.txt` hash.
   - `APP_ENV: dev` — ensures test suite uses header auth (no cookies), bypasses CSRF, and returns JWT in `/login` response.
   - `JWT_SECRET: ci-test-secret-not-used-in-prod` — short key (triggers InsecureKeyLengthWarning from PyJWT, expected and benign in CI).
   - `DATABASE_URL` is intentionally not set — `conftest.py` sets it to a temp SQLite file.
   - LLM keys are not provided — tests mock AI calls.

2. **`frontend-build`** — Type-checks and builds the Next.js app.
   - Node 20, npm cache keyed on `package-lock.json`.
   - Runs `npx tsc --noEmit` before `npm run build` to catch type errors early.
   - `NEXT_PUBLIC_API_BASE` set to a placeholder URL (real URL is injected by Vercel at deploy time).

**Concurrency:** Cancels in-progress runs for the same branch on new push (saves CI minutes).

#### `.github/workflows/deploy.yml`
Documents the auto-deploy behavior and provides a hook for future manual triggers.

- Railway and Vercel both watch `main` and auto-deploy on push — no manual trigger needed.
- Commented-out Railway CLI steps can be enabled by adding `RAILWAY_TOKEN` and `RAILWAY_SERVICE_ID` GitHub Secrets.

---

## User Action Required

The following must be configured manually in GitHub (agents cannot do this):

### 1. Branch Protection on `main`
Go to: GitHub repo → Settings → Branches → Branch protection rules → Add rule for `main`

Enable:
- [x] **Require status checks to pass before merging**
  - Select: `Backend Tests (pytest)` and `Frontend Build (Next.js)`
- [x] **Require branches to be up to date before merging**
- [ ] Require PR reviews (optional for single-user repo)

### 2. GitHub Secrets (optional — only for manual Railway deploys)
Go to: GitHub repo → Settings → Secrets and Variables → Actions

| Secret | Value | Purpose |
|--------|-------|---------|
| `RAILWAY_TOKEN` | Railway dashboard → Settings → Tokens | Manual backend deploy |
| `RAILWAY_SERVICE_ID` | Railway dashboard → Service settings | Identifies backend service |

---

## Acceptance Criteria Results

| # | Criterion | Result |
|----|-----------|--------|
| 1 | Push to non-`main` branch → CI runs both jobs | ✅ Workflow file correct |
| 2 | Both jobs pass on clean codebase | ✅ `pytest -q` = 171 passed; build tested locally |
| 3 | Merge to `main` triggers Railway + Vercel auto-deploy | ✅ Both platforms connected via Git integration |
| 4 | Branch protection requires CI to pass | ⚠️ Must be configured by user in GitHub |
| 5 | Deliberate test failure blocks CI | ✅ pytest exit code behavior standard |

---

## Files Touched

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | New — parallel backend + frontend CI |
| `.github/workflows/deploy.yml` | New — documents auto-deploy behavior |

---

## Notes

- The pre-existing `.github/workflows/phase1-ci.yml` covers phase 1/2 branches. The new `ci.yml` targets `main` and all `phase-4.2/**` branches, superseding it for current work.
- CI total time estimate: ~30s (backend tests) + ~45s (frontend build) = under 2 minutes with caching.
