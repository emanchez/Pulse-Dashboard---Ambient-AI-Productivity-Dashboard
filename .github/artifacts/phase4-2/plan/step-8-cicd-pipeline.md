# Step 8 — CI/CD Pipeline (GitHub Actions)

## Purpose

Set up a GitHub Actions CI/CD pipeline that runs the test suite on every push/PR and automatically deploys to Railway (backend) and Vercel (frontend) on merge to `main`. This ensures no broken code reaches production and codifies the deployment process.

## 🔴 ABSOLUTE BLOCKERS — User Action Required

> **This step cannot begin until the user has:**
> 1. A **GitHub repository** with the project code pushed
> 2. **Railway** and **Vercel** deployments working (Steps 5–6 complete)
> 3. **Railway API token** — available from Railway dashboard (Settings → Tokens)
> 4. **Vercel token** (optional — Vercel's Git integration auto-deploys; token is for advanced workflows)
>
> **Agents cannot create GitHub repos or generate platform tokens.**

## Deliverables

- `.github/workflows/ci.yml` — runs `pytest` and `npm run build` on every push/PR
- `.github/workflows/deploy.yml` — triggers deployment on merge to `main` (optional if platforms auto-deploy from Git)
- GitHub branch protection rules for `main` (require CI to pass before merge)
- Documentation of the CI/CD flow

## Primary files to change

- [.github/workflows/ci.yml](.github/workflows/ci.yml) (new)
- [.github/workflows/deploy.yml](.github/workflows/deploy.yml) (new, optional)

## Detailed implementation steps

1. **Create CI workflow** (`.github/workflows/ci.yml`):
   ```yaml
   name: CI

   on:
     push:
       branches: [main]
     pull_request:
       branches: [main]

   jobs:
     backend-tests:
       runs-on: ubuntu-latest
       defaults:
         run:
           working-directory: code/backend

       steps:
         - uses: actions/checkout@v4

         - name: Set up Python 3.11
           uses: actions/setup-python@v5
           with:
             python-version: "3.11"

         - name: Cache pip packages
           uses: actions/cache@v4
           with:
             path: ~/.cache/pip
             key: ${{ runner.os }}-pip-${{ hashFiles('code/backend/requirements.txt') }}

         - name: Install dependencies
           run: pip install -r requirements.txt

         - name: Run tests
           run: python -m pytest -q --tb=short
           env:
             APP_ENV: dev
             DATABASE_URL: "sqlite+aiosqlite:///./data/test-ci.db"
             JWT_SECRET: "ci-test-secret"

     frontend-build:
       runs-on: ubuntu-latest
       defaults:
         run:
           working-directory: code/frontend

       steps:
         - uses: actions/checkout@v4

         - name: Set up Node.js 20
           uses: actions/setup-node@v4
           with:
             node-version: "20"
             cache: "npm"
             cache-dependency-path: code/frontend/package-lock.json

         - name: Install dependencies
           run: npm ci

         - name: Type check
           run: npx tsc --noEmit

         - name: Build
           run: npm run build
           env:
             NEXT_PUBLIC_API_BASE: "https://placeholder.example.com"
   ```

2. **Create deployment workflow** (`.github/workflows/deploy.yml`):
   > **Note:** Both Railway and Vercel support auto-deploy from Git. If auto-deploy is enabled on both platforms, this file is optional. Create it only if manual deploy triggers are needed.

   ```yaml
   name: Deploy

   on:
     push:
       branches: [main]

   # Only run if CI passes (GitHub will block merge if CI fails with branch protection)
   jobs:
     deploy-backend:
       runs-on: ubuntu-latest
       if: github.ref == 'refs/heads/main'
       needs: []  # Railway auto-deploys from Git; this job is a backup

       steps:
         - uses: actions/checkout@v4
         - name: Deploy to Railway
           run: echo "Railway auto-deploys from Git integration. No manual action needed."
           # If manual deploy is needed:
           # uses: bervProject/railway-deploy@main
           # with:
           #   railway_token: ${{ secrets.RAILWAY_TOKEN }}
           #   service: ${{ secrets.RAILWAY_SERVICE_ID }}

     deploy-frontend:
       runs-on: ubuntu-latest
       if: github.ref == 'refs/heads/main'

       steps:
         - name: Deploy to Vercel
           run: echo "Vercel auto-deploys from Git integration. No manual action needed."
           # Vercel's Git integration handles this automatically
   ```

3. **🔴 USER: Set up GitHub Secrets:**
   In the GitHub repo → Settings → Secrets and Variables → Actions:

   | Secret | Value | Purpose |
   |--------|-------|---------|
   | `RAILWAY_TOKEN` | From Railway dashboard | Backend deployment (if manual deploy is used) |
   | `RAILWAY_SERVICE_ID` | From Railway dashboard | Identifies the backend service |

   > If using auto-deploy from Git (recommended), these secrets are optional.

4. **🔴 USER: Enable branch protection on `main`:**
   - Go to GitHub repo → Settings → Branches → Branch protection rules
   - Add rule for `main`:
     - [x] Require status checks to pass before merging
     - Select: `backend-tests` and `frontend-build` from the CI workflow
     - [x] Require branches to be up to date before merging
     - [x] Require pull request reviews before merging (optional for single-user)

5. **Add a CI status badge to the README** (optional):
   ```markdown
   ![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg)
   ```

## Integration & Edge Cases

- **Test database:** CI uses a throwaway SQLite database (`test-ci.db`) — not the production Neon database. Never connect CI to production.
- **Environment variables:** `NEXT_PUBLIC_API_BASE` in CI is set to a placeholder URL since the build doesn't need a running backend. It's baked in at build time, so the real value is set in Vercel's environment.
- **Parallel jobs:** `backend-tests` and `frontend-build` run in parallel (no dependencies between them). This halves CI time.
- **Railway auto-deploy:** Railway watches the connected Git branch and auto-deploys on push. No GitHub Actions integration is strictly needed for deployment. The CI workflow ensures tests pass before merge, and branch protection prevents broken code from reaching `main`.
- **Vercel auto-deploy:** Same as Railway — Vercel watches `main` and auto-deploys. Preview deployments happen on PRs.

## Acceptance Criteria

1. Push to a non-`main` branch and open a PR → CI runs both `backend-tests` and `frontend-build` jobs.
2. Both jobs pass on a clean codebase.
3. Merge to `main` triggers auto-deploy on Railway (backend) and Vercel (frontend).
4. Branch protection on `main` requires CI to pass before merge (user-configured).
5. A deliberately broken test (e.g. `assert False`) fails the CI and blocks the PR merge.

## Testing / QA

### Automated
- Push a test commit to a feature branch and verify CI runs in the Actions tab.
- Introduce a deliberate test failure, push, and verify the CI job fails.

### Manual
1. Open the GitHub Actions tab → verify `CI` workflow is visible.
2. Open a PR → verify both jobs run and report status.
3. Merge a green PR → verify Railway and Vercel auto-deploy.
4. Check the deployed backend `/health` endpoint after deploy.

## Files touched

- [.github/workflows/ci.yml](.github/workflows/ci.yml) (new)
- [.github/workflows/deploy.yml](.github/workflows/deploy.yml) (new, optional)

## Estimated effort

0.5 dev day

## Concurrency & PR strategy

- Branch: `phase-4.2/step-8-cicd-pipeline`
- Blocking steps:
  - `Blocked until: .github/artifacts/phase4-2/plan/step-5-backend-deploy-railway.md`
  - `Blocked until: .github/artifacts/phase4-2/plan/step-6-frontend-deploy-vercel.md`
  - **🔴 Blocked until: GitHub repo exists and platforms are connected**
- Merge Readiness: false
- **Can be parallelized with Step 7** (no code conflicts)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| CI flaky tests | Test suite is reliable after Phase 4.1 Step 9 fixes. WAL checkpoints and session-scoped auth prevent flakes. |
| CI takes too long | Backend tests ~15s, frontend build ~30s. With caching, total CI time is under 2 minutes. |
| Secrets leaked in logs | GitHub Actions masks secrets automatically. Never `echo` secret values. |
| Auto-deploy races with CI | Branch protection ensures CI passes before merge to `main`. Auto-deploy only triggers on `main` push. |

## References

- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [Railway Git integration](https://docs.railway.com/develop/deployments)
- [Vercel Git integration](https://vercel.com/docs/deployments/git)
- [code/backend/tests/conftest.py](code/backend/tests/conftest.py) — Test infrastructure

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
