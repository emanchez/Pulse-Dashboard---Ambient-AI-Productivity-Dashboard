import os
import pytest
import asyncio
import sys
import subprocess
import socket
import time

# Ensure the app package can be imported when running uvicorn from code/backend
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Use a temporary sqlite file for tests
DB_PATH = os.path.join(os.path.dirname(__file__), "test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")

import httpx

from sqlalchemy import select

from app.db.session import engine, async_session
from app.db.base import Base
from app.models.user import User
from app.models.session_log import SessionLog  # noqa: F401 — register table with Base.metadata
from app.models.manual_report import ManualReport  # noqa: F401 — register table with Base.metadata
from app.models.system_state import SystemState  # noqa: F401 — register table with Base.metadata
from app.models.task import Task  # noqa: F401 — register table with Base.metadata
from app.core.security import get_password_hash


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    async def _prepare():
        # Ensure a clean sqlite file for each test session
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
            except OSError:
                pass

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_prepare())
    yield


def _find_free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    addr, port = s.getsockname()
    s.close()
    return port


@pytest.fixture(scope="session")
def server():
    port = _find_free_port()
    env = os.environ.copy()
    # Ensure PYTHONPATH includes the code/backend directory so `app` is importable
    env["PYTHONPATH"] = ROOT
    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)]
    proc = subprocess.Popen(cmd, env=env, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # wait for server to be responsive
    base_url = f"http://127.0.0.1:{port}"
    timeout = 10.0
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{base_url}/health", timeout=1.0)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.1)

    yield base_url

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


@pytest.fixture
def client(server):
    with httpx.Client(base_url=server) as c:
        yield c


@pytest.fixture
def create_user():
    async def _create():
        async with async_session() as session:
            # Delete existing user if any
            existing_stmt = select(User).where(User.username == "testuser")
            existing = await session.execute(existing_stmt)
            existing_user = existing.scalar_one_or_none()
            if existing_user:
                await session.delete(existing_user)
                await session.commit()
            user = User(username="testuser", hashed_password=get_password_hash("testpass"))
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    return asyncio.get_event_loop().run_until_complete(_create())


@pytest.fixture
def auth_headers(client):
    """Create testuser if needed, log in, return Authorization headers."""
    async def _ensure_user():
        async with async_session() as session:
            existing_stmt = select(User).where(User.username == "testuser")
            existing = await session.execute(existing_stmt)
            existing_user = existing.scalar_one_or_none()
            if not existing_user:
                user = User(username="testuser", hashed_password=get_password_hash("testpass"))
                session.add(user)
                await session.commit()

    asyncio.get_event_loop().run_until_complete(_ensure_user())
    r = client.post("/login", json={"username": "testuser", "password": "testpass"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_b(client):
    """Create testuser2 and return its Authorization headers (used for cross-user tests)."""
    async def _ensure_user():
        async with async_session() as session:
            existing_stmt = select(User).where(User.username == "testuser2")
            existing = await session.execute(existing_stmt)
            existing_user = existing.scalar_one_or_none()
            if not existing_user:
                user = User(username="testuser2", hashed_password=get_password_hash("testpass2"))
                session.add(user)
                await session.commit()

    asyncio.get_event_loop().run_until_complete(_ensure_user())
    r = client.post("/login", json={"username": "testuser2", "password": "testpass2"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}