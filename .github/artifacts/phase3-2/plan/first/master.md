# Phase 3.2 — Security Hardening Master Plan

**Category:** Pre-Deployment Security Hardening  
**Date:** 2026-03-11  
**From:** Phase 3.2 Audit (final-report.md §5)  
**Scope boundary:** All fixes that do NOT require active deployment infrastructure. Deployment-gated items (S-2, S-3, S-5, S-8) receive `# TODO(deploy):` markers only.

---

## Scope

Harden the backend and frontend against the 15 security findings catalogued in the Phase 3.2 audit. This phase covers only code-level fixes that can be validated locally before any deployment. Deployment-dependent mitigations (HTTPS, httpOnly cookies, production CORS, CSRF) are deferred but marked clearly in the codebase.

**Out of scope:** Alembic migrations, Phase 4 AI services, OZ integration.

---

## Phase-level Deliverables

- `python-jose` removed; `PyJWT` in use with `iss`/`aud` claims and 8-hour TTL.
- Passwords hashed with `bcrypt` (not `pbkdf2_sha256`).
- Startup guard rejects default `JWT_SECRET` in non-dev environments.
- `slowapi` rate limiter active on `/login` (5/min prod, 100/min dev) and globally (200/min).
- Custom `RequestValidationError` handler returns sanitized 422 body in non-dev environments.
- Request body capped at 512 KB via middleware.
- CORS helper fails closed (raises `ValueError`) if localhost origins appear in non-dev config.
- `bleach` strips HTML from `ManualReport` `title` and `body` fields on create and update.
- Login success/failure events written to `ActionLog`.
- `# TODO(deploy):` markers in place for S-2, S-3, S-5, S-8.
- All existing backend tests continue to pass (`pytest code/backend/tests/ -q`).
- At least one new test per step verifying the security behaviour.

---

## Steps (ordered)

1. [Step 1 — JWT & Auth Hardening](./step-1-jwt-auth-hardening.md)  
   *Findings: S-1, S-4, S-9, S-10, S-11. TODO markers: S-2, S-3, S-8.*

2. [Step 2 — Rate Limiting](./step-2-rate-limiting.md)  
   *Findings: S-6, S-7.*

3. [Step 3 — CORS, Request Body Limit & 422 Hardening](./step-3-cors-request-hardening.md)  
   *Findings: S-5, S-13, S-14. TODO marker: S-5.*

4. [Step 4 — Input Sanitization](./step-4-input-sanitization.md)  
   *Finding: S-12.*

5. [Step 5 — Auth Audit Logging](./step-5-auth-audit-logging.md)  
   *Finding: S-15.*

---

## Merge Order

