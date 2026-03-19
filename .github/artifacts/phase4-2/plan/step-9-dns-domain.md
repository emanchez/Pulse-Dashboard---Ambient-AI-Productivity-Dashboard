# Step 9 — Custom Domain & DNS (Cloudflare)

## Purpose

Configure a custom domain for both the frontend and backend, ensuring a professional URL, unified cookie domain (critical for Step 7's httpOnly cookie auth), and Cloudflare's free CDN/DDoS protection. This step resolves the cross-origin cookie issue where Safari ITP blocks third-party cookies between different platform domains (e.g., `*.vercel.app` → `*.railway.app`).

## 🔴🔴 ABSOLUTE BLOCKERS — User Action Required (ALL Manual)

> **This entire step is 100% user-driven. Agents cannot perform any of these actions.**
>
> 1. **Purchase a domain name** (~$10–15/year from Namecheap, Cloudflare Registrar, Porkbun, etc.)
>    - Recommendation: **Cloudflare Registrar** — at-cost pricing, no markup, already integrated with Cloudflare DNS
>    - Example: `pulseapp.dev`, `mypulse.app`, `pulse-dash.com`
> 2. **Create a free Cloudflare account** at [cloudflare.com](https://cloudflare.com)
> 3. **Add the domain to Cloudflare** — follow the guided setup to change nameservers at your registrar
> 4. **Wait for DNS propagation** (up to 24–48 hours, usually 1–2 hours)
>
> **Do not start implementation until the domain is active in Cloudflare.**

## Deliverables

- Frontend accessible at `https://app.<domain>` (or `https://<domain>`)
- Backend accessible at `https://api.<domain>`
- Both share a parent domain (e.g., `<domain>`) so cookies with `Domain=.<domain>` work on both
- Cloudflare proxy enabled (orange cloud) for CDN + DDoS protection
- SSL/TLS set to "Full (strict)" in Cloudflare

## Recommended Domain Architecture

| Subdomain | Service | Example |
|-----------|---------|---------|
| `app.<domain>` or bare `<domain>` | Frontend (Vercel) | `app.pulseapp.dev` |
| `api.<domain>` | Backend (Railway) | `api.pulseapp.dev` |

This architecture allows a single cookie with `Domain=.pulseapp.dev` to be sent to both `app.pulseapp.dev` and `api.pulseapp.dev`, resolving the Safari ITP cross-origin issue.

## Detailed implementation steps

### 🔴 User Steps (Manual — Cannot Be Automated)

1. **🔴 USER: Purchase domain:**
   - Go to [Cloudflare Registrar](https://dash.cloudflare.com/registrar) (or your registrar of choice)
   - Search for and register a domain ($10–15/year)
   - If using a non-Cloudflare registrar, change nameservers to the ones Cloudflare provides

2. **🔴 USER: Set up Cloudflare:**
   - Add the domain to Cloudflare: [dash.cloudflare.com](https://dash.cloudflare.com) → "Add a site"
   - Select the **Free plan**
   - Follow the nameserver change instructions
   - Wait for "Active" status on the Cloudflare dashboard

3. **🔴 USER: Configure SSL in Cloudflare:**
   - Go to SSL/TLS → Overview → Set to **Full (strict)**
   - Enable "Always Use HTTPS" under SSL/TLS → Edge Certificates
   - Enable "Automatic HTTPS Rewrites"

4. **🔴 USER: Add DNS records in Cloudflare:**

   | Type | Name | Content | Proxy status |
   |------|------|---------|-------------|
   | CNAME | `app` (or `@` for bare domain) | `cname.vercel-dns.com` | Proxied (orange) |
   | CNAME | `api` | `<your-railway-service>.up.railway.app` | DNS only (grey cloud)* |

   > \* Railway requires DNS-only mode (grey cloud) for their TLS certificates. If using orange cloud with Railway, you need to configure Cloudflare's SSL to "Full" and Railway must have valid TLS.

5. **🔴 USER: Configure custom domain in Vercel:**
   - Go to Vercel dashboard → Project → Settings → Domains
   - Add `app.<domain>` (or bare `<domain>`)
   - Vercel will verify DNS ownership (the CNAME record from step 4 handles this)

6. **🔴 USER: Configure custom domain in Railway:**
   - Go to Railway dashboard → Service → Settings → Networking → Custom Domain
   - Add `api.<domain>`
   - Railway will show instructions to add a CNAME record (already done in step 4)

### Agent Steps (After Domain Is Active)

7. **Update backend CORS origins** (`config.py`):
   - Add `https://app.<domain>` (or `https://<domain>`) to the production CORS origins list
   - Remove or keep the `*.vercel.app` origin as a fallback

8. **Update cookie domain** (Step 7 security hardening):
   - Set `Domain=.<domain>` on the `pulse_token` and `csrf_token` cookies so they're shared across `app.<domain>` and `api.<domain>`:
     ```python
     response.set_cookie(
         key="pulse_token",
         value=token,
         httponly=True,
         secure=True,
         samesite="lax",
         domain=f".{settings.cookie_domain}",  # e.g. ".pulseapp.dev"
         max_age=settings.access_token_expire_minutes * 60,
         path="/",
     )
     ```
   - Add `COOKIE_DOMAIN` to backend environment variables on Railway

9. **Update frontend `NEXT_PUBLIC_API_BASE`** on Vercel:
   - Change from `https://<railway-app>.up.railway.app` to `https://api.<domain>`

10. **Verify end-to-end:**
    - Visit `https://app.<domain>` → login → verify cookies → perform CRUD → verify AI features

## Integration & Edge Cases

- **DNS propagation delay:** After adding records, it can take 1–48 hours for the domain to resolve globally. Use [dnschecker.org](https://dnschecker.org) to verify.
- **Vercel redirects:** If using a bare domain (`<domain>`) + `www.<domain>`, configure Vercel to redirect `www` to the bare domain.
- **Railway TLS:** Railway auto-provisions TLS for custom domains. No manual certificate management needed.
- **Cloudflare Cache:** For the API subdomain, caching should be disabled (Railway handles responses). For the frontend, Vercel handles caching, but Cloudflare's CDN provides additional edge caching.

## Acceptance Criteria

1. `https://app.<domain>` loads the frontend (or `https://<domain>` if using bare domain).
2. `https://api.<domain>/health` returns `{"status": "ok"}`.
3. Browser DevTools → Security tab shows a valid SSL certificate for both URLs.
4. `curl -I https://app.<domain>` includes `cf-ray` header (proving Cloudflare proxy is active).
5. Login flow works: cookies are set with correct `Domain` attribute spanning both subdomains.
6. Safari on macOS/iOS can complete a full login → task creation flow (ITP bypass confirmed).

## Testing / QA

### Manual (ALL — no automated tests for DNS/domain)
1. Open `https://app.<domain>` in Chrome, Firefox, Safari → verify page loads.
2. Open `https://api.<domain>/health` → verify JSON response.
3. Login → check cookies in DevTools → verify `Domain=.<domain>` is set.
4. Perform a task CRUD cycle → verify data persists.
5. Test on a mobile device → verify SSL and app functionality.
6. Run `dig app.<domain>` and `dig api.<domain>` → verify DNS resolution.

## Files touched

- [code/backend/app/core/config.py](code/backend/app/core/config.py) — CORS origins, COOKIE_DOMAIN
- Backend environment variables on Railway (COOKIE_DOMAIN)
- Frontend environment variables on Vercel (NEXT_PUBLIC_API_BASE)

## Estimated effort

0.5 dev day (agent work) + 1–2 hours user setup + DNS propagation wait time

## Concurrency & PR strategy

- Branch: `phase-4.2/step-9-dns-domain`
- Blocking steps:
  - `Blocked until: .github/artifacts/phase4-2/plan/step-5-backend-deploy-railway.md`
  - `Blocked until: .github/artifacts/phase4-2/plan/step-6-frontend-deploy-vercel.md`
  - **🔴 Blocked until: User has purchased a domain and set up Cloudflare (100% manual)**
- Merge Readiness: false
- **Can be parallelized with Steps 7 and 8** in terms of code work, but domain must be live for testing

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Domain not yet purchased | Step has absolute blocker. All agent work is gated on domain being active. |
| DNS propagation takes 48 hours | Use Cloudflare (fast propagation, usually <1 hour). Have .railway.app/.vercel.app fallbacks. |
| Railway SSL cert delay | Railway auto-provisions certs. If delayed, use DNS-only mode temporarily. |
| Cookie domain too broad | Use a dedicated domain for this app. Don't share with other services. |

## References

- [Cloudflare Free Plan](https://www.cloudflare.com/plans/free/)
- [Vercel Custom Domains](https://vercel.com/docs/projects/domains)
- [Railway Custom Domains](https://docs.railway.com/guides/public-networking#custom-domains)
- [Step 7 — Security Hardening](step-7-security-hardening.md) — Cookie auth requires shared domain

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
