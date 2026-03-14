# Phase 3.2 — Implementation Summary (Steps 2–5)

## What was implemented

### ✅ Step 2 — Rate Limiting
- Added `slowapi` dependency and a shared `Limiter` instance (`app/core/limiter.py`).
- Wired `SlowAPIMiddleware` into `app/main.py` to enforce a global `200/minute` cap.
- Applied `@limiter.limit(...)` to `POST /login` with `5/min` in `prod` and `100/min` in `dev`.
- Added a regression test ensuring no 429 in dev under 10 rapid login attempts.

### ✅ Step 3 — CORS, Body Limit, and 422 Hardening
- Updated `Settings.get_cors_origins()` to fail-closed in non-dev when localhost origins appear.
- Added a body-size limit middleware (512 KB) to return 413 for oversized payloads.
- Added a `RequestValidationError` handler that returns:
  - `{"detail": "Validation error"}` in prod
  - full Pydantic errors (encoded) in dev
- Added tests for oversized request (413), dev validation output, and fail-closed CORS.

### ✅ Step 4 — Input Sanitization
- Added `bleach` dependency.
- Sanitized `ManualReport` `title` and `body` via `@field_validator(..., mode="before")`, stripping tags but preserving inner text.
- Added tests confirming tags are stripped and markdown remains.

### ✅ Step 5 — Auth Audit Logging
- Extended `ActionLog` model with a `client_host` column and `AUTH_ACTION_TYPES` constant.
- Added non-blocking audit events for `LOGIN_SUCCESS` and `LOGIN_FAILED` in `/login`.
- Updated pulse/flow-state queries to ignore auth events.
- Added tests verifying audit rows are created for both success and failure.

## Verification
- All backend tests pass: `89 passed`.
- `grep -r "python-jose"` and `grep -r "pbkdf2_sha256"` return nothing.
- `TODO(deploy)` markers exist for S-2, S-3, S-5, S-8.

---

## Notes / Observations
- `bleach.clean(..., tags=[], strip=True)` removes tags but preserves text content; tests reflect that behavior.
- The 512 KB request cap is implemented via `BaseHTTPMiddleware` to avoid ASGI streaming edge cases.
