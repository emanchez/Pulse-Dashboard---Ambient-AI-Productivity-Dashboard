# Step 10 — Production Smoke Test & Go-Live Checklist

## Purpose

Execute a comprehensive end-to-end verification of the production deployment. This is the final gate before the app is considered "live." Every feature is tested against the production stack (Vercel → Railway → Neon) to confirm the deployment is correctly wired.

## Deliverables

- A completed smoke test checklist (this document) with pass/fail status on every item
- Documented performance baseline (initial response times)
- Rollback procedure documented and verified
- "Go-Live" status confirmed or issues documented

## Pre-Conditions

All previous steps must be complete before running this checklist:

| Step | Status | Required |
|------|--------|----------|
| Step 1 — Alembic Init | ✅ | Yes |
| Step 2 — Schema Hardening | ✅ | Yes |
| Step 3 — Neon Provision & Migrate | ✅ | Yes |
| Step 4 — asyncpg Switchover | ✅ | Yes |
| Step 5 — Backend Deploy (Railway) | ✅ | Yes |
| Step 6 — Frontend Deploy (Vercel) | ✅ | Yes |
| Step 7 — Security Hardening | ✅ | Yes |
| Step 8 — CI/CD Pipeline | ✅ | Yes |
| Step 9 — Custom Domain | ⚠️ | Optional (can use platform URLs) |

## Smoke Test Checklist

### 1. Infrastructure Health

| # | Test | Expected | Status |
|---|------|----------|--------|
| 1.1 | `curl https://api.<domain>/health` | `{"status": "ok"}` with 200 | ☐ |
| 1.2 | `curl -I https://api.<domain>/health` → check `x-process-time` header | < 500ms | ☐ |
| 1.3 | Open `https://app.<domain>` in browser | Frontend loads, no console errors | ☐ |
| 1.4 | Check Neon dashboard → connection count | > 0 active connections | ☐ |
| 1.5 | Check Railway logs → no startup errors | Clean startup log | ☐ |
| 1.6 | Check Vercel deployment → build succeeded | Green deployment status | ☐ |

### 2. Authentication Flow

| # | Test | Expected | Status |
|---|------|----------|--------|
| 2.1 | Open login page → submit valid credentials | Redirect to dashboard | ☐ |
| 2.2 | Check cookies → `pulse_token` | httpOnly, Secure, SameSite=Lax | ☐ |
| 2.3 | Check cookies → `csrf_token` | Present, NOT httpOnly (readable by JS) | ☐ |
| 2.4 | Refresh page → still authenticated | Dashboard loads, no re-login | ☐ |
| 2.5 | Click Logout → verify cookie cleared | Redirect to login page | ☐ |
| 2.6 | Access protected route without auth | Redirect to login (not 401 JSON) | ☐ |
| 2.7 | Submit invalid credentials | Error message, no crash | ☐ |

### 3. Task CRUD

| # | Test | Expected | Status |
|---|------|----------|--------|
| 3.1 | Create a new task | Task appears in task list | ☐ |
| 3.2 | Edit task title | Title updates, action log created | ☐ |
| 3.3 | Toggle task status | Status changes, persists on refresh | ☐ |
| 3.4 | Delete a task | Task removed from list | ☐ |
| 3.5 | Refresh after all operations | All changes persisted (Neon) | ☐ |

### 4. Session Logging

| # | Test | Expected | Status |
|---|------|----------|--------|
| 4.1 | Start a focus session | Timer starts, session logged | ☐ |
| 4.2 | End the session | Duration recorded, appears in log | ☐ |

### 5. Reports

| # | Test | Expected | Status |
|---|------|----------|--------|
| 5.1 | Create a manual report | Report saved successfully | ☐ |
| 5.2 | View report list | Report appears with correct date | ☐ |

### 6. AI / Synthesis Features

| # | Test | Expected | Status |
|---|------|----------|--------|
| 6.1 | Trigger AI synthesis (if OZ is configured) | Returns a synthesis report or graceful error | ☐ |
| 6.2 | AI rate limiter works | Rapid requests are throttled with 429 | ☐ |
| 6.3 | AI feature with mock mode | Returns mock response (if OZ not configured) | ☐ |

### 7. System State

| # | Test | Expected | Status |
|---|------|----------|--------|
| 7.1 | View current system state | State displayed correctly | ☐ |
| 7.2 | Update system state | Change persists on refresh | ☐ |

### 8. Mobile Responsiveness

| # | Test | Expected | Status |
|---|------|----------|--------|
| 8.1 | Open on iPhone Safari | Layout renders correctly (bento grid collapses) | ☐ |
| 8.2 | Open on Android Chrome | Same as above | ☐ |
| 8.3 | Login flow on mobile | Works end-to-end | ☐ |
| 8.4 | Cookie auth on Safari (ITP check) | Auth persists across navigation | ☐ |

