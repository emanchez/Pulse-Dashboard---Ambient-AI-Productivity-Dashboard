# Phase 4.2 Step 7 — Security Hardening Summary

**Branch:** `phase-4.2/step-7-security-hardening`
**Date:** 2026-03-23
**Status:** ✅ Complete

---

## What Was Done

### Backend Changes

#### `code/backend/app/api/auth.py`
- **Added `import secrets`** for cryptographically secure CSRF token generation.
- **Updated `/login` endpoint:**
  - `Response` added as parameter so Set-Cookie headers can be emitted.
  - In `APP_ENV=prod`: sets two cookies:
    - `pulse_token` — httpOnly, Secure, SameSite=Lax (JWT, not readable by JS).
    - `csrf_token` — NOT httpOnly, Secure, SameSite=Lax (readable by JS for double-submit pattern).
    - Returns `{"message": "ok"}` (no JWT in body).
  - In `APP_ENV=dev` (all tests): returns `{"access_token": "...", "token_type": "bearer"}` unchanged.
- **Added `/logout` endpoint:** Clears `pulse_token` and `csrf_token` cookies via `delete_cookie()`.
- **Replaced `get_current_user` dependency:** Changed from `token: str = Depends(oauth2_scheme)` to `request: Request` + dual-mode extraction:
  1. Reads `pulse_token` from cookies first (production).
  2. Falls back to `Authorization: Bearer <token>` header (dev mode + full test suite).
  3. Rejects the frontend sentinel value `"cookie"` so it never reaches token validation.
  - FastAPI injects `Request` automatically — no changes required to any route files.
- **Updated `/me` endpoint:** Now uses the new `get_current_user(request, session)` signature.
- **Updated `OAuth2PasswordBearer`:** Added `auto_error=False` so header absence doesn't auto-raise 401 (cookie auth handles it instead).

#### `code/backend/app/main.py`
- **Added `import secrets`** at the top of the file.
- **Added `_CSRFMiddleware`** (double-submit cookie pattern):
  - Disabled in `APP_ENV=dev` (no overhead in local dev or test suite).
  - Exempt paths: `/login`, `/logout`, `/health`.
  - Safe HTTP methods (GET, HEAD, OPTIONS, TRACE) are exempt.
  - All other requests must include `X-CSRF-Token` header matching the `csrf_token` cookie; returns 403 on mismatch.
  - Uses `secrets.compare_digest()` to prevent timing attacks.
- **Added `_HSTSMiddleware`:** Injects `Strict-Transport-Security: max-age=63072000; includeSubDomains` on all responses in non-dev environments.
- **Removed TODO comments** for S-2, S-3, S-5, S-8 (all addressed in this step).
- **Middleware stack order** (innermost → outermost):
  `ActionLog → SlowAPI → HSTS → CSRF → ContentSizeLimit`

### Frontend Changes

#### `code/frontend/lib/api.ts`
- **Added `getCsrfToken()` helper:** Reads `csrf_token` cookie from `document.cookie`. Returns empty string in SSR or when cookie is absent.
- **Rewrote `request()` function:**
  - Changed `credentials: "omit"` → `credentials: "include"` so the httpOnly cookie is sent automatically on every request.
  - Strips `Authorization: Bearer cookie` header (frontend sentinel) so the backend never receives an invalid JWT in the header.
  - Injects `X-CSRF-Token` header on POST/PUT/PATCH/DELETE from the `csrf_token` cookie.
- **Updated `getActiveSession()`** and **`getActiveSystemState()`** inline fetch calls:
  - Changed `credentials: "omit"` → `credentials: "include"`.
  - Skip `Authorization` header when token is the `"cookie"` sentinel.

