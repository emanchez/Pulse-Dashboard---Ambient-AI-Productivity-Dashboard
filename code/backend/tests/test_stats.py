from datetime import datetime, timedelta
import asyncio
from sqlalchemy import delete

from app.db.session import async_session
from app.models.action_log import ActionLog
from app.models.system_state import SystemState
from app.models.user import User


def _auth_headers(client):
    r = client.post("/login", json={"username": "testuser", "password": "testpass"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _clear_tables():
    async def _c():
        async with async_session() as s:
            await s.execute(delete(ActionLog))
            await s.execute(delete(SystemState))
            await s.commit()
    return asyncio.get_event_loop().run_until_complete(_c())


def _insert_action(timestamp, user_id: str | None = None):
    async def _i():
        async with async_session() as s:
            s.add(ActionLog(timestamp=timestamp, action_type="TEST", user_id=user_id))
            await s.commit()
    return asyncio.get_event_loop().run_until_complete(_i())


def _insert_system_state(mode_type, start_date, end_date, user_id: str | None = None):
    async def _i():
        async with async_session() as s:
            s.add(SystemState(mode_type=mode_type, start_date=start_date, end_date=end_date, user_id=user_id))
            await s.commit()
    return asyncio.get_event_loop().run_until_complete(_i())


def test_pulse_requires_auth_returns_401(client):
    r = client.get("/stats/pulse")
    assert r.status_code == 401


def test_pulse_no_actionlog_defaults_to_engaged(client, create_user):
    _clear_tables()
    headers = _auth_headers(client)
    r = client.get("/stats/pulse", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["silenceState"] == "engaged"
    assert data["gapMinutes"] == 0
    assert data["lastActionAt"] is None
    assert data["pausedUntil"] is None


def test_pulse_engaged_recent_action(client, create_user):
    _clear_tables()
    now = datetime.utcnow()
    _insert_action(now - timedelta(minutes=30), user_id=create_user.id)
    headers = _auth_headers(client)
    r = client.get("/stats/pulse", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["silenceState"] == "engaged"
    assert 20 <= data["gapMinutes"] <= 40
    assert data["lastActionAt"] is not None
    assert data["pausedUntil"] is None


def test_pulse_stagnant_old_action(client, create_user):
    _clear_tables()
    _insert_action(datetime.utcnow() - timedelta(hours=72), user_id=create_user.id)
    headers = _auth_headers(client)
    r = client.get("/stats/pulse", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["silenceState"] == "stagnant"
    assert data["gapMinutes"] > 2880


def test_pulse_paused_by_system_state_overrides_stagnant(client, create_user):
    _clear_tables()
    _insert_action(datetime.utcnow() - timedelta(hours=72), user_id=create_user.id)
    end = datetime.utcnow() + timedelta(days=3)
    _insert_system_state("Vacation", datetime.utcnow() - timedelta(days=1), end, user_id=create_user.id)
    headers = _auth_headers(client)
    r = client.get("/stats/pulse", headers=headers)
    data = r.json()
    assert data["silenceState"] == "paused"
    assert data["pausedUntil"] is not None
    assert data["gapMinutes"] > 2880  # pause overrides stagnation in result


def test_pulse_overlapping_systemstate_picks_latest_end_date(client, create_user):
    _clear_tables()
    a_end = datetime.utcnow() + timedelta(days=1)
    b_end = datetime.utcnow() + timedelta(days=5)
    _insert_system_state("Vacation", datetime.utcnow() - timedelta(days=2), a_end, user_id=create_user.id)
    _insert_system_state("Vacation", datetime.utcnow() - timedelta(days=3), b_end, user_id=create_user.id)
    headers = _auth_headers(client)
    r = client.get("/stats/pulse", headers=headers)
    data = r.json()
    assert data["silenceState"] == "paused"
    assert data["pausedUntil"].startswith(b_end.isoformat()[:19])


def test_flow_state_empty(client, auth_headers):
    """Flow state with no logs returns zero values and empty series."""
    r = client.get("/stats/flow-state", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["flowPercent"] == 0
    assert data["changePercent"] == 0
    assert data["windowLabel"] == "Last 6 hours"
    assert data["series"] == []


def test_flow_state_no_auth(client):
    """Flow state without JWT returns 401."""
    r = client.get("/stats/flow-state")
    assert r.status_code == 401


def test_flow_state_schema_shape(client, auth_headers):
    """Flow state always returns correct schema shape."""
    r = client.get("/stats/flow-state", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "flowPercent" in data
    assert "changePercent" in data
    assert "windowLabel" in data
    assert "series" in data
    assert isinstance(data["series"], list)
    assert len(data["series"]) <= 12
    assert 0 <= data["flowPercent"] <= 100


def test_pulse_still_works(client, auth_headers):
    """Existing /stats/pulse endpoint is unaffected."""
    r = client.get("/stats/pulse", headers=auth_headers)
    assert r.status_code == 200
    assert "silenceState" in r.json()