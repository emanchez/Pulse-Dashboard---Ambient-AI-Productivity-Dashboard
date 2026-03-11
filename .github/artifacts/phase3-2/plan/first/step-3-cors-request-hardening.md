# Step 3 — CORS, Request Body Limit & 422 Hardening

**Audit findings addressed:** S-5 (CORS fail-closed), S-13 (request body size limit), S-14 (verbose 422 responses)  
**TODO marker placed for:** S-5 (production CORS origin value is deployment-gated)

---

## Purpose

Harden the request boundary: make the CORS helper fail-closed so localhost origins cannot appear in a non-dev deployment, cap inbound request body size to prevent memory exhaustion via large payloads, and sanitize 422 validation error responses so internal schema structure is not leaked in production.

---

## Deliverables

- `code/backend/app/core/config.py` — `get_cors_origins()` raises `ValueError` if localhost/127.0.0.1 origins are present and `app_env != "dev"`.
- `code/backend/app/main.py` — custom `RequestValidationError` handler returning sanitized 422 body in prod; inbound content-size middleware capping at 512 KB; `# TODO(deploy): S-5` marker.
- `code/backend/requirements.txt` — no new dependency (custom fallback middleware avoids needing a separate package; see edge cases).

---

## Primary files to change

- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [code/backend/app/main.py](code/backend/app/main.py)

---

## Detailed implementation steps

### S-5 — CORS fail-closed

1. **`app/core/config.py`** — In the `Settings` class, convert the `frontend_cors_origins` helper method into a `get_cors_origins()` method (or update the existing one) that, after parsing the comma-separated origins string, validates:
   ```python
   def get_cors_origins(self) -> list[str]:
       origins = [o.strip() for o in self.frontend_cors_origins.split(",")]
       if self.app_env != "dev":
           for o in origins:
               if "localhost" in o or "127.0.0.1" in o:
                   raise ValueError(
                       f"CORS origin '{o}' contains localhost/127.0.0.1. "
                       "Set FRONTEND_CORS_ORIGINS to the production domain."
                   )
       return origins
   ```
   This ensures a misconfigured production deployment fails loudly rather than silently allowing local origins.

2. **`app/main.py`** — Wherever `CORSMiddleware` is added, ensure it calls `settings.get_cors_origins()` (not direct attribute access). Add a `# TODO(deploy): S-5` comment on the line that sets `allow_origins`:
   ```python
   # TODO(deploy): S-5 — Set FRONTEND_CORS_ORIGINS env var to the production domain.
   #               get_cors_origins() will raise ValueError if localhost remains in non-dev config.
   app.add_middleware(
       CORSMiddleware,
       allow_origins=settings.get_cors_origins(),
       ...
   )
   ```

### S-13 — Request body size limit

3. **`app/main.py`** — Check whether the installed version of `starlette` (pinned by FastAPI) includes `starlette.middleware.contentsize.ContentSizeLimitMiddleware`. As of starlette `0.36.x` this middleware does NOT exist. Use a custom ASGI middleware instead:
   ```python
   _MAX_BODY_BYTES = 512 * 1024  # 512 KB
   
   class _ContentSizeLimitMiddleware:
       def __init__(self, app: ASGIApp, max_bytes: int = _MAX_BODY_BYTES) -> None:
           self._app = app
           self._max_bytes = max_bytes
   
       async def __call__(self, scope, receive, send) -> None:
           if scope["type"] == "http":
               body_size = 0
               original_receive = receive
   
               async def limited_receive():
                   nonlocal body_size
                   message = await original_receive()
                   if message["type"] == "http.request":
                       body_size += len(message.get("body", b""))
                       if body_size > self._max_bytes:
                           response = Response(
                               content='{"detail": "Request body too large"}',
                               status_code=413,
                               media_type="application/json",
                           )
                           await response(scope, send_wrapper, send)
                           raise RuntimeError("body too large")
                   return message
   
               await self._app(scope, limited_receive, send)
           else:
               await self._app(scope, receive, send)
   ```
   Register it before `CORSMiddleware`:
   ```python
   app.add_middleware(_ContentSizeLimitMiddleware, max_bytes=_MAX_BODY_BYTES)
   ```
   
   > **Note:** The middleware above is a sketch. The exact ASGI streaming pattern requires careful handling of `more_body` and the `send` callable. Review and test the implementation to ensure it returns the 413 response correctly without leaving the connection in an inconsistent state. If the implementation is fragile, consider a simpler approach: check `Content-Length` header only (not streaming body) as a lightweight pre-flight guard.

### S-14 — Sanitized 422 responses

4. **`app/main.py`** — Add a `RequestValidationError` exception handler that hides field-level detail in prod:
   ```python
   from fastapi.exceptions import RequestValidationError
   from fastapi.encoders import jsonable_encoder
   from starlette.requests import Request as StarletteRequest
   
   @app.exception_handler(RequestValidationError)
   async def validation_exception_handler(request: StarletteRequest, exc: RequestValidationError):
       if settings.app_env != "dev":
           return JSONResponse(status_code=422, content={"detail": "Validation error"})
       # Use jsonable_encoder so Pydantic v2 Url objects in exc.errors() serialize correctly.
       return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})
   ```
   
   > **Critical implementation note:** Do NOT pass `exc.errors()` directly to `JSONResponse` in the dev branch. Pydantic v2's `ValidationError.errors()` may return objects with non-JSON-serializable types (e.g., `Url`). Wrapping with `jsonable_encoder()` converts them to strings. Omitting this causes the handler itself to raise an unhandled exception, which FastAPI returns as a 500, defeating the purpose of the handler.

