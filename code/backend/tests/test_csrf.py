"""Regression and unit tests for _CSRFMiddleware.

Background
----------
Phase 4.2 initially implemented double-submit cookie CSRF protection:
  - /login set a readable ``csrf_token`` cookie (non-httpOnly)
  - mutating requests were required to echo its value in ``X-CSRF-Token``
  - the middleware compared cookie value to header value via compare_digest

This broke in production because the frontend (Vercel) and backend (Railway)
run on different domains.  Browser SOP means document.cookie only returns
cookies belonging to the *current* page's domain.  The ``csrf_token`` cookie
was set by the Railway domain; JavaScript on the Vercel domain cannot read it.
``getCsrfToken()`` always returned ``""``, the header was never sent, and every
mutating request received a 403.

Regression captured here so it can never silently re-surface.

Fix
---
Switched to *custom-header CSRF* protection:
  - Backend: verify X-CSRF-Token header is **present and non-empty** (no cookie match)
  - Frontend: always send ``X-CSRF-Token: 1`` (or cookie value if available) on mutations
  - Security: CORS allowlist + browser SOP prevent cross-origin JS from adding
    custom headers without a successful preflight that the server approves.
    A present X-CSRF-Token is therefore proof of same-origin intent.

Test organisation
-----------------
TestCSRFMiddlewareProd          -- CSRF enforcement active (app_env="prod")
TestCSRFMiddlewareDev           -- CSRF completely disabled in dev mode
TestCSRFRegressionAiSynthesis   -- explicit regression for the reported 403 on
                                   POST /ai/synthesis in production

Note on test client
-------------------
starlette.testclient.TestClient (0.36.3) has a version incompatibility with
httpx >=0.27 where it tries to pass ``app=`` as a keyword to httpx.Client,
which is no longer accepted.  Tests here use httpx.AsyncClient with
ASGITransport instead, wrapped in a thin _SyncASGIClient helper.
"""
from __future__ import annotations

import asyncio
import os

import httpx
import pytest

# Point at the shared test DB (must be set before any app import)
DB_PATH = os.path.join(os.path.dirname(__file__), "test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")

from app.core.config import get_settings  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.db.session import async_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from sqlalchemy import select  # noqa: E402


# ---------------------------------------------------------------------------
# In-process sync HTTP client (bypasses starlette/httpx version mismatch)
# ---------------------------------------------------------------------------

