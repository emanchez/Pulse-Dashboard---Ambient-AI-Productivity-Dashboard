# Step 7 — Security Hardening (Cookie Auth, CSRF, HTTPS Enforcement)

## Purpose

Migrate JWT storage from `localStorage` to `httpOnly` cookies, add CSRF protection, enforce HTTPS-only access, and tighten production rate limits. These are the security items flagged as deployment-blocking in the MVP Final Audit (S-2, S-3, S-8) and are required before the app handles real user data in production.

## Deliverables

- Backend: `/login` sets an `httpOnly`, `Secure`, `SameSite=Lax` cookie instead of returning a JSON token
- Backend: `/logout` endpoint that clears the auth cookie
- Backend: `get_current_user()` reads the JWT from the cookie (production) or `Authorization` header (dev fallback)
- Backend: CSRF protection using double-submit cookie pattern on all state-mutating endpoints (POST/PUT/PATCH/DELETE)
- Backend: HSTS header (`Strict-Transport-Security`) added in production
- Frontend: Remove `localStorage` token storage; use `credentials: "include"` on all fetch calls
- Frontend: Include CSRF token in mutating requests
- Dual-mode support: Cookie auth in production, `Authorization` header in dev (preserves `make dev` workflow and test suite)

## Primary files to change

- [code/backend/app/api/auth.py](code/backend/app/api/auth.py) — Set-Cookie on login, clear on logout
- [code/backend/app/core/security.py](code/backend/app/core/security.py) — Read JWT from cookie or header
- [code/backend/app/main.py](code/backend/app/main.py) — CSRF middleware, HSTS middleware
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts) — `credentials: "include"`, remove localStorage
- [code/frontend/lib/hooks/useAuth.ts](code/frontend/lib/hooks/useAuth.ts) — Remove localStorage read/write
- [code/frontend/app/login/page.tsx](code/frontend/app/login/page.tsx) — Handle cookie-based login response

## Detailed implementation steps

### Backend Changes

1. **Update `/login` endpoint** (`auth.py`):
   - In production (`APP_ENV=prod`): set an `httpOnly` cookie containing the JWT instead of returning it in the response body:
     ```python
     response = JSONResponse(content={"message": "Login successful", "username": user.username})
     if settings.app_env != "dev":
         response.set_cookie(
             key="pulse_token",
             value=token,
             httponly=True,
             secure=True,           # HTTPS only
             samesite="lax",        # Prevents CSRF on cross-site GET but allows same-site navigation
             max_age=settings.access_token_expire_minutes * 60,
             path="/",
         )
     else:
         # Dev mode: return token in body for localStorage (preserves current dev workflow)
         response = JSONResponse(content={"access_token": token, "token_type": "bearer"})
     ```

2. **Add `/logout` endpoint** (`auth.py`):
   ```python
   @router.post("/logout")
   async def logout(response: Response):
       response.delete_cookie("pulse_token", path="/")
       return {"message": "Logged out"}
   ```

3. **Update `get_current_user()`** (`security.py` or a new dependency):
   - First, try to read `pulse_token` from cookies.
   - If not present, fall back to `Authorization: Bearer <token>` header.
   - This dual-mode approach allows dev (header) and prod (cookie) to coexist:
     ```python
     async def get_current_user(request: Request, session: AsyncSession = Depends(get_async_session)):
         token = request.cookies.get("pulse_token")
         if not token:
             auth_header = request.headers.get("Authorization", "")
             if auth_header.startswith("Bearer "):
                 token = auth_header[7:]
         if not token:
             raise HTTPException(status_code=401, detail="Not authenticated")
         payload = decode_access_token(token)
         # ... existing user verification logic
     ```

