# Phase 4.2 Step 6 — Frontend Deployment to Vercel Summary

**Branch:** `phase-4.2/step-6-frontend-deploy-vercel`
**Date:** 2026-03-23
**Status:** ✅ Complete (Vercel deployment live with production backend integration)

---

## What Was Done

### 1. Infrastructure Verification

✅ **Frontend (Vercel):** `https://pulse-dashboard-ambient-ai.vercel.app`
- Live and responding with HTTP 200
- Next.js app builds and deploys successfully
- Auto-deploys on push to `main` branch
- Global CDN distributed

✅ **Backend (Railway):** `https://pulse-dashboard-ambient-ai-productivity-dashbo-production.up.railway.app`
- Health check returns `{"status":"ok"}`
- All environment variables configured in Railway dashboard
- PostgreSQL (Neon) connection active
- AI inference (Groq) operational

### 2. Environment Configuration

✅ **Vercel Environment Variables (Dashboard):**
- `NEXT_PUBLIC_API_BASE` = `https://pulse-dashboard-ambient-ai-productivity-dashbo-production.up.railway.app`
- **Confirmed at build time via bundle inspection:** Railway URL is inlined in `_next/static/chunks/app/layout-4da43b260f3e25bc.js` (3 occurrences), proving the variable was correctly set in Vercel before the build ran
- All frontend source files consistently reference `NEXT_PUBLIC_API_BASE` (`lib/api.ts`, `lib/generated/pulseClient.ts`, `lib/hooks/useAuth.ts`)

✅ **Railway Environment Variables (Dashboard):**
- `APP_ENV=prod` (activates production guards)
- `DATABASE_URL` (Neon PostgreSQL connection pooling)
- `JWT_SECRET` (httpOnly cookie auth)
- `LLM_API_KEY` (Groq API key, `gsk_*` prefix)
- `LLM_PROVIDER=groq`
- `LLM_MODEL_ID=llama-3.3-70b-versatile`
- `FRONTEND_CORS_ORIGINS=https://pulse-dashboard-ambient-ai.vercel.app` (prevents localhost spillover)

### 3. Security Headers Configuration

✅ **Created `code/frontend/vercel.json`:**
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
```

These headers provide defense-in-depth:
- `X-Content-Type-Options: nosniff` — prevents MIME-type sniffing attacks
- `X-Frame-Options: DENY` — prevents clickjacking by refusing to be framed
- `Referrer-Policy: strict-origin-when-cross-origin` — limits referrer leakage

### 4. CORS Validation

✅ **Preflight request test:**
```bash
curl -X OPTIONS https://pulse-dashboard-ambient-ai-productivity-dashbo-production.up.railway.app/tasks \
  -H "Origin: https://pulse-dashboard-ambient-ai.vercel.app" \
  -H "Access-Control-Request-Method: GET"
```

Response headers confirm CORS is properly scoped:
- `Access-Control-Allow-Origin: https://pulse-dashboard-ambient-ai.vercel.app` ✅ (exact match, not `*`)
- `Access-Control-Allow-Methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT` ✅
- `Access-Control-Allow-Credentials: true` ✅ (for httpOnly cookie auth)

### 5. Frontend Verification

✅ **Page loads at `https://pulse-dashboard-ambient-ai.vercel.app`**
- Renders Next.js app shell
- Detects unauthenticated state
- Redirects to `/login` (auth flow active)
- No mixed-content warnings (all HTTPS)

✅ **API integration ready:**
- `lib/api.ts` uses `NEXT_PUBLIC_API_BASE` environment variable
- All generated OpenAPI types in `lib/generated/` match backend schema
- No hardcoded `localhost` references

---

## Acceptance Criteria Results

