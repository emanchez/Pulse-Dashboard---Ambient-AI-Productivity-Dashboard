import pytest
import asyncio
from sqlalchemy import select


def test_e2e_login_and_tasks_flow(client, create_user):
    # login
    r = client.post("/login", json={"username": "testuser", "password": "testpass"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # me
    r = client.get("/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["username"] == "testuser"

    # list tasks (empty)
    r = client.get("/tasks/", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # create task
    payload = {"name": "Smoke Task"}
    r = client.post("/tasks/", json=payload, headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Smoke Task"
    task_id = data["id"]

    # verify ActionLog entry exists for this action
    from app.db.session import async_session
    from app.models.action_log import ActionLog

    async def _check():
        async with async_session() as session:
            res = await session.execute(select(ActionLog))
            logs = res.scalars().all()
            return any(log.action_type.startswith("POST /tasks") or log.task_id == task_id for log in logs)

    assert asyncio.get_event_loop().run_until_complete(_check())