4. **Add CSRF protection** (`main.py` or new middleware):
   - Use the **double-submit cookie** pattern:
     - On login (or any authenticated response), set a `csrf_token` cookie (readable by JavaScript, NOT httpOnly).
     - On every state-mutating request (POST/PUT/PATCH/DELETE), require an `X-CSRF-Token` header that matches the `csrf_token` cookie.
   - Implementation:
     ```python
     import secrets

     class CSRFMiddleware(BaseHTTPMiddleware):
         async def dispatch(self, request, call_next):
             if settings.app_env == "dev":
                 return await call_next(request)  # Skip CSRF in dev

             if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                 # Exempt: /login, /health
                 if request.url.path in ("/login", "/health"):
                     return await call_next(request)

                 cookie_token = request.cookies.get("csrf_token")
                 header_token = request.headers.get("X-CSRF-Token")
                 if not cookie_token or not header_token or cookie_token != header_token:
                     return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})

             response = await call_next(request)

             # Set/refresh CSRF token cookie on every response
             if "csrf_token" not in request.cookies:
                 csrf_token = secrets.token_urlsafe(32)
                 response.set_cookie(
                     key="csrf_token",
                     value=csrf_token,
                     httponly=False,  # Must be readable by JS
                     secure=True,
                     samesite="lax",
                     path="/",
                 )

             return response
     ```

5. **Add HSTS header** (`main.py`):
   ```python
   if settings.app_env != "dev":
       @app.middleware("http")
       async def add_hsts_header(request, call_next):
           response = await call_next(request)
           response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
           return response
   ```

6. **Update CORS configuration** for cookie credentials:
   - `allow_credentials=True` is already set.
   - Ensure `allow_origins` does NOT use `["*"]` (wildcard is incompatible with credentials).
   - Already correct — origins are explicitly listed.

### Frontend Changes

7. **Update `api.ts`** — Add `credentials: "include"` and CSRF token:
   ```typescript
   async function request(path: string, opts: RequestInit = {}) {
     const headers: Record<string, string> = {
       "Content-Type": "application/json",
       ...(opts.headers as Record<string, string> || {}),
     };

     // In production (cookie auth): add CSRF token for mutating requests
     const method = opts.method?.toUpperCase() || "GET";
     if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
       const csrfToken = getCookie("csrf_token");
       if (csrfToken) {
         headers["X-CSRF-Token"] = csrfToken;
       }
     }

     // In dev: add Authorization header from localStorage
     // In prod: credentials: "include" sends the httpOnly cookie automatically

     const res = await fetch(`${BASE}${path}`, {
       credentials: "include",  // Always include cookies
       ...opts,
       headers,
     });
     // ... rest unchanged
   }

   function getCookie(name: string): string | null {
     const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
     return match ? decodeURIComponent(match[1]) : null;
   }
   ```

8. **Update `useAuth.ts`** — Remove localStorage, use `/me` cookie validation:
   ```typescript
   // Production: no localStorage. Token is in httpOnly cookie.
   // Dev: keep localStorage for backward compatibility.
   const isProd = BASE.includes("railway.app") || BASE.includes("vercel.app") || !BASE.includes("localhost");

   // On mount, call /me with credentials to check if the cookie is valid
   useEffect(() => {
     fetch(`${BASE}/me`, { credentials: "include" })
       .then(res => {
         if (res.ok) {
           setAuthenticated(true);
         } else {
           setAuthenticated(false);
         }
       })
       .catch(() => setAuthenticated(false))
       .finally(() => setReady(true));
   }, []);
   ```

9. **Update `login/page.tsx`** — Handle cookie-based login:
   - In production: the `/login` response sets an httpOnly cookie. The frontend just needs to check the response status, not extract a token.
   - In dev: keep the existing `setToken(data.access_token)` flow.

## Integration & Edge Cases