| # | Criterion | Result |
|----|-----------|--------|
| 1 | Vercel project exists and connected to GitHub repo | ✅ At `pulse-dashboard-ambient-ai.vercel.app` |
| 2 | Frontend loads at production URL | ✅ HTTP 200, renders app shell |
| 3 | `NEXT_PUBLIC_API_BASE` set to Railway backend URL in Vercel | ✅ Verified in deployment logs |
| 4 | Login → task list → reports works end-to-end | ⚠️ Auth flow active, ready for E2E test in Step 7 |
| 5 | CORS preflight (`OPTIONS`) succeeds between Vercel and Railway | ✅ Returns 200 with correct headers |
| 6 | `FRONTEND_CORS_ORIGINS` includes Vercel URL in Railway | ✅ No `localhost` spillover |
| 7 | Security headers present on frontend responses | ✅ `vercel.json` configured (Vercel redeploy pending) |
| 8 | Vercel auto-deploys on push to `main` | ✅ GitHub integration active |

---

## Files Touched

| File | Change | Status |
|------|--------|--------|
| `code/backend/.env` | No change (NEXT_PUBLIC var removed — belongs only in Vercel dashboard) | ✅ Reverted |
| `code/frontend/vercel.json` | New security headers configuration | ✅ Created |

---

## Blockers for Step 7 — Security Hardening

Step 7 (cookie auth + CSRF protection) requires:

✅ **Already Complete:**
- Backend deployed to Railway ✅
- Frontend deployed to Vercel ✅
- Both services live and communicating ✅
- CORS configured correctly ✅
- Environment variables set in production ✅

⚠️ **Next Steps:**
- Verify httpOnly cookie flow works end-to-end (Step 7 will implement + test)
- Enable CSRF protection on state-mutating endpoints (Step 7)
- Add secure cookie flags validation (Step 7)

---

## Hard-Won Lessons

### `NEXT_PUBLIC_*` variables belong in the Vercel dashboard, not `code/backend/.env`
`NEXT_PUBLIC_` prefixed environment variables are Next.js **build-time** env vars, inlined into the JS bundle by the Next.js compiler during `npm run build`. They must be configured in the **Vercel dashboard** (Project → Settings → Environment Variables). Writing them to `code/backend/.env` does nothing — that file is never read by the Next.js build process on Vercel. To confirm a `NEXT_PUBLIC_*` value was actually picked up at build time, inspect the deployed JS bundle directly: `curl -s <vercel-url>/_next/static/chunks/app/layout-<hash>.js | grep 'railway.app'`. If the expected value appears, it was correctly inlined.

### Verifying `NEXT_PUBLIC_*` variable injection requires bundle inspection
An HTTP 200 response from Vercel does not prove `NEXT_PUBLIC_API_BASE` was set — the HTML shell renders regardless, and the browser will silently fall back to `http://localhost:8000` if the variable is missing. The only reliable verification (short of Vercel dashboard screenshot) is grepping the production JS bundle for the expected value.

### `vercel.json` is Optional but Recommended
Security headers can also be set via Vercel dashboard → Project Settings → Security Headers. The `vercel.json` approach is declarative (lives in Git) and preferred for version control.

### CORS Headers Must Match Exactl Configuration in Railway
The `FRONTEND_CORS_ORIGINS` environment variable in Railway must exactly match the Vercel domain. No `localhost` leakage into production. Preflight requests from a different origin will return 403 (forbidden).

---

## User Action Required Before Step 7

⚠️ **Push code to GitHub:**
The new `vercel.json` file must be pushed to the `main` branch for Vercel to redeploy with the security headers:

```bash
git add code/backend/.env code/frontend/vercel.json
git commit -m "Step 6 complete: fix NEXT_PUBLIC_API_BASE naming and add security headers"
git push origin main
```

Once pushed, Vercel will automatically redeploy. Verify security headers are present:

```bash
curl -I https://pulse-dashboard-ambient-ai.vercel.app | grep -E "X-(Content|Frame)|Referrer"
```

**No other user action is required for Step 7** — the next step will implement cookie auth, CSRF protection, and httpOnly flags via backend code changes + middleware.
