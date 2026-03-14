# Step 1 — JWT & Auth Hardening

**Audit findings addressed:** S-1 (startup guard), S-4 (python-jose → PyJWT), S-9 (iss/aud claims), S-10 (token TTL), S-11 (bcrypt)  
**TODO markers placed for:** S-2 (localStorage), S-3 (HTTPS), S-8 (CSRF)

---

## Purpose

Replace the unmaintained `python-jose` JWT library with `PyJWT`, switch password hashing from `pbkdf2_sha256` to `bcrypt`, add `iss`/`aud` claims to tokens, reduce the token TTL from 7 days to 8 hours, add a startup guard that prevents the server from starting in non-dev environments with the default secret, and place `# TODO(deploy):` markers for the three deployment-gated findings.

---

## Deliverables

- `code/backend/requirements.txt` — `python-jose[cryptography]` removed; `PyJWT>=2.8.0` added.
- `code/backend/app/core/security.py` — rewritten to use `PyJWT` and direct `bcrypt` library.
- `code/backend/app/core/config.py` — `app_env` field added; `ACCESS_TOKEN_EXPIRE_MINUTES` default reduced to 480 (8 hours).
- `code/backend/app/main.py` — startup guard in `lifespan`; `# TODO(deploy):` markers for S-3 and S-8.
- `code/frontend/lib/hooks/useAuth.ts` — `# TODO(deploy):` marker for S-2.
- `scripts/create_dev_user.py` — no change required (re-run after merge to re-hash dev user with bcrypt).

---

## Primary files to change

- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/app/core/security.py](code/backend/app/core/security.py)
- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [code/backend/app/main.py](code/backend/app/main.py)
- [code/frontend/lib/hooks/useAuth.ts](code/frontend/lib/hooks/useAuth.ts)

---

## Detailed implementation steps

1. **`requirements.txt`** — Remove the line `python-jose[cryptography]==3.3.0`. Add `PyJWT>=2.8.0` below `passlib[bcrypt]`. Keep `passlib[bcrypt]==1.7.4` in the file only as a transitional reference — it is no longer called in the hashing path (see step 3 below). Alternatively, remove it too since `bcrypt` is installed as a direct dependency of `passlib`. Confirm that `bcrypt` itself is listed (add `bcrypt>=4.0.0` explicitly to prevent silent version drift).

2. **`app/core/security.py`** — Replace all imports and functions:
   - Remove `from jose import JWTError, jwt` (and any other `jose` imports).
   - Add `import bcrypt as _bcrypt` and `import jwt as pyjwt` (plus `from jwt.exceptions import InvalidTokenError`).
   - Rewrite `get_password_hash(password: str) -> str` to call `_bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")`.
   - Rewrite `verify_password(plain: str, hashed: str) -> bool` to call `_bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))`.
   - Rewrite `create_access_token(subject: str, expires_delta: timedelta | None = None) -> str` to use `pyjwt.encode(payload, key, algorithm="HS256")` where `payload` includes `{"sub": subject, "exp": ..., "iss": "pulse-api", "aud": "pulse-client"}`.
   - Rewrite `decode_access_token(token: str) -> str` to call `pyjwt.decode(token, key, algorithms=["HS256"], audience="pulse-client", issuer="pulse-api")`. Catch `InvalidTokenError` and raise `HTTPException(status_code=401, detail="Invalid or expired token")`.
   - Remove any remaining `CryptContext` usage.

3. **`app/core/config.py`** — Add a new field `app_env: str = Field("dev", validation_alias="APP_ENV")`. Change the default for `access_token_expire_minutes` from `60 * 24 * 7` to `60 * 8` (480 minutes = 8 hours). No other changes to `Settings`.

4. **`app/main.py`** — In the `lifespan` async context manager (or the startup event), add:
   ```python
   if settings.jwt_secret == "dev-secret-change-me" and settings.app_env != "dev":
       raise RuntimeError(
           "JWT_SECRET must be changed from the default value in non-dev environments. "
           "Set the JWT_SECRET environment variable."
       )
   ```
   Also add two comment markers near the top of the file (after the existing imports/middleware block):
   ```python
   # TODO(deploy): S-3 — Enforce HTTPS. Deploy behind nginx/Caddy with TLS termination.
   #               Set Strict-Transport-Security header. Configure `Secure` cookie flag.
   
   # TODO(deploy): S-8 — Add CSRF protection when httpOnly cookie auth is active (S-2).
   #               Use double-submit cookie or synchronizer token pattern.
   ```

5. **`code/frontend/lib/hooks/useAuth.ts`** — Find the `useEffect` or `localStorage.setItem` call that stores the token. Add directly above it:
   ```typescript
   // TODO(deploy): S-2 — Migrate token storage from localStorage to httpOnly + Secure +
   //               SameSite=Strict cookies. Remove this localStorage write and the corresponding
   //               read below. Implement a /refresh endpoint for session renewal.
   ```

6. **After merging** — Re-run `scripts/create_dev_user.py` to replace the dev user's `pbkdf2_sha256` hash with a `bcrypt` hash in `dev.db`. Without this step, existing dev user logins will fail.

---

## Integration & Edge Cases