class _SyncASGIClient:
    """Thin synchronous wrapper around httpx.AsyncClient + ASGITransport.

    Makes requests directly against the ASGI app (no subprocess, no port).
    Allows prod-mode CSRF tests by mutating get_settings() in-process before
    calling the middleware dispatch path.
    """

    def __init__(self) -> None:
        self._transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        async def _req() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport,
                base_url="http://testserver",
            ) as client:
                return await client.request(method, path, **kwargs)

        return asyncio.get_event_loop().run_until_complete(_req())

    def get(self, path: str, **kwargs) -> httpx.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> httpx.Response:
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> httpx.Response:
        return self._request("DELETE", path, **kwargs)

    def patch(self, path: str, **kwargs) -> httpx.Response:
        return self._request("PATCH", path, **kwargs)

    def options(self, path: str, **kwargs) -> httpx.Response:
        return self._request("OPTIONS", path, **kwargs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _get_or_create_testuser() -> User:
    """Upsert testuser and return the ORM object.  Safe to call multiple times."""
    async def _upsert():
        async with async_session() as session:
            stmt = select(User).where(User.username == "testuser")
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                user = User(
                    username="testuser",
                    hashed_password=get_password_hash("testpass"),
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            return user

    return _run(_upsert())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def prod_settings():
    """Temporarily switch app_env to 'prod' so _CSRFMiddleware is active.

    Restores the original value on teardown even if the test raises.
    The Settings instance is cached (lru_cache) so mutating it in-process
    affects all code paths that call get_settings() -- including middleware.
    """
    settings = get_settings()
    original = settings.app_env
    settings.app_env = "prod"
    yield settings
    settings.app_env = original


@pytest.fixture(scope="module")
def valid_jwt() -> str:
    """Return a signed JWT for testuser (no HTTP round-trip needed)."""
    user = _get_or_create_testuser()
    return create_access_token(subject=str(user.id))


@pytest.fixture()
def client() -> _SyncASGIClient:
    """Return a fresh in-process ASGI test client."""
    return _SyncASGIClient()


# ---------------------------------------------------------------------------
# CSRF enforcement -- production mode
# ---------------------------------------------------------------------------

class TestCSRFMiddlewareProd:
    """_CSRFMiddleware must block mutations without X-CSRF-Token in prod mode."""

    def test_post_without_csrf_header_returns_403(self, prod_settings, client):
        """POST to a non-exempt endpoint without X-CSRF-Token -> 403."""
        r = client.post("/tasks/", json={"name": "no-csrf"})
        assert r.status_code == 403
        assert r.json()["detail"] == "CSRF validation failed"

    def test_post_with_empty_csrf_header_returns_403(self, prod_settings, client):
        """X-CSRF-Token present but empty string -> still 403.

        Empty header is not a valid proof-of-intent sentinel.
        """
        r = client.post(
            "/tasks/",
            json={"name": "empty-csrf"},
            headers={"X-CSRF-Token": ""},
        )
        assert r.status_code == 403
        assert "CSRF" in r.json()["detail"]

    def test_post_with_whitespace_only_csrf_header_returns_403(self, prod_settings, client):
        """X-CSRF-Token containing only whitespace -> 403.

        Whitespace-only should be treated the same as absent/empty.
        """
        r = client.post(
            "/tasks/",
            json={"name": "whitespace-csrf"},
            headers={"X-CSRF-Token": "   "},
        )
        assert r.status_code == 403

    def test_post_with_csrf_header_passes_middleware(self, prod_settings, client, valid_jwt):
        """POST with non-empty X-CSRF-Token passes CSRF -- must not return 403 CSRF error."""
        r = client.post(
            "/tasks/",
            json={"name": "csrf-ok"},
            headers={
                "Authorization": f"Bearer {valid_jwt}",
                "X-CSRF-Token": "1",
            },
        )
        # CSRF passed -- any outcome except a CSRF 403 is acceptable
        if r.status_code == 403:
            body = r.json()
            assert "CSRF" not in body.get("detail", ""), (
                f"CSRF middleware blocked a request that included X-CSRF-Token: {r.text}"
            )

    def test_put_without_csrf_header_returns_403(self, prod_settings, client):
        """PUT is a mutating method -- also guarded by CSRF."""
        r = client.put("/tasks/some-id", json={"name": "nope"})
        assert r.status_code == 403

    def test_delete_without_csrf_header_returns_403(self, prod_settings, client):
        """DELETE is a mutating method -- also guarded by CSRF."""
        r = client.delete("/tasks/some-id")
        assert r.status_code == 403

    def test_patch_without_csrf_header_returns_403(self, prod_settings, client):
        """PATCH is a mutating method -- also guarded by CSRF."""
        r = client.patch("/reports/some-id", json={"status": "archived"})
        assert r.status_code == 403

    def test_get_without_csrf_header_passes(self, prod_settings, client, valid_jwt):
        """GET is a safe method -- CSRF never applies."""
        r = client.get(
            "/tasks/",
            headers={"Authorization": f"Bearer {valid_jwt}"},
        )
        # CSRF must not have fired (200 or other are expected; 403 CSRF is wrong)
        if r.status_code == 403:
            assert "CSRF" not in r.json().get("detail", ""), (
                "CSRF middleware incorrectly blocked a GET request"
            )

    def test_options_without_csrf_header_passes(self, prod_settings, client):
        """OPTIONS is a safe method (CORS preflight) -- never blocked by CSRF."""
        r = client.options("/tasks/")
        assert r.status_code != 403

    def test_login_exempt_from_csrf(self, prod_settings, client):
        """/login is explicitly exempt -- must not be blocked (no cookie yet)."""
        r = client.post("/login", json={"username": "x", "password": "x"})
        # 401 Unauthorized expected (bad creds); 403 CSRF would be a bug
        assert r.status_code != 403, (
            f"/login must be exempt from CSRF but got 403: {r.text}"
        )

    def test_logout_exempt_from_csrf(self, prod_settings, client):
        """/logout is explicitly exempt."""
        r = client.post("/logout")
        assert r.status_code != 403

    def test_health_exempt_from_csrf(self, prod_settings, client):
        """/health is explicitly exempt."""
        r = client.get("/health")
        assert r.status_code == 200

    def test_csrf_value_arbitrary_string_accepted(self, prod_settings, client, valid_jwt):
        """X-CSRF-Token value is not validated against a secret -- any non-empty string works."""
        r = client.post(
            "/tasks/",
            json={"name": "arbitrary-csrf"},
            headers={
                "Authorization": f"Bearer {valid_jwt}",
                "X-CSRF-Token": "not-a-secret-just-a-sentinel",
            },
        )
        if r.status_code == 403:
            assert "CSRF" not in r.json().get("detail", ""), (
                "Arbitrary non-empty X-CSRF-Token value must be accepted"
            )


# ---------------------------------------------------------------------------
# CSRF disabled in dev mode
# ---------------------------------------------------------------------------

class TestCSRFMiddlewareDev:
    """_CSRFMiddleware must be fully disabled in dev mode."""

    def test_post_without_csrf_passes_in_dev(self, client, valid_jwt):
        """Dev mode: POST without X-CSRF-Token must not be blocked by CSRF."""
        settings = get_settings()
        assert settings.app_env == "dev", (
            "Pre-condition failed: test assumes app_env=dev (the default)"
        )
        r = client.post(
            "/tasks/",
            json={"name": "dev-no-csrf"},
            headers={"Authorization": f"Bearer {valid_jwt}"},
        )
        # Must not receive a CSRF 403 -- any other status is acceptable
        if r.status_code == 403:
            assert "CSRF" not in r.json().get("detail", ""), (
                f"CSRF middleware should not fire in dev: {r.text}"
            )

    def test_ai_synthesis_without_csrf_passes_in_dev(self, client, valid_jwt):
        """Dev mode: POST /ai/synthesis without X-CSRF-Token must not be CSRF-blocked."""
        settings = get_settings()
        assert settings.app_env == "dev"
        r = client.post(
            "/ai/synthesis",
            json={},
            headers={"Authorization": f"Bearer {valid_jwt}"},
        )
        if r.status_code == 403:
            assert "CSRF" not in r.json().get("detail", ""), (
                f"CSRF must not fire in dev mode: {r.text}"
            )


# ---------------------------------------------------------------------------
# Regression: POST /ai/synthesis returned 403 in production
# ---------------------------------------------------------------------------

class TestCSRFRegressionAiSynthesis:
    """Explicit regression tests for the synthesis-endpoint 403 bug.

    Root cause: double-submit cookie CSRF required reading csrf_token from
    document.cookie.  In production (cross-origin), getCsrfToken() always
    returned '' because the cookie belonged to the backend domain (Railway),
    not the frontend domain (Vercel).  The X-CSRF-Token header was never sent,
    and the backend returned 403 on every POST /ai/synthesis request.
    """

    def test_synthesis_without_csrf_header_returns_403_in_prod(
        self, prod_settings, client, valid_jwt
    ):
        """Regression: POST /ai/synthesis WITHOUT X-CSRF-Token -> 403 in prod.

        This test documents the exact failure mode that was occurring in
        production.  It must ALWAYS pass to confirm the middleware fix holds.
        """
        r = client.post(
            "/ai/synthesis",
            json={},
            headers={"Authorization": f"Bearer {valid_jwt}"},
            # Note: deliberately NO X-CSRF-Token header
        )
        assert r.status_code == 403, (
            f"Expected 403 when X-CSRF-Token is absent in prod mode, got {r.status_code}"
        )
        assert r.json()["detail"] == "CSRF validation failed"

    def test_synthesis_with_csrf_header_not_blocked_by_csrf_in_prod(
        self, prod_settings, client, valid_jwt
    ):
        """Regression fix: POST /ai/synthesis WITH X-CSRF-Token: 1 -> CSRF passes.

        The fix: frontend always sends X-CSRF-Token: 1 (or any non-empty value).
        Backend verifies presence only.  This succeeds cross-origin because the
        frontend sends the header explicitly (not via cookie read), and CORS
        prevents cross-origin JS from adding custom headers without preflight.
        """
        r = client.post(
            "/ai/synthesis",
            json={},
            headers={
                "Authorization": f"Bearer {valid_jwt}",
                "X-CSRF-Token": "1",
            },
        )
        # CSRF passed -- expect 202 (synthesis accepted) or 503 (AI disabled in test env)
        # but NOT 403 CSRF
        assert r.status_code != 403, (
            f"POST /ai/synthesis with X-CSRF-Token present must not return 403, "
            f"got {r.status_code}: {r.text}"
        )
        allowed_statuses = {202, 409, 429, 503, 504}
        assert r.status_code in allowed_statuses, (
            f"Unexpected status after CSRF pass for /ai/synthesis: {r.status_code}: {r.text}"
        )

    def test_other_ai_endpoints_also_unblocked_with_csrf_header(
        self, prod_settings, client, valid_jwt
    ):
        """All /ai/* mutating endpoints pass CSRF when header is present."""
        endpoints = [
            ("/ai/suggest-tasks", {}),
            ("/ai/co-plan", {"reportId": "nonexistent"}),
        ]
        for path, body in endpoints:
            r = client.post(
                path,
                json=body,
                headers={
                    "Authorization": f"Bearer {valid_jwt}",
                    "X-CSRF-Token": "1",
                },
            )
            assert r.status_code != 403, (
                f"POST {path} with X-CSRF-Token must not return 403, "
                f"got {r.status_code}: {r.text}"
            )

    def test_old_cookie_approach_is_not_required(
        self, prod_settings, client, valid_jwt
    ):
        """Backwards-compat: X-CSRF-Token header without csrf_token cookie works.

        Under the old double-submit pattern, the absence of the cookie would
        cause compare_digest to fail even if the header was present.
        Under the new pattern, the cookie is irrelevant -- header presence is all
        that matters.
        """
        # Fresh _SyncASGIClient has no cookie jar -- csrf_token cookie absent
        r = client.post(
            "/ai/synthesis",
            json={},
            headers={
                "Authorization": f"Bearer {valid_jwt}",
                "X-CSRF-Token": "any-value",
                # no Cookie header with csrf_token
            },
        )
        assert r.status_code != 403, (
            f"CSRF must not require a cookie -- header-only approach must work, "
            f"got {r.status_code}: {r.text}"
        )