### 9. Security Checks

| # | Test | Expected | Status |
|---|------|----------|--------|
| 9.1 | `curl -X POST https://api.<domain>/tasks -H "Content-Type: application/json"` (no auth) | 401 Unauthorized | ☐ |
| 9.2 | `curl -X POST https://api.<domain>/tasks -b "pulse_token=..."` (no CSRF token) | 403 CSRF validation failed | ☐ |
| 9.3 | Check response headers for `Strict-Transport-Security` | Present with `max-age=63072000` | ☐ |
| 9.4 | Check response headers for `X-Content-Type-Options` | `nosniff` | ☐ |
| 9.5 | Try accessing `http://` (non-HTTPS) | Redirected to `https://` | ☐ |
| 9.6 | Rate limit test: 6 rapid login attempts | 5th or 6th returns 429 | ☐ |

### 10. Performance Baseline

| # | Metric | Target | Actual | Status |
|---|--------|--------|--------|--------|
| 10.1 | `/health` response time | < 200ms | ___ ms | ☐ |
| 10.2 | `/tasks` (10 tasks) response time | < 500ms | ___ ms | ☐ |
| 10.3 | Frontend initial load (Lighthouse) | Performance > 80 | ___ | ☐ |
| 10.4 | Frontend Time to Interactive | < 3s | ___ s | ☐ |

## Rollback Procedure

If critical issues are found during the smoke test:

### Backend Rollback (Railway)
1. Go to Railway dashboard → Deployments
2. Click on the previous working deployment → "Redeploy"
3. Railway rolls back instantly

### Frontend Rollback (Vercel)
1. Go to Vercel dashboard → Deployments
2. Click on the previous working deployment → "Promote to Production"
3. Vercel rolls back instantly

### Database Rollback (Neon)
1. Neon supports point-in-time recovery on the paid plan
2. On the free plan: Alembic `downgrade -1` reverts the last migration
3. If data migration was the issue, re-run from the SQLite backup (Step 3 created a backup)

### Emergency: Full Revert to Local Dev
1. Stop Railway and Vercel deployments (set to manual deploy)
2. Switch `backend/.env` back to SQLite URL
3. Run locally with `make dev`

## Go-Live Decision Matrix

| Condition | Status | Go-Live? |
|-----------|--------|----------|
| All infrastructure health checks pass | ☐ | Required |
| Auth flow works end-to-end | ☐ | Required |
| Task CRUD works | ☐ | Required |
| CSRF protection active | ☐ | Required |
| HSTS enabled | ☐ | Required |
| AI features work OR graceful degradation | ☐ | Required (either) |
| Mobile responsive | ☐ | Required |
| Custom domain configured | ☐ | Optional |
| CI/CD pipeline running | ☐ | Required |
| Performance within targets | ☐ | Recommended |

**Go-Live = ALL "Required" items pass.**

## Post-Launch Monitoring (First 48 Hours)

1. Check Railway logs every 12 hours for errors
2. Monitor Neon dashboard for connection exhaustion
3. Check Vercel analytics for build failures
4. Test the auth flow once daily (cookie expiry/refresh)
5. Monitor free tier usage:
   - Neon: 0.5 GB storage, 100 compute-hours/month
   - Railway: $5 credit (~500 hours at minimum resources)
   - Vercel: 100 GB bandwidth/month

## Files touched

None — this is a verification document.

## Estimated effort

0.5 dev day for full smoke test execution

## Concurrency & PR strategy

- Branch: `phase-4.2/step-10-prod-smoke-test`
- Blocking steps:
  - `Blocked until: ALL previous steps (1–8) are complete and deployed`
  - Step 9 is optional but recommended
- Merge Readiness: false
- This step is SEQUENTIAL — it runs last

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Smoke test reveals critical issue | Rollback procedures documented above. Each issue feeds back to the relevant step. |
| Free tier limits hit during testing | Monitor usage dashboards. Neon and Railway free tiers are generous for single-user apps. |
| OZ AI service not accessible from Railway | Verify OZ API is reachable from Railway's network. If not, document and use mock mode. |
| DNS not propagated yet | Use platform URLs (*.railway.app, *.vercel.app) for smoke test. Retest after DNS propagates. |

## References

- [Step 5 — Backend Deploy](step-5-backend-deploy-railway.md) — Railway rollback
- [Step 6 — Frontend Deploy](step-6-frontend-deploy-vercel.md) — Vercel rollback
- [Step 3 — Neon Provision](step-3-neon-provision-migrate.md) — Database backup
- [Step 7 — Security Hardening](step-7-security-hardening.md) — Cookie auth tests

## Author Checklist (must complete before PR)
- [ ] All smoke test items executed
- [ ] Performance baseline recorded
- [ ] Rollback procedure verified (at least one test rollback)
- [ ] Go-Live decision documented
- [ ] Post-launch monitoring plan communicated