Steps 2–5 are all independent of each other and may be parallelised. Step 1 must merge first because steps 2 and 5 depend on the `app_env` field added in Step 1 (Step 2 uses it to select the login rate-limit string; Step 5's tests use `create_access_token` from the updated `security.py`).

1. `.github/artifacts/phase3-2/plan/first/step-1-jwt-auth-hardening.md` — branch: `phase-3.2/step-1-jwt-auth-hardening`
2. `.github/artifacts/phase3-2/plan/first/step-2-rate-limiting.md` — branch: `phase-3.2/step-2-rate-limiting` *(blocked on step 1)*
3. `.github/artifacts/phase3-2/plan/first/step-3-cors-request-hardening.md` — branch: `phase-3.2/step-3-cors-request-hardening` *(can merge in parallel with steps 2, 4, 5 after step 1)*
4. `.github/artifacts/phase3-2/plan/first/step-4-input-sanitization.md` — branch: `phase-3.2/step-4-input-sanitization`
5. `.github/artifacts/phase3-2/plan/first/step-5-auth-audit-logging.md` — branch: `phase-3.2/step-5-auth-audit-logging` *(blocked on step 1)*

---

## Phase Acceptance Criteria

1. `pytest code/backend/tests/ -q` exits 0 with no regressions after all steps merge.
2. `GET /health` returns 200 after `uvicorn` startup with `APP_ENV=prod` and a non-default `JWT_SECRET`.
3. Starting the server with `APP_ENV=prod` and `JWT_SECRET=dev-secret-change-me` raises `RuntimeError` and prevents startup.
4. `POST /login` with wrong credentials returns 401; attempting 6 requests/minute from the same IP in prod returns 429 on the 6th.
5. `POST /reports` with `title` containing `<script>alert(1)</script>` persists a clean string with tags stripped.
6. A valid JWT decoded with `decode_access_token` includes `iss=pulse-api` and `aud=pulse-client`.
7. `GET /reports` with an oversized body (>512 KB) returns 413.
8. In prod mode, `POST /tasks` with a missing required field returns 422 with `{"detail": "Validation error"}` (no internal field names).
9. A successful login creates a `LOGIN_SUCCESS` row in `action_logs`; a failed login creates a `LOGIN_FAILED` row.
10. `grep -r "python-jose"` in `code/backend/` returns no results.
11. `grep -r "pbkdf2_sha256"` in `code/backend/` returns no results.
12. All `# TODO(deploy):` markers for S-2, S-3, S-5, S-8 are present in the codebase (`grep -r "TODO(deploy)"` finds them).

---

## Concurrency Groups & PR Strategy

| Group | Steps | Can be parallelised? |
|-------|-------|----------------------|
| A | Step 1 | No — must merge first |
| B | Steps 2, 3, 4, 5 | Yes — all independent after step 1 merges |

Branch naming: `phase-3.2/step-<n>-<short-title>`  
PRs in Group B that are opened before Step 1 merges must include `Depends-On: phase-3.2/step-1-jwt-auth-hardening` in the PR description and carry the `depends` label.

---

## Verification Plan

After all 5 steps merge:

```bash
# 1. Install/verify dependencies
cd code/backend
pip install -r requirements.txt
grep -i "pyjwt\|python-jose\|slowapi\|bleach" requirements.txt

# 2. Regression test suite
cd /project-root
.venv/bin/pytest code/backend/tests/ -q

# 3. Startup guard (should raise)
APP_ENV=prod JWT_SECRET=dev-secret-change-me .venv/bin/uvicorn app.main:app &
# Expect: RuntimeError at startup — process exits non-zero

# 4. Startup guard (should succeed — use a real secret)
APP_ENV=prod JWT_SECRET=prod-secret-32chars-min .venv/bin/uvicorn app.main:app &
curl -s http://127.0.0.1:8001/health

# 5. Audit log smoke test
curl -s -X POST http://127.0.0.1:8001/login \
  -H "Content-Type: application/json" \
  -d '{"username":"devuser","password":"wrongpass"}'
# Then query action_logs for a LOGIN_FAILED row.

# 6. HTML sanitization check
TOKEN=$(curl -s -X POST .../login -d '{"username":"devuser","password":"devpass"}' | jq -r .accessToken)
curl -s -X POST .../reports \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"<b>hello</b>","body":"test","status":"draft"}'
# Expect: title in response is "hello" (tags stripped)

# 7. TODO marker check
grep -rn "TODO(deploy)" code/
```

**Manual checklist:**

- [ ] `requirements.txt` contains `PyJWT` and not `python-jose`.
- [ ] `python-jose` is not importable in the venv (`import jose` raises ImportError).
- [ ] A decoded token payload contains `iss` and `aud` fields.
- [ ] `/login` returns 429 after 5 rapid calls in prod mode (manual curl loop or integration test).
- [ ] `# TODO(deploy):` comments present for S-2 in `useAuth.ts`, S-3 and S-8 in `main.py`.

---

## Risks, Rollbacks & Migration Notes

| Risk | Impact | Mitigation |
|------|--------|------------|
| Existing dev users have `pbkdf2_sha256` hashes in `dev.db` | First login after Step 1 fails for existing users | Run `scripts/create_dev_user.py` to re-create the dev user with a `bcrypt` hash after Step 1 merges. **BEFORE MERGE:** take a `dev.db` snapshot. |
| Deployed `dev.db` schema doesn't need changing | Low | No column changes in this phase. |
| `slowapi` integration breaks test fixture (rate-limit fires mid-suite) | Test failures | Step 2 uses `app_env`-conditional limits: `100/minute` in dev vs `5/minute` in prod. The dev default is intentionally permissive. |
| `bleach` strips content users consider valid (e.g., markdown asterisks) | Minor UX | `bleach.clean(v, tags=[], strip=True)` only removes HTML tags. Markdown symbols are unaffected. |

**Required backup before Step 1 merge:**
```bash
cp code/backend/data/dev.db code/backend/data/dev.db.pre-security-hardening.bak
```

---

## References

- [.github/artifacts/phase3-2/summary/final-report.md](../../summary/final-report.md) — §5 Security Audit
- [.github/artifacts/PDD.md](../../../PDD.md) — ADR-001 (local-first), ADR-003 (auth policy)
- [.github/artifacts/architecture.md](../../../architecture.md)
- [.github/artifacts/PLANNING.md](../../../PLANNING.md)
- Step files: [step-1](./step-1-jwt-auth-hardening.md), [step-2](./step-2-rate-limiting.md), [step-3](./step-3-cors-request-hardening.md), [step-4](./step-4-input-sanitization.md), [step-5](./step-5-auth-audit-logging.md)

---

## Author Checklist (master)

- [x] All step files created and linked
- [x] Phase-level acceptance criteria are measurable
- [x] PR/merge order documented