---

## Integration & Edge Cases

- **CORS middleware order:** The content-size middleware must be added **before** CORS middleware. Starlette applies middleware in reverse registration order (last added = outermost). The recommended order (outermost first) is: content-size → CORS → application.
- **`get_cors_origins()` and startup:** The CORS origins are resolved at app startup (when `add_middleware` is called), not per-request. If `get_cors_origins()` raises, the app crashes at startup with a clear error — this is the intended fail-closed behaviour.
- **`pydantic-settings` v2 and `List[str]` fields:** If `frontend_cors_origins` is typed as `List[str]`, pydantic-settings v2 will attempt to JSON-parse the raw env var string. A comma-separated value is not valid JSON and causes a `SettingsError` at startup. Keep this field typed as `str` and split it inside `get_cors_origins()`. This is a documented hard-won lesson in the project context.
- **Content-size and streaming:** The custom middleware approach may not correctly handle chunked transfer encoding. If issues arise during testing, fall back to a header-only guard:
  ```python
  content_length = request.headers.get("content-length")
  if content_length and int(content_length) > _MAX_BODY_BYTES:
      return JSONResponse(status_code=413, content={"detail": "Request body too large"})
  ```
  This is weaker (attackers can omit the header) but safe enough for a local-first tool.
- **`exc.errors()` serialization — known footgun:** The handler MUST use `jsonable_encoder(exc.errors())` not `exc.errors()` directly. Pydantic v2 returns `InputUrl` objects that `JSONResponse` cannot serialize, producing a 500 instead of 422. This footgun is documented in the project's hard-won lessons.

---

## Acceptance Criteria

1. `POST /tasks` with a missing required field returns 422 (not 500) in both dev and prod modes.
2. In prod mode (`APP_ENV=prod`), the 422 response body is exactly `{"detail": "Validation error"}` (no field names or schema details).
3. In dev mode, the 422 response body includes the full Pydantic error array.
4. Sending a request body larger than 512 KB to any endpoint returns 413.
5. Starting the server with `APP_ENV=prod` and `FRONTEND_CORS_ORIGINS=http://localhost:3000` raises `ValueError` at startup.
6. Starting the server with `APP_ENV=prod` and `FRONTEND_CORS_ORIGINS=https://my-app.example.com` starts successfully.
7. `grep "TODO(deploy): S-5"` finds a match in `code/backend/app/main.py`.
8. All existing backend tests pass: `pytest code/backend/tests/ -q` exits 0.

---

## Testing / QA

**Tests to add in `code/backend/tests/test_api.py`:**

- `test_oversized_request_returns_413` — Send `POST /tasks` with a body of `512 * 1024 + 1` bytes. Assert response is 413.
- `test_validation_error_sanitized_in_prod` — Start the test app with `APP_ENV=prod`. Send `POST /tasks` with a missing `title` field. Assert status 422 and body `== {"detail": "Validation error"}`.
- `test_validation_error_full_in_dev` — Send `POST /tasks` with a missing `title` field in dev mode. Assert status 422 and body `detail` is a list (not a string).

```bash
.venv/bin/pytest code/backend/tests/test_api.py -q -k "oversized or validation_error"
```

**Manual QA checklist:**

1. Start dev server. `POST /tasks` with `{}` body. Confirm 422 with detailed errors.
2. Start server with `APP_ENV=prod JWT_SECRET=prod-secret ...`. Same request. Confirm 422 with `{"detail": "Validation error"}` only.
3. Send an oversized body (use Python or curl with `dd`): `dd if=/dev/zero bs=1024 count=600 | curl -X POST .../tasks -H "Content-Type: application/json" --data-binary @-`. Expect 413.
4. Start with `APP_ENV=prod FRONTEND_CORS_ORIGINS=http://localhost:3000`. Expect startup crash with `ValueError`.

---

## Files touched

- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [code/backend/app/main.py](code/backend/app/main.py)

---

## Estimated effort

0.5–1 dev day

---

## Concurrency & PR strategy

- `Blocking steps:` Blocked until Step 1 merges (requires `app_env` field in `config.py`). Can be developed in parallel with Steps 2, 4, 5.
- `Merge Readiness: false` — set to `true` once Step 1 is merged and all 8 acceptance criteria pass.
- `Depends-On: phase-3.2/step-1-jwt-auth-hardening`
- Branch: `phase-3.2/step-3-cors-request-hardening`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Custom content-size middleware breaks streaming responses | Test with `pytest` against all major endpoint types. If issues arise, fall back to `Content-Length` header-only guard. |
| `exc.errors()` without `jsonable_encoder` causes 500 instead of 422 | Always wrap with `jsonable_encoder(exc.errors())`. This is the documented Pydantic v2 footgun — see hard-won lessons in `copilot-instructions.md`. |
| CORS fail-closed blocks test runs | Tests use `APP_ENV=dev` by default; localhost origins remain valid. No impact on tests. |

---

## References

- [.github/artifacts/phase3-2/summary/final-report.md](../../summary/final-report.md) — S-5, S-13, S-14
- [code/backend/app/main.py](code/backend/app/main.py)
- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- `copilot-instructions.md` — "Hard-Won Lessons" section (pydantic-settings List[str] pitfall; exc.errors() serialization)

---

## Author Checklist

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/`
- [x] Manual QA checklist added
- [x] Backup/atomic-write noted (no persistence changes)
