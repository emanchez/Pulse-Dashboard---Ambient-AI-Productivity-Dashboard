"""
Test fixtures for the Ambient AI Productivity Dashboard.

Two test patterns are used:

1. **In-process async tests** (test_ghost_list.py, test_ai.py, etc.):
   Use `async_session` directly to call service functions.
   No server subprocess. Fast, no cross-process issues.

2. **HTTP integration tests** (test_stats.py, test_sessions.py, test_system_states.py):
   Use `client` fixture which talks to a real uvicorn subprocess.
   `_session_auth_token` logs in ONCE per session (avoids rate-limiter on /login).
   `auth_headers` is a cheap wrapper that returns the cached token dict.
   After any direct DB write, call `_wal_checkpoint(session)` so the subprocess
   connection can see the new rows immediately.

WAL visibility rule: after any direct DB write in the pytest process that must be
visible to the running uvicorn subprocess, call `_wal_checkpoint(session)` before
yielding/returning so SQLite flushes the WAL to the shared DB file.

Rate limiter rule: /login is guarded by slowapi (100 req/min).  Do NOT call
/login inside individual test functions or function-scoped fixtures — always
use the session-scoped `_session_auth_token` fixture instead.

Event loop rule: all synchronous helpers that need async work must call
`asyncio.get_event_loop().run_until_complete()` (not `asyncio.run()`). The
session-scoped `session_event_loop` fixture creates one shared loop that persists
for the entire pytest session, allowing all test files to share the same loop
reference without the RuntimeError 'There is no current event loop'.
"""
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

from sqlalchemy import select, text

from app.db.session import engine, async_session
from app.db.base import Base
from app.models.user import User
from app.models.session_log import SessionLog  # noqa: F401 — register table with Base.metadata
from app.models.manual_report import ManualReport  # noqa: F401 — register table with Base.metadata
from app.models.system_state import SystemState  # noqa: F401 — register table with Base.metadata
from app.models.task import Task  # noqa: F401 — register table with Base.metadata
from app.models.ai_usage import AIUsageLog  # noqa: F401 — register table with Base.metadata
from app.models.synthesis import SynthesisReport  # noqa: F401 — register table with Base.metadata
from app.core.security import get_password_hash


async def _wal_checkpoint(session) -> None:
    """Force a WAL checkpoint so subprocess DB connections see recent writes.

    Call this after any direct-DB write in the pytest process that must be
    immediately visible to the running uvicorn subprocess.

    No-op for non-SQLite databases (PRAGMA is SQLite-only).
    """
    db_url = os.environ.get("DATABASE_URL", "")
    if "sqlite" in db_url:
        await session.execute(text("PRAGMA wal_checkpoint(FULL)"))


# ---------------------------------------------------------------------------
# Session-scoped event loop — shared by all test files
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def session_event_loop():
    """Provide a single shared event loop for the entire pytest session.

    This prevents RuntimeError 'There is no current event loop' that arises
    when test files call asyncio.get_event_loop() after a previous asyncio.run()
    call has closed the loop.  All session-scoped async work and all synchronous
    helper functions share this one loop.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def prepare_database(session_event_loop):
    """Delete any stale test.db and create a fresh schema before the session."""
    async def _prepare():
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
            except OSError:
                pass
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    session_event_loop.run_until_complete(_prepare())
    yield


# ---------------------------------------------------------------------------
# Server subprocess (HTTP integration tests)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Session-scoped auth tokens — login ONCE to avoid rate limiter (100/min)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _session_auth_token(server, session_event_loop):
    """Log in as testuser once per test session and cache the JWT.

    Calling /login for every test hits slowapi's rate limiter (100 req/min)
    when the full suite has 30+ tests that each need auth.  Session-scoping
    this fixture means /login is called exactly once; all tests share the token.
    """
    async def _ensure_user():
        async with async_session() as session:
            existing = await session.execute(select(User).where(User.username == "testuser"))
            if not existing.scalar_one_or_none():
                user = User(username="testuser", hashed_password=get_password_hash("testpass"))
                session.add(user)
                await session.commit()
                await _wal_checkpoint(session)

    session_event_loop.run_until_complete(_ensure_user())

    with httpx.Client(base_url=server) as c:
        r = c.post("/login", json={"username": "testuser", "password": "testpass"})
        assert r.status_code == 200, f"Session login failed: {r.text}"
        return r.json()["access_token"]


@pytest.fixture(scope="session")
def _session_auth_token_b(server, session_event_loop):
    """Log in as testuser2 once per test session (for cross-user isolation tests)."""
    async def _ensure_user():
        async with async_session() as session:
            existing = await session.execute(select(User).where(User.username == "testuser2"))
            if not existing.scalar_one_or_none():
                user = User(username="testuser2", hashed_password=get_password_hash("testpass2"))
                session.add(user)
                await session.commit()
                await _wal_checkpoint(session)

    session_event_loop.run_until_complete(_ensure_user())

    with httpx.Client(base_url=server) as c:
        r = c.post("/login", json={"username": "testuser2", "password": "testpass2"})
        assert r.status_code == 200, f"Session login (user2) failed: {r.text}"
        return r.json()["access_token"]


# ---------------------------------------------------------------------------
# Per-test auth header fixtures (cheap — no HTTP, just wraps cached token)
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_headers(client, _session_auth_token):
    """Return Authorization headers using the session-cached JWT.

    Does NOT call /login (that would hit the rate limiter).  The token is
    minted once by _session_auth_token and reused for every test.
    """
    return {"Authorization": f"Bearer {_session_auth_token}"}


@pytest.fixture
def auth_headers_b(client, _session_auth_token_b):
    """Return Authorization headers for testuser2 (cross-user isolation tests)."""
    return {"Authorization": f"Bearer {_session_auth_token_b}"}


# ---------------------------------------------------------------------------
# create_user — direct DB fixture (in-process async tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def create_user():
    """Upsert testuser and return the User object. Safe to call repeatedly.

    CRITICAL: Uses upsert (never delete+recreate) to preserve the user's UUID.
    Deleting and recreating a user generates a new UUID and orphans all related
    data (tasks, action logs, etc.) — a hard-won lesson from Phase 4.1.
    """
    async def _create():
        async with async_session() as session:
            existing_stmt = select(User).where(User.username == "testuser")
            existing = await session.execute(existing_stmt)
            existing_user = existing.scalar_one_or_none()
            if existing_user:
                # Preserve UUID — only reset password if needed.
                existing_user.hashed_password = get_password_hash("testpass")
                await session.commit()
                await session.refresh(existing_user)
                await _wal_checkpoint(session)
                return existing_user
            user = User(username="testuser", hashed_password=get_password_hash("testpass"))
            session.add(user)
            await session.commit()
            await session.refresh(user)
            await _wal_checkpoint(session)
            return user

    return asyncio.get_event_loop().run_until_complete(_create())
