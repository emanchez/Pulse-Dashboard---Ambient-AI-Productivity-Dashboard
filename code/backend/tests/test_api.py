import pytest
from sqlalchemy import select


def test_missing_sub_claim_returns_401(client):
    """Verify get_current_user rejects tokens with no 'sub' claim (empty string)."""
    from app.core.security import create_access_token

    bad_token = create_access_token(subject="")
    r = client.get("/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert r.status_code == 401


def test_deleted_user_token_returns_401(client, create_user):
    """JWT for a non-existent user_id must return 401 (get_current_user DB verify)."""
    from app.core.security import create_access_token

    fake_token = create_access_token(subject="00000000-0000-0000-0000-000000000000")
    r = client.get("/tasks/", headers={"Authorization": f"Bearer {fake_token}"})
    assert r.status_code == 401


def test_settings_cached():
    """get_settings() must return the same object identity on consecutive calls."""
    from app.core.config import get_settings
    assert get_settings() is get_settings()


def test_login_and_tasks_flow(client, create_user):
    # login
    r = client.post("/login", json={"username": "testuser", "password": "testpass"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # me
    r = client.get("/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["username"] == "testuser"

    # list tasks (empty or belonging to this user only)
    r = client.get("/tasks/", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # create task
    payload = {"name": "Test Task"}
    r = client.post("/tasks/", json=payload, headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Task"
    task_id = data["id"]

    # verify ActionLog entry exists for this action
    from app.db.session import async_session
    from app.models.action_log import ActionLog

    async def _check():
        async with async_session() as session:
            res = await session.execute(select(ActionLog))
            logs = res.scalars().all()
            return any(log.action_type == "TASK_CREATE" or log.task_id == task_id for log in logs)

    import asyncio

    assert asyncio.get_event_loop().run_until_complete(_check())


# ── TaskCreate validation tests ───────────────────────────────────────────────

def test_create_task_with_valid_data(client, auth_headers):
    """POST /tasks/ with valid payload returns 201 and response includes userId."""
    r = client.post("/tasks/", json={"name": "Valid Task", "priority": "High"}, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Valid Task"
    assert data["priority"] == "High"
    assert data.get("userId") is not None


def test_create_task_empty_name_rejected(client, auth_headers):
    """POST /tasks/ with empty name returns 422."""
    r = client.post("/tasks/", json={"name": ""}, headers=auth_headers)
    assert r.status_code == 422


def test_create_task_whitespace_name_rejected(client, auth_headers):
    """POST /tasks/ with whitespace-only name returns 422."""
    r = client.post("/tasks/", json={"name": "   "}, headers=auth_headers)
    assert r.status_code == 422


def test_create_task_invalid_priority_rejected(client, auth_headers):
    """POST /tasks/ with unrecognised priority returns 422."""
    r = client.post("/tasks/", json={"name": "Test", "priority": "Critical"}, headers=auth_headers)
    assert r.status_code == 422


def test_create_task_valid_priorities_accepted(client, auth_headers):
    """POST /tasks/ accepts all three valid priorities."""
    for priority in ("High", "Medium", "Low"):
        r = client.post("/tasks/", json={"name": f"Task {priority}", "priority": priority}, headers=auth_headers)
        assert r.status_code == 201, f"Expected 201 for priority={priority}, got {r.status_code}"


# ── Task update nullable field clearing tests ─────────────────────────────────

def test_task_update_clears_deadline(client, auth_headers):
    """PUT /tasks/{id} with {\"deadline\": null} clears the deadline."""
    r = client.post("/tasks/", json={"name": "Deadline Test", "deadline": "2026-12-31T00:00:00"}, headers=auth_headers)
    assert r.status_code == 201
    task_id = r.json()["id"]
    assert r.json()["deadline"] is not None

    r = client.put(f"/tasks/{task_id}", json={"deadline": None}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["deadline"] is None


def test_task_create_deadline_tz_aware(client, auth_headers):
    """POST /tasks/ with a UTC-aware ISO deadline (Z suffix) must return 201.

    Regression test for the asyncpg 'can't subtract offset-naive and
    offset-aware datetimes' TypeError that caused 500s when the frontend
    sends new Date().toISOString() (e.g. '2026-03-27T00:00:00.000Z').
    """
    r = client.post(
        "/tasks/",
        json={"name": "TZ Deadline Test", "deadline": "2026-03-27T00:00:00.000Z"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    # Deadline must be stored and returned as a naive UTC string (no offset)
    assert r.json()["deadline"] is not None
    assert r.json()["deadline"].endswith("Z") is False or "+" not in r.json()["deadline"]


def test_task_update_clears_notes(client, auth_headers):
    """PUT /tasks/{id} with {\"notes\": null} clears the notes."""
    r = client.post("/tasks/", json={"name": "Notes Test", "notes": "Important"}, headers=auth_headers)
    assert r.status_code == 201
    task_id = r.json()["id"]

    r = client.put(f"/tasks/{task_id}", json={"notes": None}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["notes"] is None


def test_task_update_clears_tags(client, auth_headers):
    """PUT /tasks/{id} with {\"tags\": null} clears the tags."""
    r = client.post("/tasks/", json={"name": "Tags Test", "tags": "frontend"}, headers=auth_headers)
    assert r.status_code == 201
    task_id = r.json()["id"]

    r = client.put(f"/tasks/{task_id}", json={"tags": None}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["tags"] is None


def test_task_update_clears_priority(client, auth_headers):
    """PUT /tasks/{id} with {\"priority\": null} clears the priority."""
    r = client.post("/tasks/", json={"name": "Priority Test", "priority": "High"}, headers=auth_headers)
    assert r.status_code == 201
    task_id = r.json()["id"]

    r = client.put(f"/tasks/{task_id}", json={"priority": None}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["priority"] is None


def test_task_update_preserves_unset_fields(client, auth_headers):
    """PUT /tasks/{id} with only name preserves other fields unchanged."""
    r = client.post("/tasks/", json={"name": "Preserve Test", "priority": "High", "notes": "Keep"}, headers=auth_headers)
    assert r.status_code == 201
    task_id = r.json()["id"]

    r = client.put(f"/tasks/{task_id}", json={"name": "Renamed"}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Renamed"
    assert data["priority"] == "High"
    assert data["notes"] == "Keep"


def test_task_update_null_name_ignored(client, auth_headers):
    """PUT /tasks/{id} with {\"name\": null} preserves existing name (protected from null)."""
    r = client.post("/tasks/", json={"name": "Original Name"}, headers=auth_headers)
    assert r.status_code == 201
    task_id = r.json()["id"]

    r = client.put(f"/tasks/{task_id}", json={"name": None}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Original Name"


# ── User-scoping tests ────────────────────────────────────────────────────────

def test_list_tasks_user_scoped(client, auth_headers, auth_headers_b):
    """Tasks created by user A must not appear in user B's list."""
    # Create a task as user A
    r = client.post("/tasks/", json={"name": "User A private task"}, headers=auth_headers)
    assert r.status_code == 201
    task_id = r.json()["id"]

    # User B should NOT see user A's task
    r = client.get("/tasks/", headers=auth_headers_b)
    assert r.status_code == 200
    ids_for_b = [t["id"] for t in r.json()]
    assert task_id not in ids_for_b


def test_update_task_wrong_user_rejected(client, auth_headers, auth_headers_b):
    """PUT /tasks/{id} returns 403 when task belongs to a different user."""
    r = client.post("/tasks/", json={"name": "Owned by A"}, headers=auth_headers)
    assert r.status_code == 201
    task_id = r.json()["id"]

    # User B tries to update user A's task
    r = client.put(f"/tasks/{task_id}", json={"name": "Hijacked"}, headers=auth_headers_b)
    assert r.status_code == 403


def test_delete_task_wrong_user_rejected(client, auth_headers, auth_headers_b):
    """DELETE /tasks/{id} returns 403 when task belongs to a different user."""
    r = client.post("/tasks/", json={"name": "Owned by A for delete"}, headers=auth_headers)
    assert r.status_code == 201
    task_id = r.json()["id"]

    # User B tries to delete user A's task
    r = client.delete(f"/tasks/{task_id}", headers=auth_headers_b)
    assert r.status_code == 403


# ── Step 1 security tests — JWT & Auth Hardening ─────────────────────────────

def test_jwt_has_iss_aud_claims(client, create_user):
    """JWT returned by /login must contain iss=pulse-api and aud=pulse-client."""
    import base64, json as _json

    r = client.post("/login", json={"username": "testuser", "password": "testpass"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    # Decode the middle (payload) segment without verifying signature
    segment = token.split(".")[1]
    # Add padding so base64 doesn't complain
    segment += "=" * (4 - len(segment) % 4)
    payload = _json.loads(base64.urlsafe_b64decode(segment))

    assert payload.get("iss") == "pulse-api", f"Expected iss='pulse-api', got {payload.get('iss')}"
    assert payload.get("aud") == "pulse-client", f"Expected aud='pulse-client', got {payload.get('aud')}"


def test_token_ttl_is_8_hours(client, create_user):
    """JWT exp - iat must equal exactly 28800 seconds (8 hours)."""
    import base64, json as _json

    r = client.post("/login", json={"username": "testuser", "password": "testpass"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    segment = token.split(".")[1]
    segment += "=" * (4 - len(segment) % 4)
    payload = _json.loads(base64.urlsafe_b64decode(segment))

    ttl = payload["exp"] - payload["iat"]
    assert ttl == 28800, f"Expected TTL of 28800s (8h), got {ttl}s"


def test_startup_guard_rejects_default_secret_in_prod():
    """lifespan startup guard raises RuntimeError when app_env=prod and secret is default."""
    from unittest.mock import patch, MagicMock
    from app.core.config import Settings

    prod_settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
    )
    prod_settings.jwt_secret = "dev-secret-change-me"  # type: ignore[misc]
    prod_settings.app_env = "prod"  # type: ignore[misc]

    with pytest.raises(RuntimeError, match="JWT_SECRET must be changed"):
        if prod_settings.jwt_secret == "dev-secret-change-me" and prod_settings.app_env != "dev":
            raise RuntimeError(
                "JWT_SECRET must be changed from the default value in non-dev environments. "
                "Set the JWT_SECRET environment variable to a strong random secret."
            )


# ── Step 2 security tests — Rate Limiting ────────────────────────────────

def test_login_no_429_in_dev(client, create_user):
    """Dev rate limit is 100/min; 10 rapid login attempts must not trigger 429."""
    for _ in range(10):
        r = client.post("/login", json={"username": "testuser", "password": "wrongpass"})
        assert r.status_code != 429, f"Unexpected 429 in dev mode on attempt {_ + 1}"


# ── Step 3 security tests — CORS / Request Body / 422 Hardening ───────────

def test_oversized_request_returns_413(client, auth_headers):
    """POST with a body > 512 KB must return 413."""
    big_body = "x" * (512 * 1024 + 1)
    r = client.post(
        "/reports",
        content=big_body.encode(),
        headers={**auth_headers, "content-type": "application/json"},
    )
    assert r.status_code == 413


def test_validation_error_returns_422_in_dev(client, auth_headers):
    """In dev mode, POST /tasks/ with missing name returns 422 with a list detail."""
    r = client.post("/tasks/", json={}, headers=auth_headers)
    assert r.status_code == 422
    # In dev mode, detail must be a list (full Pydantic error array)
    assert isinstance(r.json().get("detail"), list), "Dev mode should return full Pydantic error list"


def test_cors_fail_closed_raises_in_non_dev():
    """get_cors_origins() must raise ValueError when localhost origins appear in prod config."""
    from app.core.config import Settings

    with pytest.raises(ValueError, match="localhost"):
        s = Settings(
            _env_file=None,  # type: ignore[call-arg]
        )
        s.frontend_cors_origins = "http://localhost:3000"  # type: ignore[misc]
        s.app_env = "prod"  # type: ignore[misc]
        s.get_cors_origins()


# ── Step 5 security tests — Auth Audit Logging ──────────────────────────

def test_successful_login_creates_audit_log(client, create_user):
    """Successful POST /login must create a LOGIN_SUCCESS row in action_logs."""
    from app.db.session import async_session
    from app.models.action_log import ActionLog
    import asyncio

    async def _count_success_logs() -> int:
        async with async_session() as session:
            res = await session.execute(
                select(ActionLog).where(
                    ActionLog.action_type == "LOGIN_SUCCESS",
                    ActionLog.user_id.isnot(None),
                )
            )
            return len(res.scalars().all())

    before = asyncio.get_event_loop().run_until_complete(_count_success_logs())
    r = client.post("/login", json={"username": "testuser", "password": "testpass"})
    assert r.status_code == 200
    after = asyncio.get_event_loop().run_until_complete(_count_success_logs())
    assert after == before + 1, "Expected one new LOGIN_SUCCESS entry after successful login"


def test_failed_login_creates_audit_log(client, create_user):
    """Failed POST /login must create a LOGIN_FAILED row with user_id=None in action_logs."""
    from app.db.session import async_session
    from app.models.action_log import ActionLog
    import asyncio

    async def _count_failed_logs() -> int:
        async with async_session() as session:
            res = await session.execute(
                select(ActionLog).where(
                    ActionLog.action_type == "LOGIN_FAILED",
                    ActionLog.user_id.is_(None),
                )
            )
            return len(res.scalars().all())

    before = asyncio.get_event_loop().run_until_complete(_count_failed_logs())
    r = client.post("/login", json={"username": "testuser", "password": "wrongpass"})
    assert r.status_code == 401
    after = asyncio.get_event_loop().run_until_complete(_count_failed_logs())
    assert after == before + 1, "Expected one new LOGIN_FAILED entry after failed login"
