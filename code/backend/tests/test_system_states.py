"""
Integration tests for the SystemState CRUD API.
Requires: running backend server (via conftest.py `server` fixture)
Fixtures: client, auth_headers from conftest.py

NOTE: Tests use large unique future-day offsets to avoid overlap between
states persisted across the session-scoped server. Near-present ranges are
reserved only for tests that require an "active now" state and include cleanup.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.db.session import async_session
from app.models.action_log import ActionLog
from app.models.system_state import SystemState
from sqlalchemy import delete, select


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt(days_offset: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days_offset)).isoformat()


def _create_at(client, auth_headers, start_days: int, end_days: int, **kwargs):
    """POST /system-states with an explicit non-overlapping date window."""
    payload = {
        "modeType": "vacation",
        "startDate": _dt(start_days),
        "endDate": _dt(end_days),
        **kwargs,
    }
    return client.post("/system-states", json=payload, headers=auth_headers)


def _cleanup_active_states(client, auth_headers):
    """Delete all states for this user so pulse tests are isolated."""
    r = client.get("/system-states", headers=auth_headers)
    if r.status_code == 200:
        for state in r.json():
            client.delete(f"/system-states/{state['id']}", headers=auth_headers)


# ---------------------------------------------------------------------------
# Create — each test uses a unique far-future window (no overlaps)
# ---------------------------------------------------------------------------

def test_create_system_state(client, auth_headers):
    # Window: +100 to +107 days
    r = _create_at(client, auth_headers, 100, 107, description="Spring break")
    assert r.status_code == 201
    data = r.json()
    assert data["modeType"] == "vacation"
    assert data["requiresRecovery"] is True
    assert data["userId"] is not None
    assert data["id"] is not None


def test_create_no_auth(client):
    r = client.post(
        "/system-states",
        json={"modeType": "vacation", "startDate": _dt(110), "endDate": _dt(117)},
    )
    assert r.status_code == 401


def test_create_invalid_mode_type(client, auth_headers):
    r = client.post(
        "/system-states",
        json={"modeType": "holiday", "startDate": _dt(120), "endDate": _dt(127)},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_create_end_before_start(client, auth_headers):
    r = client.post(
        "/system-states",
        json={"modeType": "vacation", "startDate": _dt(135), "endDate": _dt(130)},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_create_end_equals_start(client, auth_headers):
    ts = _dt(140)
    r = client.post(
        "/system-states",
        json={"modeType": "leave", "startDate": ts, "endDate": ts},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_create_leave_mode(client, auth_headers):
    # Unique window: +200 to +207 days
    r = _create_at(client, auth_headers, 200, 207, modeType="leave")
    assert r.status_code == 201
    assert r.json()["modeType"] == "leave"


def test_create_mode_type_case_insensitive(client, auth_headers):
    # Unique window: +300 to +307 days
    r = _create_at(client, auth_headers, 300, 307, modeType="VACATION")
    assert r.status_code == 201
    assert r.json()["modeType"] == "vacation"


def test_create_overlapping(client, auth_headers):
    # First: +400 to +420
    _create_at(client, auth_headers, 400, 420)
    # Overlapping: +415 to +425
    r = _create_at(client, auth_headers, 415, 425)
    assert r.status_code == 409


def test_create_null_end_date_then_any_start_overlaps(client, auth_headers):
    # Indefinite state from +500 (no end_date)
    r1 = client.post(
        "/system-states",
        json={"modeType": "vacation", "startDate": _dt(500)},
        headers=auth_headers,
    )
    assert r1.status_code == 201
    # Any range starting after +500 overlaps
    r2 = _create_at(client, auth_headers, 510, 520)
    assert r2.status_code == 409
    # Cleanup indefinite state
    client.delete(f"/system-states/{r1.json()['id']}", headers=auth_headers)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def test_list_states(client, auth_headers):
    _create_at(client, auth_headers, 600, 607)
    r = client.get("/system-states", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_list_states_no_auth(client):
    r = client.get("/system-states")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Active state
# ---------------------------------------------------------------------------

def test_get_active_state_none(client, auth_headers):
    _cleanup_active_states(client, auth_headers)
    r = client.get("/system-states/active", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() is None


def test_get_active_state_exists(client, auth_headers):
    _cleanup_active_states(client, auth_headers)
    # State covering now: started 1 day ago, ends 6 days from now
    r1 = client.post(
        "/system-states",
        json={
            "modeType": "vacation",
            "startDate": _dt(-1),
            "endDate": _dt(6),
            "description": "Active now",
        },
        headers=auth_headers,
    )
    assert r1.status_code == 201
    state_id = r1.json()["id"]

    r = client.get("/system-states/active", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data is not None
    assert data["modeType"] == "vacation"

    # Cleanup
    client.delete(f"/system-states/{state_id}", headers=auth_headers)


def test_active_route_not_shadowed_by_id_route(client, auth_headers):
    """Ensure /active is not treated as a state_id."""
    r = client.get("/system-states/active", headers=auth_headers)
    # Should return 200 (active state or null), NOT 404
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def test_update_state(client, auth_headers):
    create = _create_at(client, auth_headers, 700, 707, description="Original")
    state_id = create.json()["id"]
    r = client.put(
        f"/system-states/{state_id}",
        json={"description": "Mental health break"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["description"] == "Mental health break"


def test_update_state_not_found(client, auth_headers):
    r = client.put(
        "/system-states/nonexistent-xyz",
        json={"description": "X"},
        headers=auth_headers,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def test_delete_state(client, auth_headers):
    create = _create_at(client, auth_headers, 800, 807)
    assert create.status_code == 201, f"Create failed: {create.text}"
    state_id = create.json()["id"]
    r = client.delete(f"/system-states/{state_id}", headers=auth_headers)
    assert r.status_code == 204
    states = client.get("/system-states", headers=auth_headers).json()
    assert all(s["id"] != state_id for s in states)


def test_delete_state_not_found(client, auth_headers):
    r = client.delete("/system-states/nonexistent-xyz", headers=auth_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Pulse integration
# ---------------------------------------------------------------------------

def test_pulse_reflects_active_state(client, auth_headers):
    """Creating a vacation covering now must make pulse return silenceState='paused'."""
    _cleanup_active_states(client, auth_headers)

    r1 = client.post(
        "/system-states",
        json={
            "modeType": "vacation",
            "startDate": _dt(-1),
            "endDate": _dt(6),
        },
        headers=auth_headers,
    )
    assert r1.status_code == 201
    state_id = r1.json()["id"]

    pulse = client.get("/stats/pulse", headers=auth_headers)
    assert pulse.status_code == 200
    assert pulse.json()["silenceState"] == "paused"

    # Cleanup
    client.delete(f"/system-states/{state_id}", headers=auth_headers)


def test_pulse_reverts_after_delete(client, auth_headers):
    """Deleting the active vacation reverts pulse out of 'paused'."""
    _cleanup_active_states(client, auth_headers)

    r1 = client.post(
        "/system-states",
        json={
            "modeType": "vacation",
            "startDate": _dt(-1),
            "endDate": _dt(6),
        },
        headers=auth_headers,
    )
    state_id = r1.json()["id"]
    client.delete(f"/system-states/{state_id}", headers=auth_headers)

    pulse = client.get("/stats/pulse", headers=auth_headers)
    assert pulse.status_code == 200
    assert pulse.json()["silenceState"] != "paused"


# ---------------------------------------------------------------------------
# ActionLog entries
# ---------------------------------------------------------------------------

def test_action_log_entries_created(client, auth_headers):
    _create_at(client, auth_headers, 900, 907)

    async def _check():
        async with async_session() as session:
            result = await session.execute(
                select(ActionLog).where(ActionLog.action_type.like("%/system-states%"))
            )
            return result.scalars().all()

    logs = asyncio.get_event_loop().run_until_complete(_check())
    assert len(logs) >= 1



