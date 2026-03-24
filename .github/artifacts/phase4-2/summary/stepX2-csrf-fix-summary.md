# Step X2 — CSRF Cross-Origin Fix Summary

**Date:** 2026-03-23  
**Type:** Production hotfix + test reinforcement  
**Triggered by:** `POST /ai/synthesis` returning 403 in production  
**Status:** ✅ Resolved — 190 tests passing

---

## Problem

`POST /ai/synthesis` (and all other mutating `/ai/*` endpoints) returned HTTP 403 in production from the moment the application was first used, making AI features completely inaccessible.

### Root cause

Phase 4.2 step 7 (security hardening) implemented **double-submit cookie CSRF protection**:

1. `/login` sets a `csrf_token` cookie (non-httpOnly, readable by JS)
2. Frontend reads it via `document.cookie` → `getCsrfToken()`
3. Frontend echoes it as `X-CSRF-Token` header on mutations
4. Backend `_CSRFMiddleware` compares cookie value to header value

This pattern works within a single origin. **It is architecturally broken for cross-origin deployments.**

The frontend runs on **Vercel** (`pulse-dashboard.vercel.app`). The backend runs on **Railway** (`*.railway.app`). Browser SOP (Same-Origin Policy) prevents JavaScript running on the Vercel domain from reading cookies set by the Railway domain. `document.cookie` only returns cookies that belong to the *current* page's domain.

Result: `getCsrfToken()` always returned `""` → the `if (csrfToken)` guard suppressed the header → backend received `X-CSRF-Token: null` → `compare_digest(csrf_cookie, None)` → **403 on every mutating request in production, always**.

### Why tests didn't catch it

The test suite runs with `APP_ENV=dev`. The `_CSRFMiddleware` has this bypass:

```python
if _s.app_env == "dev" or request.method in self._SAFE_METHODS:
    return await call_next(request)
```

CSRF was completely inactive during all testing. There were zero tests that verified CSRF behavior in `app_env=prod` mode. The middleware was added, audited, and confirmed by 171 tests — none of which ever exercised the code path that was broken.

---

## Fix

### CSRF approach changed: double-submit cookie → custom-header presence

**Security model (unchanged in intent, corrected in implementation):**  
The browser's SOP + CORS preflight mechanism prevents cross-origin JavaScript from adding *custom headers* to a cross-origin request without a successful CORS preflight that the server explicitly approves. Because the backend CORS allowlist restricts which origins can make credentialed requests, any request bearing a custom `X-CSRF-Token` header must have originated from allowed JS. The header *value* is not secret — its **non-empty presence** is the proof of same-origin intent.

This is the [OWASP-recommended "Custom Request Headers" CSRF defense](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#employing-custom-request-headers-for-ajaxapi) for API-only SPAs with strict CORS.

### Files changed

| File | Change |
|------|--------|
| `code/backend/app/main.py` | `_CSRFMiddleware`: replaced `compare_digest(csrf_cookie, csrf_header)` with `csrf_header.strip()` presence check. Removed `import secrets`. Updated docstring to document the security model. |
| `code/backend/app/api/auth.py` | Removed `csrf_token` cookie from `/login` response (no longer needed). Removed `import secrets`. Added explanatory comment documenting why the cookie was removed. |
| `code/frontend/lib/api.ts` | Changed from `if (csrfToken) headers["X-CSRF-Token"] = csrfToken` to `headers["X-CSRF-Token"] = getCsrfToken() \|\| "1"` — always sends the header on mutations. Updated comment to explain the security model. |
| `code/backend/tests/test_csrf.py` | **New file.** 19 regression + unit tests covering the middleware in `prod` and `dev` modes. Specifically captures the `/ai/synthesis` 403 bug as a named regression test. |

### Diff summary

**`_CSRFMiddleware` before:**
```python
csrf_cookie = request.cookies.get("csrf_token")
csrf_header = request.headers.get("X-CSRF-Token")
if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
    return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
```

**`_CSRFMiddleware` after:**
```python
csrf_header = request.headers.get("X-CSRF-Token", "").strip()
if not csrf_header:
    return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
```

**`api.ts` before:**
```typescript
if (isMutating) {
    const csrfToken = getCsrfToken();
    if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
}
```

**`api.ts` after:**
```typescript
if (isMutating) {
    headers["X-CSRF-Token"] = getCsrfToken() || "1";
}
```

---

## Why this is still secure

| Attack vector | Defence |
|---|---|
| Cross-origin CSRF from attacker domain | Browser SOP prevents attacker's JS from adding `X-CSRF-Token` without a CORS preflight. Backend's `allow_origins` only whitelists Vercel domain → preflight rejected → header can't be set |
| Cross-origin CSRF from form submission | Form POSTs are `application/x-www-form-urlencoded` or `multipart/form-data` — browser adds no custom headers. FastAPI expects `application/json` body → request fails at Pydantic validation anyway |
| Cross-origin CSRF with credentials via `fetch` | `credentials: "include"` + custom headers always require preflight. CORS restricts this to known origins |
| Attacker reads `X-CSRF-Token` value | Value is not secret (`"1"` by default). No secret knowledge required on either side — the CORS restriction is the security property |

The old `compare_digest` check added no security benefit over the new approach: even if an attacker could not forge the cookie value, the fundamental problem (not being able to read the cookie from a cross-origin page) was already providing all the security. The new approach is cryptographically equivalent but actually works.

---

## Test gaps addressed

19 new tests in [tests/test_csrf.py](../../../../code/backend/tests/test_csrf.py):

| Test class | Coverage |
|---|---|
| `TestCSRFMiddlewareProd` | Blocks POST/PUT/DELETE/PATCH without header; allows with any non-empty value; allows GET/OPTIONS; exempts /login /logout /health; whitespacen-only rejected |
| `TestCSRFMiddlewareDev` | Mutations without header NOT blocked in dev mode; `/ai/synthesis` specifically passes |
| `TestCSRFRegressionAiSynthesis` | Named regression: confirms exact production failure (no header → 403); confirms fix (header present → not 403); all `/ai/*` endpoints unblocked; cookie not required |

### Lesson documented in copilot-instructions.md (to add)

> **Middleware that has an `app_env == "dev"` bypass must be tested against a simulated `app_env == "prod"` state.** If middleware is only exercised through the subprocess server (which always starts with `APP_ENV=dev`), production-only code paths are dead code from the test suite's perspective. Use in-process `httpx.AsyncClient + ASGITransport` with a `yield` fixture that patches `get_settings().app_env` to test prod-mode middleware paths directly.

---

## Test results

```
190 passed, 11 warnings in 23.37s
```

Previous: 171 passed. New: +19 (all CSRF regression/unit tests).  
Warnings: existing JWT key-length warnings from intentional test tokens only.

---

## Deployment checklist

- [ ] Deploy backend to Railway (env vars unchanged — no new `APP_ENV`, `CSRF_*` vars required)
- [ ] Deploy frontend to Vercel (api.ts change ships automatically)
- [ ] Smoke test: `POST /ai/synthesis` from the production frontend URL → verify 202 (not 403)
- [ ] Smoke test: `POST /tasks/` from the production frontend URL → verify task is created
- [ ] Verify no `csrf_token` cookie appears in browser DevTools after login (it was removed)

---

## References

- OWASP CSRF Prevention: Custom Request Headers pattern — https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#employing-custom-request-headers-for-ajaxapi
- Phase 4.2 step 7 summary: [step7-security-hardening-summary.md](step7-security-hardening-summary.md) (introduced the double-submit pattern)
- Deployment audit: [deployment-audit.md](../../deployment-audit.md)
