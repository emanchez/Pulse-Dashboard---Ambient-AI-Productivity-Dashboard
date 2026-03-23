# Step 6 — Deploy Frontend to Vercel

## Purpose

Deploy the Next.js frontend to Vercel with the production backend URL configured as `NEXT_PUBLIC_API_BASE`. This makes the frontend accessible at a public URL with automatic SSL, CDN, and CI/CD from Git.

## 🔴 ABSOLUTE BLOCKERS — User Action Required

> **This step cannot begin until the user has:**
> 1. Created a **Vercel account** at [vercel.com/signup](https://vercel.com/signup) (free Hobby plan)
> 2. **Step 5 is complete** — the backend is live at `https://<app>.up.railway.app` and `/health` returns 200
> 3. The codebase is pushed to a **GitHub repository**
>
> **Agents cannot create Vercel accounts or push code to Git.**

## Deliverables

- Vercel project connected to the GitHub repo
- `NEXT_PUBLIC_API_BASE` environment variable set to the production backend URL
- Frontend accessible at `https://<project>.vercel.app`
- Auto-deploy on push to `main` branch
- Preview deployments on pull requests
- `FRONTEND_CORS_ORIGINS` updated in Railway backend to include the Vercel URL

## Primary files to change

- [code/frontend/next.config.js](code/frontend/next.config.js) (may need output config for Vercel)
- [code/frontend/vercel.json](code/frontend/vercel.json) (new, optional)

## Detailed implementation steps

1. **🔴 USER: Connect Vercel to GitHub repo:**
   - Go to [vercel.com/new](https://vercel.com/new)
   - Import the GitHub repository
   - Vercel auto-detects Next.js projects

2. **Configure Vercel project settings (dashboard):**
   - **Framework Preset:** Next.js (auto-detected)
   - **Root Directory:** `code/frontend` (critical — the Next.js project is in a subdirectory)
   - **Build Command:** `npm run build` (default)
   - **Output Directory:** `.next` (default for Next.js)
   - **Install Command:** `npm ci` (default)
   - **Node.js Version:** 20.x (matches `package.json` engines `>=20 <21`)

3. **🔴 USER: Set environment variables in Vercel dashboard:**

   | Variable | Value | Environment |
   |----------|-------|-------------|
   | `NEXT_PUBLIC_API_BASE` | `https://<app>.up.railway.app` | Production, Preview, Development |

   > `NEXT_PUBLIC_` prefix is required for Next.js to expose this at build time to the browser.

4. **Create optional `vercel.json`** for explicit configuration:
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
   This adds security headers that complement the backend's CORS configuration.

5. **🔴 USER: Update backend CORS after getting Vercel URL:**
   Once the first deploy completes, Vercel assigns a URL (e.g. `https://pulse-dash.vercel.app`).
   - Go to Railway dashboard → Backend service → Variables
   - Update `FRONTEND_CORS_ORIGINS` to: `https://pulse-dash.vercel.app`
   - Redeploy the backend (Railway auto-redeploys on variable change)

6. **Verify the full stack:**
   ```bash
   # Frontend loads
   curl -s -o /dev/null -w "%{http_code}" https://<project>.vercel.app
   # Expected: 200

   # Frontend can reach backend (CORS test)
   curl -s -I -X OPTIONS https://<backend>.up.railway.app/tasks \
     -H "Origin: https://<project>.vercel.app" \
     -H "Access-Control-Request-Method: GET"
   # Expected: Access-Control-Allow-Origin: https://<project>.vercel.app
   ```

7. **Test login flow end-to-end:**
   - Open `https://<project>.vercel.app` in a browser
   - Should redirect to `/login`
   - Login with `devuser` credentials
   - Should see tasks, reports, synthesis pages with data from the Neon database

## Integration & Edge Cases

- **`NEXT_PUBLIC_` prefix:** Environment variables without this prefix are only available server-side. Since `api.ts` runs in the browser, the variable must be `NEXT_PUBLIC_API_BASE`.
- **Preview deployments:** Vercel creates preview URLs for every PR. These will use the same `NEXT_PUBLIC_API_BASE` (pointing to production backend). For true preview environments, you'd need a separate backend — out of scope for now.
- **Build cache:** Vercel caches `node_modules` and `.next` build artifacts. If the build fails due to stale cache, clear it in the Vercel dashboard (Settings → General → Build Cache).
- **Static generation:** Pages using `generateStaticParams` or `getStaticProps` are pre-rendered at build time. Since all pages in this app use client-side data fetching (not SSG), this is not an issue.
- **Vercel serverless functions:** Not used — the app is a pure SPA that calls the separate FastAPI backend. No API routes in Next.js.
- **Hobby plan limits:** 100 GB bandwidth/month, 6000 build minutes/month. More than sufficient for a single-user app.

## Acceptance Criteria

1. 🔴 Vercel project exists and is connected to the GitHub repo (user-verified).
2. `https://<project>.vercel.app` loads the Pulse Dashboard login page.
3. `NEXT_PUBLIC_API_BASE` is set to the Railway backend URL in Vercel.
4. Login → task list → report creation works end-to-end in the browser.
5. CORS preflight (`OPTIONS`) request from the Vercel URL to the Railway backend succeeds.
6. `FRONTEND_CORS_ORIGINS` in Railway includes the Vercel URL.
7. Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) are present on frontend responses.
8. Vercel auto-deploys on push to `main`.

## Testing / QA

### Automated
```bash
# Pre-deploy: ensure build succeeds locally
cd code/frontend
NEXT_PUBLIC_API_BASE=https://<backend>.up.railway.app npm run build
```

### Manual
1. Open `https://<project>.vercel.app` — login page should load.
2. Login with valid credentials — should see dashboard with tasks.
3. Navigate to Reports → create a report → verify it saves.
4. Navigate to Synthesis → trigger synthesis → verify AI response.
5. Open browser DevTools → Network tab → verify all API calls go to the Railway backend URL.
6. Check no mixed-content warnings (all HTTPS).
7. Check response headers for `X-Content-Type-Options: nosniff`.

## Files touched

- [code/frontend/vercel.json](code/frontend/vercel.json) (new, optional)
- [code/frontend/next.config.js](code/frontend/next.config.js) (may need minor update)

## Estimated effort

0.5 dev day (excluding user account setup)

## Concurrency & PR strategy

- Branch: `phase-4.2/step-6-frontend-deploy-vercel`
- Blocking steps:
  - `Blocked until: .github/artifacts/phase4-2/plan/step-5-backend-deploy-railway.md`
  - **🔴 Blocked until: Vercel account created by user**
  - **🔴 Blocked until: Production backend URL available from Step 5**
- Merge Readiness: true

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Vercel build fails due to TypeScript errors | `npm run build` passes locally (verified in Phase 4.1 Step 7). Run build before pushing. |
| CORS blocks frontend→backend after deploy | Update `FRONTEND_CORS_ORIGINS` in Railway immediately after getting the Vercel URL. |
| `NEXT_PUBLIC_API_BASE` not set at build time | Vercel dashboard clearly shows env vars. Verify in the build logs that the variable is used. |
| Mixed content (HTTP backend + HTTPS frontend) | Backend is on Railway HTTPS (automatic). No HTTP→HTTPS mismatch. |

## References

- [Vercel Next.js deployment docs](https://vercel.com/docs/frameworks/nextjs)
- [Vercel environment variables](https://vercel.com/docs/projects/environment-variables)
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts) — `NEXT_PUBLIC_API_BASE` usage
- [code/frontend/next.config.js](code/frontend/next.config.js) — Current Next.js config

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