- **Existing dev.db hashes:** All users created before this step have `pbkdf2_sha256` hashes. `verify_password` with the new `bcrypt.checkpw` will always return `False` for those hashes. The dev user must be recreated (step 6 above). If any other users exist in dev, they will need new passwords.
- **passlib presence:** `passlib[bcrypt]==1.7.4` remains in `requirements.txt` and installed. It is not called in any code path after this step. If `passlib` is removed from `requirements.txt`, confirm no other module imports it.
- **bcrypt 5.x incompatibility with passlib:** `passlib` 1.7.4 calls `bcrypt.__about__.__version__` which does not exist in `bcrypt>=4.0`. Do NOT route hashing through `passlib.CryptContext` — use `bcrypt` directly. This is the reason `passlib` is bypassed.
- **PyJWT vs python-jose API:** `PyJWT` `encode()` returns a `str` (not `bytes`) since v2.x. No `.decode()` call needed. `decode()` returns a `dict`. Audience/issuer validation is handled by passing `audience=` and `issuer=` kwargs.
- **Token TTL reduction from 7 days to 8 hours:** Any existing long-lived tokens (7-day) will continue to validate until they expire. No forced revocation is needed for dev.

**Backup note:** Before merging, snapshot `dev.db`:
```bash
cp code/backend/data/dev.db code/backend/data/dev.db.pre-security-hardening.bak
```

---

## Acceptance Criteria

1. `grep -r "python-jose"` in `code/backend/` returns 0 results.
2. `grep -r "pbkdf2_sha256"` in `code/backend/` returns 0 results.
3. `POST /login` with valid credentials returns 200 and a JWT token string.
4. The decoded JWT payload from a `/login` response contains `"iss": "pulse-api"` and `"aud": "pulse-client"`.
5. The decoded JWT `exp` − `iat` equals 28800 seconds (8 hours).
6. Starting the server with `APP_ENV=prod` and `JWT_SECRET=dev-secret-change-me` raises `RuntimeError` before accepting connections.
7. Starting the server with `APP_ENV=prod` and a non-default `JWT_SECRET` starts successfully and `GET /health` returns 200.
8. `grep "TODO(deploy): S-2"` finds a match in `code/frontend/lib/hooks/useAuth.ts`.
9. `grep "TODO(deploy): S-3"` finds a match in `code/backend/app/main.py`.
10. `grep "TODO(deploy): S-8"` finds a match in `code/backend/app/main.py`.
11. All existing backend tests pass: `pytest code/backend/tests/ -q` exits 0.

---

## Testing / QA

**Tests to add in `code/backend/tests/test_api.py`:**

- `test_jwt_has_iss_aud_claims` — Login with valid credentials. Decode the token body (base64 middle segment). Assert `payload["iss"] == "pulse-api"` and `payload["aud"] == "pulse-client"`.
- `test_token_ttl_is_8_hours` — Login. Decode the token. Assert `payload["exp"] - payload["iat"] == 28800`.
- `test_startup_guard_rejects_default_secret_in_prod` — Call `decode_access_token` (or a unit test on the `lifespan` logic) asserting the guard raises when `app_env=prod` and secret is default. (Unit test, no live server needed.)

```bash
.venv/bin/pytest code/backend/tests/test_api.py -q -k "iss_aud or ttl or startup_guard"
```

**Manual QA checklist:**

1. Install updated requirements: `pip install -r code/backend/requirements.txt`.
2. Confirm `jose` is no longer importable: `python -c "import jose"` should raise `ModuleNotFoundError`.
3. Start the dev server normally. `POST /login` succeeds.
4. Copy the returned token to [jwt.io](https://jwt.io). Verify `iss`, `aud`, and `exp` fields.
5. Check that `exp - iat ≈ 28800` in the decoded payload.
6. Confirm `# TODO(deploy):` comments are visible in `main.py` and `useAuth.ts`.

---

## Files touched

- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/app/core/security.py](code/backend/app/core/security.py)
- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [code/backend/app/main.py](code/backend/app/main.py)
- [code/frontend/lib/hooks/useAuth.ts](code/frontend/lib/hooks/useAuth.ts)

---

## Estimated effort

1 dev day

---

## Concurrency & PR strategy

This is the **blocking step** for Steps 2 and 5. All other steps (3 and 4) may be worked in parallel but should not be merged until this step is merged.

- `Blocking steps:` None (this is the root step).
- `Merge Readiness: false` — set to `true` once acceptance criteria 1–11 are verified and the dev user is re-created.
- Branch: `phase-3.2/step-1-jwt-auth-hardening`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Dev user locked out after hash algorithm change | Run `scripts/create_dev_user.py` immediately after merge. Document this in PR description. |
| `bcrypt` version pinned vs floating | Pin `bcrypt>=4.0,<6` in `requirements.txt` to avoid future breaks from major changes. |
| Long-lived 7-day tokens still valid post-merge | Acceptable — no production deployment yet. Dev tokens will expire naturally or be replaced by re-login. |
| `pyjwt.encode()` returns `bytes` in old versions | Prevented by `PyJWT>=2.8.0` pin (all v2.x return `str`). |

---

## References

- [.github/artifacts/phase3-2/summary/final-report.md](../../summary/final-report.md) — S-1, S-4, S-9, S-10, S-11
- [code/backend/app/core/security.py](code/backend/app/core/security.py)
- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [PyJWT docs](https://pyjwt.readthedocs.io/)

---

## Author Checklist

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/`
- [x] Manual QA checklist added
- [x] Backup/atomic-write noted (dev.db snapshot)
