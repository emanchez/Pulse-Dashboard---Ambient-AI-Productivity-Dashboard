"""Tests for session management endpoints."""
import pytest


def test_active_session_empty(client, auth_headers):
    # Stop any lingering active session first
    client.post("/sessions/stop", headers=auth_headers)
    r = client.get("/sessions/active", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() is None


def test_start_session(client, auth_headers):
    # Ensure clean state
    client.post("/sessions/stop", headers=auth_headers)
    r = client.post("/sessions/start", json={"taskName": "UI Redesign", "goalMinutes": 60}, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["taskName"] == "UI Redesign"
    assert data["goalMinutes"] == 60
    assert data["endedAt"] is None
    assert data["elapsedMinutes"] >= 0
    # Clean up
    client.post("/sessions/stop", headers=auth_headers)


def test_start_idempotent(client, auth_headers):
    # Ensure clean state
    client.post("/sessions/stop", headers=auth_headers)
    r1 = client.post("/sessions/start", json={"taskName": "UI Redesign"}, headers=auth_headers)
    r2 = client.post("/sessions/start", json={"taskName": "UI Redesign"}, headers=auth_headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
    # Clean up
    client.post("/sessions/stop", headers=auth_headers)


def test_active_session_after_start(client, auth_headers):
    client.post("/sessions/stop", headers=auth_headers)
    client.post("/sessions/start", json={"taskName": "Active Test"}, headers=auth_headers)
    r = client.get("/sessions/active", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data is not None
    assert data["taskName"] == "Active Test"
    assert data["elapsedMinutes"] >= 0
    client.post("/sessions/stop", headers=auth_headers)


def test_stop_session(client, auth_headers):
    client.post("/sessions/stop", headers=auth_headers)
    client.post("/sessions/start", json={"taskName": "UI Redesign"}, headers=auth_headers)
    r = client.post("/sessions/stop", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["endedAt"] is not None


def test_active_session_empty_after_stop(client, auth_headers):
    client.post("/sessions/stop", headers=auth_headers)
    client.post("/sessions/start", json={"taskName": "Temp"}, headers=auth_headers)
    client.post("/sessions/stop", headers=auth_headers)
    r = client.get("/sessions/active", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() is None


def test_stop_no_session_404(client, auth_headers):
    # Ensure no active session
    client.post("/sessions/stop", headers=auth_headers)
    r = client.post("/sessions/stop", headers=auth_headers)
    assert r.status_code == 404
    assert "No active session" in r.json()["detail"]


def test_start_no_auth_401(client):
    r = client.post("/sessions/start", json={"taskName": "x"})
    assert r.status_code == 401


def test_start_blank_name_400(client, auth_headers):
    r = client.post("/sessions/start", json={"taskName": ""}, headers=auth_headers)
    assert r.status_code == 400