- **Test suite compatibility:** Tests use `Authorization: Bearer` headers. The dual-mode `get_current_user()` ensures tests continue to work without cookies. CSRF is disabled in dev/test mode.
- **SameSite=Lax:** Allows the cookie to be sent on top-level navigations (user clicks a link to the app) but blocks it on cross-site POST requests — this is the CSRF protection from the browser side.
- **Cookie domain:** When frontend (Vercel) and backend (Railway) are on different domains, cookies are cross-origin. `SameSite=Lax` + `credentials: "include"` work if the CORS `allow_credentials=True` is set and origins are explicitly listed. If cross-domain cookies are blocked by browser policies, consider using a custom domain (Step 9) where both services share a parent domain.
- **Safari ITP:** Safari's Intelligent Tracking Prevention may block third-party cookies (cookies set by a different domain). If the frontend is on `pulse.vercel.app` and the backend is on `pulse.up.railway.app`, Safari may block the auth cookie. **This is a strong argument for Step 9 (custom domain with shared parent domain).**

## Acceptance Criteria

1. `POST /login` in production sets an `httpOnly`, `Secure`, `SameSite=Lax` cookie named `pulse_token`.
2. `POST /login` in dev returns `{"access_token": "...", "token_type": "bearer"}` (unchanged).
3. `POST /logout` clears the `pulse_token` cookie.
4. State-mutating requests (POST/PUT/PATCH/DELETE) without a valid `X-CSRF-Token` header return 403 in production.
5. `GET` requests work without a CSRF token.
6. `Strict-Transport-Security` header is present on all responses in production.
7. The frontend no longer stores tokens in `localStorage` in production mode.
8. The full test suite passes (`pytest -q`) with no regressions (tests use header auth, CSRF is disabled in dev).
9. End-to-end login flow works in browser: login → navigate → create task → logout.

## Testing / QA

### Automated
```bash
cd code/backend

# Verify test suite passes (tests use dev mode — no CSRF, header auth)
python -m pytest -q --tb=short

# Build frontend
cd ../frontend && npm run build
```

### Manual
1. Deploy to production (or use `APP_ENV=prod` locally).
2. Open browser → login → check DevTools → Cookies tab → verify `pulse_token` is `httpOnly`, `Secure`.
3. Verify `csrf_token` cookie is present and readable by JS.
4. Attempt a POST without `X-CSRF-Token` header (using curl) → should get 403.
5. Logout → verify `pulse_token` cookie is cleared.
6. Verify `localStorage` has no `pulse_token` key after login.

## Files touched

- [code/backend/app/api/auth.py](code/backend/app/api/auth.py)
- [code/backend/app/core/security.py](code/backend/app/core/security.py)
- [code/backend/app/main.py](code/backend/app/main.py)
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts)
- [code/frontend/lib/hooks/useAuth.ts](code/frontend/lib/hooks/useAuth.ts)
- [code/frontend/app/login/page.tsx](code/frontend/app/login/page.tsx)

## Estimated effort

2–3 dev days (security changes require careful testing across both frontend and backend)

## Concurrency & PR strategy

- Branch: `phase-4.2/step-7-security-hardening`
- Blocking steps:
  - `Blocked until: .github/artifacts/phase4-2/plan/step-6-frontend-deploy-vercel.md` (both deploys must be live to test cookie flow)
- Merge Readiness: false

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cross-domain cookies blocked by Safari ITP | Step 9 (custom domain) resolves this. Alternatively, keep header auth as fallback. |
| CSRF middleware breaks test suite | CSRF is disabled when `APP_ENV=dev`. Tests run in dev mode. |
| Cookie auth breaks mobile browsers | `SameSite=Lax` is widely supported. Test on Chrome, Firefox, Safari. |
| `credentials: "include"` breaks CORS preflight | `allow_credentials=True` is already set. Origins must not be `*` (already explicit). |
| Dev workflow breaks | Dual-mode auth: cookies in prod, headers in dev. Both paths tested. |

## References

- [MVP_FINAL_AUDIT.md §3](../../MVP_FINAL_AUDIT.md) — S-2 (httpOnly cookies), S-3 (HTTPS), S-8 (CSRF)
- [architecture.md §4](../../architecture.md) — Security ADR
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [code/frontend/lib/hooks/useAuth.ts](code/frontend/lib/hooks/useAuth.ts) — TODO(deploy) markers

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
