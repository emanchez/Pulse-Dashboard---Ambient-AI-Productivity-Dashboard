"""
Integration tests for the ManualReport CRUD API.
Requires: running backend server (via conftest.py `server` fixture)
Fixtures: client, auth_headers from conftest.py
"""
import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import async_session
from app.models.action_log import ActionLog
from sqlalchemy import select


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create(client, auth_headers, **kwargs):
    payload = {"title": "Test Report", "body": "Hello world foo bar", **kwargs}
    return client.post("/reports", json=payload, headers=auth_headers)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def test_create_report(client, auth_headers):
    r = _create(client, auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Test Report"
    assert data["wordCount"] == 4  # "Hello world foo bar"
    assert data["status"] == "published"
    assert data["userId"] is not None
    assert data["id"] is not None
    assert data["createdAt"] is not None
    assert data["updatedAt"] is not None


def test_create_report_no_auth(client):
    r = client.post("/reports", json={"title": "Test", "body": "Hello"})
    assert r.status_code == 401


def test_create_report_empty_title(client, auth_headers):
    r = client.post("/reports", json={"title": "", "body": "Hello"}, headers=auth_headers)
    assert r.status_code == 422


def test_create_report_title_whitespace(client, auth_headers):
    r = client.post("/reports", json={"title": "   ", "body": "Hello"}, headers=auth_headers)
    assert r.status_code == 422


def test_create_report_invalid_status(client, auth_headers):
    r = _create(client, auth_headers, status="nonexistent")
    assert r.status_code == 422


def test_create_report_archived_status(client, auth_headers):
    """Creating a report with status='archived' is now valid."""
    r = _create(client, auth_headers, status="archived")
    assert r.status_code == 201
    assert r.json()["status"] == "archived"


def test_create_report_draft_status(client, auth_headers):
    r = _create(client, auth_headers, status="draft")
    assert r.status_code == 201
    assert r.json()["status"] == "draft"


def test_create_with_tags(client, auth_headers):
    r = _create(client, auth_headers, tags=["Engineering", "Strategy"])
    assert r.status_code == 201
    data = r.json()
    assert data["tags"] == ["Engineering", "Strategy"]


def test_create_with_invalid_task_ids(client, auth_headers):
    r = _create(client, auth_headers, associatedTaskIds=["nonexistent-task-id"])
    assert r.status_code == 400


# ── Step 4 security tests — Input Sanitization ─────────────────────────

def test_html_stripped_from_title(client, auth_headers):
    """HTML tags in title must be stripped on create."""
    r = client.post(
        "/reports",
        json={"title": "<b>hello</b>", "body": "body text"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["title"] == "hello"


def test_html_stripped_from_body(client, auth_headers):
    """HTML tags in body must be stripped on create.

    bleach.clean(tags=[], strip=True) removes tag markers but preserves text
    content between tags — '<script>alert(1)</script>text' becomes 'alert(1)text'.
    The content cannot execute because the <script> tags are absent, and React
    escapes all output by default.
    """
    r = client.post(
        "/reports",
        json={"title": "clean title", "body": "<script>alert(1)</script>safe text"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    # bleach strips the <script>…</script> markers but keeps the inner text.
    assert r.json()["body"] == "alert(1)safe text"
    # Crucially, the stored body must NOT contain any HTML tag markers.
    assert "<script>" not in r.json()["body"]
    assert "</script>" not in r.json()["body"]


def test_markdown_preserved_in_body(client, auth_headers):
    """bleach must not strip markdown syntax — only HTML tags."""
    markdown_body = "## heading\n- item one\n**bold** _italic_"
    r = client.post(
        "/reports",
        json={"title": "markdown report", "body": markdown_body},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["body"] == markdown_body


def test_html_stripped_on_update(client, auth_headers):
    """HTML tags in body must be stripped on update."""
    create_r = _create(client, auth_headers)
    assert create_r.status_code == 201
    report_id = create_r.json()["id"]

    update_r = client.put(
        f"/reports/{report_id}",
        json={"body": "<em>updated</em>"},
        headers=auth_headers,
    )
    assert update_r.status_code == 200
    assert update_r.json()["body"] == "updated"


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def test_list_reports(client, auth_headers):
    _create(client, auth_headers, title="List Test")
    r = client.get("/reports", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "offset" in data
    assert "limit" in data
    assert data["offset"] == 0
    assert data["limit"] == 20
    assert data["total"] >= 1


def test_list_reports_pagination(client, auth_headers):
    _create(client, auth_headers, title="Paginate A")
    _create(client, auth_headers, title="Paginate B")
    r = client.get("/reports?offset=0&limit=1", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) <= 1
    assert data["limit"] == 1
    assert data["total"] >= 1


def test_list_reports_no_auth(client):
    r = client.get("/reports")
    assert r.status_code == 401


def test_list_reports_status_filter(client, auth_headers):
    # Create an archived report
    create = _create(client, auth_headers, title="Archive Filter")
    report_id = create.json()["id"]
    client.patch(f"/reports/{report_id}/archive", headers=auth_headers)

    r = client.get("/reports?status=archived", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert all(item["status"] == "archived" for item in data["items"])


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

def test_get_report(client, auth_headers):
    create = _create(client, auth_headers, title="Get Me")
    report_id = create.json()["id"]
    r = client.get(f"/reports/{report_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Get Me"


def test_get_report_not_found(client, auth_headers):
    r = client.get("/reports/nonexistent-id-xyz", headers=auth_headers)
    assert r.status_code == 404


def test_get_report_no_auth(client, auth_headers):
    create = _create(client, auth_headers, title="Auth Check")
    report_id = create.json()["id"]
    r = client.get(f"/reports/{report_id}")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def test_update_report_title(client, auth_headers):
    create = _create(client, auth_headers, title="Old Title", body="Old body content")
    report_id = create.json()["id"]
    r = client.put(f"/reports/{report_id}", json={"title": "Updated Title"}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Updated Title"
    assert data["body"] == "Old body content"  # unchanged


def test_update_report_recomputes_word_count(client, auth_headers):
    create = _create(client, auth_headers, title="WC Test", body="one two")
    report_id = create.json()["id"]
    r = client.put(
        f"/reports/{report_id}",
        json={"body": "one two three four"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["wordCount"] == 4


def test_update_report_not_found(client, auth_headers):
    r = client.put("/reports/nonexistent-xyz", json={"title": "X"}, headers=auth_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

def test_archive_report(client, auth_headers):
    create = _create(client, auth_headers, title="Archive Me")
    report_id = create.json()["id"]
    r = client.patch(f"/reports/{report_id}/archive", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "archived"


def test_archive_idempotent(client, auth_headers):
    create = _create(client, auth_headers, title="Archive Twice")
    report_id = create.json()["id"]
    client.patch(f"/reports/{report_id}/archive", headers=auth_headers)
    r = client.patch(f"/reports/{report_id}/archive", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "archived"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def test_delete_report(client, auth_headers):
    create = _create(client, auth_headers, title="Delete Me")
    report_id = create.json()["id"]
    r = client.delete(f"/reports/{report_id}", headers=auth_headers)
    assert r.status_code == 204
    r2 = client.get(f"/reports/{report_id}", headers=auth_headers)
    assert r2.status_code == 404


def test_delete_report_not_found(client, auth_headers):
    r = client.delete("/reports/nonexistent-xyz", headers=auth_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# ActionLog entries
# ---------------------------------------------------------------------------

def test_action_log_entries_created(client, auth_headers):
    # POST should create an action log entry
    create = _create(client, auth_headers, title="Log Check")
    report_id = create.json()["id"]

    async def _check():
        async with async_session() as session:
            result = await session.execute(
                select(ActionLog).where(ActionLog.action_type.like("REPORT_%"))
            )
            return result.scalars().all()

    logs = asyncio.get_event_loop().run_until_complete(_check())
    assert len(logs) >= 1


# ---------------------------------------------------------------------------
# Structured 500 on DB error (unit test — service layer)
# ---------------------------------------------------------------------------

def test_create_report_db_commit_error(client, auth_headers):
    """When db.commit() raises SQLAlchemyError during report creation, the
    service must raise HTTPException(500) with a structured detail message,
    not an unhandled traceback."""
    from app.services.report_service import create_report
    from app.models.manual_report import ManualReportCreate

    async def _run():
        mock_session = AsyncMock(spec=["add", "commit", "refresh", "rollback"])
        mock_session.commit.side_effect = SQLAlchemyError("simulated commit failure")

        payload = ManualReportCreate(title="Boom", body="trigger error")

        from fastapi import HTTPException as _HTTPException
        with pytest.raises(_HTTPException) as exc_info:
            await create_report(mock_session, "fake-user-id", payload)

        assert exc_info.value.status_code == 500
        assert "Database error" in exc_info.value.detail

    asyncio.get_event_loop().run_until_complete(_run())
