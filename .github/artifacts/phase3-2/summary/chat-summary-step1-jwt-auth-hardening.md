# Chat Summary — Step 1: JWT & Auth Hardening

**Date:** 2026-03-14

## What was done

- Implemented Phase 3.2 Step 1 (JWT/auth hardening) in the backend and frontend.
- Replaced `python-jose` with `PyJWT` and removed all `python-jose` references.
- Replaced password hashing via `passlib.pbkdf2_sha256` with direct `bcrypt` hashing/verification.
- Added `iss` and `aud` claims to JWTs and validated them on decode.
- Reduced default token TTL from 7 days to 8 hours.
- Added `app_env` config and a startup guard that prevents running with the default secret in non-dev environments.
- Added `# TODO(deploy):` markers for S-2 (frontend), S-3 (HTTPS), and S-8 (CSRF).
- Added 3 new backend tests verifying iss/aud claims, token TTL, and the startup guard.
- Ran the full backend test suite (79 passing) and recreated the dev user with a bcrypt password hash.

## Files changed

- `code/backend/requirements.txt`
- `code/backend/app/core/security.py`
- `code/backend/app/core/config.py`
- `code/backend/app/main.py`
- `code/frontend/lib/hooks/useAuth.ts`
- `code/backend/tests/test_api.py`

## Notes

- Dev user was re-created using `scripts/create_dev_user.py` to ensure login works after switching hashing algorithm.
- All acceptance criteria from the phase plan were verified (no `python-jose` or `pbkdf2_sha256` in app code, TODO markers present, tests passing).