#### `code/frontend/lib/hooks/useAuth.ts`
- **Removed TODO(deploy) comment** for S-2 migration.
- **Unified session validation on mount:** Always calls `GET /me` with `credentials: "include"`. Optionally includes `Authorization: Bearer <stored>` if a JWT is in localStorage (dev mode).  
  - 200 → authenticated. Token state = stored JWT (dev) or `"cookie"` sentinel (prod, no localStorage entry).
  - 401/403 → clear localStorage, unauthenticated.
  - Network error → keep stored token (keeps UX stable when backend is temporarily unreachable).
- **Updated `setToken()`:** Only writes to localStorage when `t !== "cookie"` (i.e., a real JWT). Prod sessions store nothing in localStorage.
- **Updated `logout()`:** Now calls `POST /logout` with `credentials: "include"` to clear the httpOnly cookie before clearing local state. Errors on the `/logout` fetch are swallowed.

#### `code/frontend/app/login/page.tsx`
- **Updated `handleSubmit()`:** Uses `data.access_token || "cookie"` to handle both:
  - Dev response: `{"access_token": "eyJ..."}` → stores real JWT.
  - Prod response: `{"message": "ok"}` (no `access_token`) → uses `"cookie"` sentinel.

---

## Acceptance Criteria Results

| # | Criterion | Result |
|----|-----------|--------|
| 1 | `/login` in prod sets `pulse_token` httpOnly cookie | ✅ Implemented |
| 2 | `/login` in dev returns `{"access_token": "..."}` (unchanged) | ✅ Verified — test suite passes |
| 3 | `/logout` clears `pulse_token` and `csrf_token` cookies | ✅ Implemented |
| 4 | POST/PUT/PATCH/DELETE without `X-CSRF-Token` return 403 in prod | ✅ `_CSRFMiddleware` implemented |
| 5 | GET requests work without CSRF token | ✅ Safe methods exempted |
| 6 | `Strict-Transport-Security` header in production | ✅ `_HSTSMiddleware` implemented |
| 7 | Frontend no longer stores tokens in localStorage in production | ✅ `"cookie"` sentinel used; localStorage write guarded |
| 8 | Full test suite passes (`pytest -q`) — **171 passed, 0 failed** | ✅ Verified |
| 9 | End-to-end login flow | ⚠️ Requires production deploy test (Step 10) |

---

## Files Touched

| File | Change |
|------|--------|
| `code/backend/app/api/auth.py` | Cookie auth, /logout, dual-mode get_current_user |
| `code/backend/app/main.py` | CSRF middleware, HSTS middleware, removed TODOs |
| `code/frontend/lib/api.ts` | credentials:include, CSRF header, getCsrfToken() |
| `code/frontend/lib/hooks/useAuth.ts` | Cookie-aware session validation, cookie sentinel |
| `code/frontend/app/login/page.tsx` | Handle prod/dev login response |

---

## Hard-Won Lessons

### `OAuth2PasswordBearer` with `auto_error=False` is required for dual-mode auth
The default `OAuth2PasswordBearer` raises a 401 automatically when the `Authorization` header is absent. When switching to cookie-first auth, the header is legitimately absent in production. Setting `auto_error=False` tells FastAPI not to auto-reject and lets the dependency logic check the cookie instead.

### `secrets.compare_digest()` is mandatory for CSRF token comparison
Using `==` for CSRF token comparison is vulnerable to timing attacks. `secrets.compare_digest()` runs in constant time regardless of where the strings diverge.

### FastAPI injects `Request` automatically in Depends — no route changes needed
Replacing `token: str = Depends(oauth2_scheme)` with `request: Request` in `get_current_user` does not require changes to any route file. FastAPI automatically resolves `Request` as a special injection target when it appears as a parameter in a dependency.

### The "cookie" sentinel preserves backwards compatibility without changing function signatures
All `api.ts` functions accept a `token: string` parameter and pass it as `Authorization: Bearer ${token}`. Instead of changing 20+ function signatures to `token: string | null`, the `request()` function detects `"Bearer cookie"` and strips the header, letting the browser send the httpOnly cookie instead. This is clean and transparent to callers.
