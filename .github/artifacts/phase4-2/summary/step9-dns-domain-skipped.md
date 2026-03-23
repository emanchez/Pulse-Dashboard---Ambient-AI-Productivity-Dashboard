# Phase 4.2 Step 9 — DNS / Custom Domain (SKIPPED)

**Status:** ⏭️ Skipped by user decision
**Date:** 2026-03-23

## Decision

Step 9 (custom domain setup with Cloudflare DNS) has been intentionally skipped. The application will continue to use platform-provided URLs:

- **Frontend:** `https://pulse-dashboard-ambient-ai.vercel.app`
- **Backend:** `https://pulse-dashboard-ambient-ai-productivity-dashbo-production.up.railway.app`

## Impact on Step 10

Step 9 is marked **optional** in the Phase 4.2 master plan. Step 10 (production smoke test) is unblocked:

- All smoke test items that reference `https://api.<domain>` or `https://app.<domain>` should be substituted with the platform URLs above.
- HSTS and HTTPS enforcement are active regardless (Railway and Vercel enforce TLS on their platform URLs).
- CORS is scoped to the Vercel URL (`FRONTEND_CORS_ORIGINS=https://pulse-dashboard-ambient-ai.vercel.app`).

## Safari / ITP Warning

Using separate-domain URLs (`*.vercel.app` and `*.railway.app` are different eTLD+1 domains) means Safari's Intelligent Tracking Prevention (ITP) **may block** cross-domain httpOnly cookies. This is the risk documented in the step-7 plan under Safari ITP.

**Mitigation:** If Safari cookie auth fails, the backend's Bearer header fallback in `get_current_user` allows the app to function in dev mode. For future production Safari support, registering a custom domain (shared parent domain for both frontend and backend) resolves ITP.

## Future Action

If a custom domain is purchased in the future, follow [step-9-dns-domain.md](../plan/step-9-dns-domain.md) to configure Cloudflare DNS and update:
1. `FRONTEND_CORS_ORIGINS` in Railway environment variables
2. `NEXT_PUBLIC_API_BASE` in Vercel environment variables
3. Backend `Set-Cookie` domain attribute if needed
