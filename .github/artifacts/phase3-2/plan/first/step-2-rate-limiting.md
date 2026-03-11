# Step 2 — Rate Limiting

**Audit findings addressed:** S-6 (no rate limiting on `/login`), S-7 (no global rate limiting)

---

## Purpose

Add `slowapi` rate limiting to protect `/login` from brute-force attacks and to throttle all authenticated endpoints against token abuse.

---

## Deliverables

- `code/backend/requirements.txt` — `slowapi>=0.1.9` added.
- `code/backend/app/core/limiter.py` — new module providing a singleton `Limiter` instance.
- `code/backend/app/main.py` — limiter attached to `app.state`; `RateLimitExceeded` handler registered.
- `code/backend/app/api/auth.py` — `@limiter.limit(...)` decorator on `POST /login`; rate-limit string conditional on `app_env`.

---

## Primary files to change

- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/app/core/limiter.py](code/backend/app/core/limiter.py) *(new file)*
- [code/backend/app/main.py](code/backend/app/main.py)
- [code/backend/app/api/auth.py](code/backend/app/api/auth.py)

---

## Detailed implementation steps

1. **`requirements.txt`** — Add `slowapi>=0.1.9` on a new line (below `PyJWT`).

2. **`app/core/limiter.py` (new file)** — Create a module-level `Limiter` singleton:
   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address
   
   limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
   ```
   The `default_limits=["200/minute"]` applies to all routes that don't have an explicit `@limiter.limit()` decorator. This satisfies S-7 without requiring per-route annotations on every endpoint.

3. **`app/main.py`** — Import `limiter` from `app.core.limiter` and the `slowapi` exception handler:
   ```python
   from slowapi import _rate_limit_exceeded_handler
   from slowapi.errors import RateLimitExceeded
   from app.core.limiter import limiter
   ```
   After `app = FastAPI(...)` and before the routers are included, add:
   ```python
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
   ```
   The built-in `_rate_limit_exceeded_handler` returns a `429 Too Many Requests` JSON response.

4. **`app/api/auth.py`** — Import `limiter`, `Request`, and `get_settings`:
   ```python
   from fastapi import Request
   from app.core.limiter import limiter
   from app.core.config import get_settings
   ```
   Compute the login limit once at module load:
   ```python
   _settings = get_settings()
   _LOGIN_RATE_LIMIT = "5/minute" if _settings.app_env == "prod" else "100/minute"
   ```
   Add the decorator and `request: Request` parameter to the login route:
   ```python
   @router.post("/login")
   @limiter.limit(_LOGIN_RATE_LIMIT)
   async def login(request: Request, payload: LoginRequest, ...):
   ```
   The `request` parameter must be present for `slowapi` to extract the client IP. It does not need to be used in the function body.

---

## Integration & Edge Cases

- **`slowapi` + `default_limits`:** The default limit applies only to routes that are decorated with `@limiter.limit()` OR are processed by the `SlowAPIASGIMiddleware`. Using `app.state.limiter = limiter` (without the middleware) means the default limit is NOT automatically applied to all routes — only explicitly decorated ones. To enforce the global 200/min (S-7), add `SlowAPIASGIMiddleware` to the app instead of, or in addition to, `app.state.limiter`. Consult slowapi docs to confirm the correct approach for the installed version.
- **Test fixture isolation:** The test `conftest.py` creates a new server process per test session. The function-scoped `auth_headers` fixture logs in on every test. With 5/min, a test suite of 76 tests would hit the limit. The `_LOGIN_RATE_LIMIT` conditional (`100/min` in dev) prevents this. Tests must run with `APP_ENV=dev` (the default).
- **IP key function:** Using `get_remote_address` means limits are per-IP. Behind a load balancer, all requests may share the same IP. For production, a forwarded-IP key function may be needed. Document this as a deployment-time note.
- **429 response format:** `_rate_limit_exceeded_handler` returns `{"error": "Rate limit exceeded: N per M"}`. The frontend should handle 429 gracefully (display an error message, not crash).

---

## Acceptance Criteria

1. `POST /login` with 6 rapid requests from the same IP in prod mode (`APP_ENV=prod`) returns 429 on the 6th request.
2. `POST /login` in dev mode (`APP_ENV=dev`) does not return 429 for the first 100 requests/minute.
3. A 429 response body contains a non-empty JSON object (not a raw string).
4. All existing backend tests pass after adding rate limiting: `pytest code/backend/tests/ -q` exits 0.
5. `grep "slowapi" code/backend/requirements.txt` finds a match.
6. `code/backend/app/core/limiter.py` exists and imports without error.

---

## Testing / QA

**Tests to add in `code/backend/tests/test_api.py`:**

- `test_login_rate_limit_in_prod` — Start a local app instance with `APP_ENV=prod`. Send 6 sequential `POST /login` requests with the same (wrong) credentials. Assert the first 5 return 401 and the 6th returns 429.  
  *Note: This test requires either a rate-limit window reset mechanism or a 61-second sleep. Mark with `@pytest.mark.slow` and exclude from default CI run if the sleep is needed.*

```bash
.venv/bin/pytest code/backend/tests/test_api.py -q -k "rate_limit" -m "not slow"
```

**Manual QA checklist:**

1. Install updated requirements: `pip install -r code/backend/requirements.txt`.
2. Confirm `slowapi` is importable: `python -c "import slowapi; print(slowapi.__version__)"`.
3. Start the dev server. Send a valid `POST /login` 10 times in quick succession. Confirm no 429 is returned.
4. Start the server with `APP_ENV=prod` (and a valid `JWT_SECRET`). Use a loop:
   ```bash
   for i in {1..6}; do
     curl -s -o /dev/null -w "%{http_code}\n" \
       -X POST http://127.0.0.1:8001/login \
       -H "Content-Type: application/json" \
       -d '{"username":"x","password":"y"}'
   done
   ```
   Expect: 5× `401`, 1× `429`.

---

## Files touched

- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/app/core/limiter.py](code/backend/app/core/limiter.py)
- [code/backend/app/main.py](code/backend/app/main.py)
- [code/backend/app/api/auth.py](code/backend/app/api/auth.py)

---

## Estimated effort

0.5 dev days

---

## Concurrency & PR strategy

- `Blocking steps:` Blocked until Step 1 merges — this step imports `app_env` from `config.py` which is added in Step 1.
- `Merge Readiness: false` — set to `true` once Step 1 is merged and acceptance criteria are all green.
- `Depends-On: phase-3.2/step-1-jwt-auth-hardening`
- Branch: `phase-3.2/step-2-rate-limiting`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `slowapi` version incompatible with FastAPI version in use | Pin `slowapi>=0.1.9` and test against FastAPI `>=0.100,<0.110`. Review changelog if CI fails. |
| Global default limit unexpectedly throttles heavy test suites | Use `100/minute` for dev; slow/integration tests should use `@pytest.mark.slow` and be excluded from default runs. |
| Behind a reverse proxy, all clients share one IP | Document as a deployment note. See `slowapi` `key_func` customization docs. |

---

## References

- [.github/artifacts/phase3-2/summary/final-report.md](../../summary/final-report.md) — S-6, S-7
- [slowapi documentation](https://slowapi.readthedocs.io/)
- [code/backend/app/api/auth.py](code/backend/app/api/auth.py)
- [code/backend/app/main.py](code/backend/app/main.py)

---

## Author Checklist

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/`
- [x] Manual QA checklist added
- [x] Backup/atomic-write noted (no persistence changes in this step)
