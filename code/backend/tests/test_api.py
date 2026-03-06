import pytest
from sqlalchemy import select


def test_missing_sub_claim_returns_401(client):
    """Verify get_current_user rejects tokens with no 'sub' claim (empty string)."""
    from app.core.security import create_access_token

    bad_token = create_access_token(subject="")
    r = client.get("/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert r.status_code == 401


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
            return any(log.action_type.startswith("POST /tasks") or log.task_id == task_id for log in logs)

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

