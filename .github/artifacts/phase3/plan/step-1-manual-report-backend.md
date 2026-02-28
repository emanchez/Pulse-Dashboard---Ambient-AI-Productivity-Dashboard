# Step 1 — ManualReport Model Enhancement + CRUD API

## Purpose

Enhance the existing `ManualReport` model stub with `user_id`, `status`, and `tags` columns, create request/update Pydantic schemas, build a full CRUD API with pagination and archive support, and wire event-sourced action logging — enabling the frontend to create, list, view, edit, archive, and delete reports.

## Deliverables

- Enhanced `code/backend/app/models/manual_report.py` — `user_id`, `status`, `tags` columns added; `ManualReportCreate` and `ManualReportUpdate` schemas added
- New `code/backend/app/services/report_service.py` — business logic: create (auto word_count), list (paginated, filterable by status), get, update, delete, archive; task ID validation
- New `code/backend/app/api/reports.py` — 6 JWT-guarded, user-scoped endpoints
- Updated `code/backend/app/main.py` — register reports router + model import for table creation
- Extended `code/backend/app/middlewares/action_log.py` — log mutations on `/reports` paths
- New `code/backend/tests/test_reports.py` — comprehensive test suite
- Updated `code/backend/app/schemas/__init__.py` — re-export new schemas

## Primary files to change (required)

- [code/backend/app/models/manual_report.py](../../../../code/backend/app/models/manual_report.py) *(modify)*
- [code/backend/app/services/report_service.py](../../../../code/backend/app/services/report_service.py) *(new)*
- [code/backend/app/api/reports.py](../../../../code/backend/app/api/reports.py) *(new)*
- [code/backend/app/main.py](../../../../code/backend/app/main.py) *(modify)*
- [code/backend/app/middlewares/action_log.py](../../../../code/backend/app/middlewares/action_log.py) *(modify)*
- [code/backend/app/schemas/__init__.py](../../../../code/backend/app/schemas/__init__.py) *(modify)*
- [code/backend/tests/test_reports.py](../../../../code/backend/tests/test_reports.py) *(new)*

## Detailed implementation steps

1. **Enhance `ManualReport` model** in `code/backend/app/models/manual_report.py`:
   - Add columns:
     - `user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)`
     - `status: Mapped[str] = mapped_column(String(32), nullable=False, default="published")` — valid values: `draft`, `published`, `archived`
     - `tags: Mapped[list | None] = mapped_column(JSON, nullable=True)` — list of tag strings (e.g., `["Engineering", "Strategy"]`)
   - Keep existing columns: `title`, `body`, `word_count`, `associated_task_ids`
   - Model inherits `TimestampedBase` (already does) — provides `id`, `created_at`, `updated_at`

2. **Update `ManualReportSchema`** (read DTO) in the same file:
   - Add fields: `status: str | None = None`, `tags: list[str] | None = None`, `user_id: str | None = None`, `updated_at: datetime | None = None`
   - Add `model_config = ConfigDict(from_attributes=True)` to support ORM → schema conversion

3. **Create `ManualReportCreate` schema** (write DTO):
   ```python
   class ManualReportCreate(CamelModel):
       title: str  # required, max 256 chars
       body: str   # required, max 50000 chars
       associated_task_ids: list[str] | None = None
       tags: list[str] | None = None
       status: str = "published"  # default published; accept "draft"
   ```
   - Add Pydantic validators: `title` min 1 / max 256 chars, `body` max 50,000 chars, `status` must be in `{"draft", "published"}` (archived is set via dedicated endpoint)

4. **Create `ManualReportUpdate` schema** (partial update DTO):
   ```python
   class ManualReportUpdate(CamelModel):
       title: str | None = None
       body: str | None = None
       associated_task_ids: list[str] | None = None
       tags: list[str] | None = None
       status: str | None = None  # allow changing to draft/published
   ```

5. **Create `PaginatedReportsResponse` schema**:
   ```python
   class PaginatedReportsResponse(CamelModel):
       items: list[ManualReportSchema]
       total: int
       offset: int
       limit: int
   ```

6. **Create `report_service.py`** in `code/backend/app/services/`:
   - `create_report(db, user_id, data: ManualReportCreate) -> ManualReport`:
     - Auto-compute `word_count = len(data.body.split())`
     - If `associated_task_ids` is provided, validate each ID exists in the `tasks` table (query `SELECT id FROM tasks WHERE id IN (:ids)` and raise 400 for any missing)
     - Insert and return the new row
   - `list_reports(db, user_id, offset=0, limit=20, status_filter=None) -> tuple[list[ManualReport], int]`:
     - Filter by `user_id`; optionally filter by `status`
     - Order by `created_at DESC`
     - Return `(items, total_count)`
   - `get_report(db, user_id, report_id) -> ManualReport | None`:
     - Filter by `id` AND `user_id` (user-scoped)
   - `update_report(db, user_id, report_id, data: ManualReportUpdate) -> ManualReport | None`:
     - Fetch report scoped to user; apply non-None fields; recompute `word_count` if body changed
     - Validate `associated_task_ids` if provided
   - `delete_report(db, user_id, report_id) -> bool`:
     - Fetch report scoped to user; delete; return True/False
   - `archive_report(db, user_id, report_id) -> ManualReport | None`:
     - Set `status = "archived"`; return updated report

7. **Create `reports.py` router** in `code/backend/app/api/`:
   - `POST /reports` → 201, body `ManualReportCreate`, response `ManualReportSchema`
   - `GET /reports` → 200, query params `offset: int = 0`, `limit: int = 20`, `status: str | None = None`, response `PaginatedReportsResponse`
   - `GET /reports/{report_id}` → 200, response `ManualReportSchema`; 404 if not found
   - `PUT /reports/{report_id}` → 200, body `ManualReportUpdate`, response `ManualReportSchema`; 404 if not found
   - `DELETE /reports/{report_id}` → 204; 404 if not found
   - `PATCH /reports/{report_id}/archive` → 200, response `ManualReportSchema`; 404 if not found
   - All routes use `Depends(get_current_user)` from `code/backend/app/api/auth.py` and `Depends(get_async_session)`
   - Router: `router = APIRouter(prefix="/reports")`

8. **Update `main.py`**:
   - Add `from .api import reports as reports_router`
   - Add `app.include_router(reports_router.router)`
   - Add `from .models.manual_report import ManualReport as _ManualReport  # noqa: F401` to register model with Base.metadata

9. **Extend `ActionLogMiddleware`**:
   - In the `dispatch` method, add `/reports` to the path check alongside `/tasks`:
     ```python
     if (path.startswith("/tasks") or path.startswith("/reports")) and method in {"POST", "PUT", "DELETE", "PATCH"}:
     ```
   - For `/reports` paths, extract `report_id` from path segments (similar pattern to task_id extraction)
   - Store in `action_type` field: e.g., `"POST /reports"`, `"PATCH /reports/{id}/archive"`

10. **Update `schemas/__init__.py`**:
    - Add re-exports: `ManualReportCreate`, `ManualReportUpdate`, `PaginatedReportsResponse`

11. **Write tests** in `code/backend/tests/test_reports.py` — see Testing / QA section.

## Integration & Edge Cases

- **User scoping:** All queries filter by `user_id` from JWT. A user cannot see, edit, or delete another user's reports.
- **Task ID validation:** When `associated_task_ids` is provided, validate the IDs exist in the `tasks` table. Note: tasks are currently NOT user-scoped (known tech debt), so validation only checks existence, not ownership.
- **Word count computation:** Server-side via `len(body.split())`. Updated when body changes via PUT.
- **Archive semantics:** Archive is a status change, not deletion. Archived reports are still visible in list with `status=archived` filter. The `PATCH /reports/{id}/archive` endpoint is idempotent.
- **Pagination:** Offset-based with `total` count. Frontend uses `limit=20` default. "Load Historical Reports" triggers `offset += limit`.
- **DB migration:** `manual_reports` table gains new columns. Since the table stub exists but has no data (no endpoints existed before), `create_all` will detect the new columns. If the table already exists with data (unlikely), Alembic may be needed.
- **BEFORE MERGE:** Snapshot `data/dev.db` to `data/dev.db.bak`.

## Acceptance Criteria

1. `POST /reports` with `{ "title": "Weekly Update", "body": "Progress on backend refactoring and frontend polish." }` returns `201` with JSON containing `id`, `title`, `body`, `wordCount: 7`, `status: "published"`, `userId`, `createdAt`, `updatedAt`.
2. `POST /reports` with empty `title` returns `422` (Pydantic validation).
3. `POST /reports` without JWT returns `401`.
4. `GET /reports` returns `200` with `{ "items": [...], "total": <int>, "offset": 0, "limit": 20 }`.
5. `GET /reports?status=archived` returns only archived reports.
6. `GET /reports?offset=0&limit=1` returns at most 1 item with correct `total`.
7. `GET /reports/{id}` returns `200` with the full report; `GET /reports/{nonexistent}` returns `404`.
8. `PUT /reports/{id}` with `{ "title": "Updated Title" }` returns `200` with `title: "Updated Title"` and unchanged `body`.
9. `PUT /reports/{id}` with updated `body` recalculates `wordCount`.
10. `PATCH /reports/{id}/archive` returns `200` with `status: "archived"`.
11. `DELETE /reports/{id}` returns `204`; subsequent `GET /reports/{id}` returns `404`.
12. `POST /reports` with `associated_task_ids` referencing a nonexistent task returns `400`.
13. `POST /reports` with `tags: ["Engineering", "Strategy"]` stores and returns the tags.
14. User A cannot `GET /reports/{id}` a report created by User B (returns `404`).
15. `ActionLog` table contains entries for `POST /reports` and `PUT /reports/{id}` mutations.

## Testing / QA

### Automated tests — `code/backend/tests/test_reports.py`

```python
# Fixtures: client, auth_headers (reuse from conftest.py)

def test_create_report(client, auth_headers):
    r = client.post("/reports", json={"title": "Test", "body": "Hello world foo bar"}, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Test"
    assert data["wordCount"] == 4
    assert data["status"] == "published"
    assert data["userId"] is not None

def test_create_report_no_auth(client):
    r = client.post("/reports", json={"title": "Test", "body": "Hello"})
    assert r.status_code == 401

def test_create_report_empty_title(client, auth_headers):
    r = client.post("/reports", json={"title": "", "body": "Hello"}, headers=auth_headers)
    assert r.status_code == 422

def test_list_reports(client, auth_headers):
    client.post("/reports", json={"title": "A", "body": "Content"}, headers=auth_headers)
    r = client.get("/reports", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1

def test_list_reports_pagination(client, auth_headers):
    r = client.get("/reports?offset=0&limit=1", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) <= 1

def test_list_reports_status_filter(client, auth_headers):
    r = client.get("/reports?status=archived", headers=auth_headers)
    assert r.status_code == 200
    # all items should be archived
    for item in r.json()["items"]:
        assert item["status"] == "archived"

def test_get_report(client, auth_headers):
    create = client.post("/reports", json={"title": "Get Me", "body": "Body"}, headers=auth_headers)
    report_id = create.json()["id"]
    r = client.get(f"/reports/{report_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Get Me"

def test_get_report_not_found(client, auth_headers):
    r = client.get("/reports/nonexistent-id", headers=auth_headers)
    assert r.status_code == 404

def test_update_report(client, auth_headers):
    create = client.post("/reports", json={"title": "Old", "body": "Old body"}, headers=auth_headers)
    report_id = create.json()["id"]
    r = client.put(f"/reports/{report_id}", json={"title": "New"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "New"
    assert r.json()["body"] == "Old body"  # unchanged

def test_update_report_recomputes_word_count(client, auth_headers):
    create = client.post("/reports", json={"title": "WC", "body": "one two"}, headers=auth_headers)
    report_id = create.json()["id"]
    r = client.put(f"/reports/{report_id}", json={"body": "one two three four"}, headers=auth_headers)
    assert r.json()["wordCount"] == 4

def test_archive_report(client, auth_headers):
    create = client.post("/reports", json={"title": "Archive Me", "body": "Body"}, headers=auth_headers)
    report_id = create.json()["id"]
    r = client.patch(f"/reports/{report_id}/archive", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "archived"

def test_delete_report(client, auth_headers):
    create = client.post("/reports", json={"title": "Delete Me", "body": "Body"}, headers=auth_headers)
    report_id = create.json()["id"]
    r = client.delete(f"/reports/{report_id}", headers=auth_headers)
    assert r.status_code == 204
    r2 = client.get(f"/reports/{report_id}", headers=auth_headers)
    assert r2.status_code == 404

def test_create_with_tags(client, auth_headers):
    r = client.post("/reports", json={"title": "Tagged", "body": "Content", "tags": ["Engineering", "Strategy"]}, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["tags"] == ["Engineering", "Strategy"]

def test_create_with_invalid_task_ids(client, auth_headers):
    r = client.post("/reports", json={"title": "Bad", "body": "Content", "associatedTaskIds": ["nonexistent"]}, headers=auth_headers)
    assert r.status_code == 400
```

### Manual QA checklist

1. Start backend: `uvicorn app.main:app --reload`
2. Login → get token
3. `POST /reports` with title + body → verify 201 with auto word count
4. `GET /reports` → verify paginated response
5. `PUT /reports/{id}` → verify partial update
6. `PATCH /reports/{id}/archive` → verify status change
7. `DELETE /reports/{id}` → verify 204 + gone
8. Check `action_logs` table → verify entries for report mutations

## Files touched (repeat for reviewers)

- [code/backend/app/models/manual_report.py](../../../../code/backend/app/models/manual_report.py)
- [code/backend/app/services/report_service.py](../../../../code/backend/app/services/report_service.py)
- [code/backend/app/api/reports.py](../../../../code/backend/app/api/reports.py)
- [code/backend/app/main.py](../../../../code/backend/app/main.py)
- [code/backend/app/middlewares/action_log.py](../../../../code/backend/app/middlewares/action_log.py)
- [code/backend/app/schemas/__init__.py](../../../../code/backend/app/schemas/__init__.py)
- [code/backend/tests/test_reports.py](../../../../code/backend/tests/test_reports.py)

## Estimated effort

1–2 dev days

## Concurrency & PR strategy

- **Suggested branch:** `phase-3/step-1-manual-report-backend`
- **Blocking steps:** `phase-3/step-0-tech-debt-cleanup` must be merged first (consolidated auth, modern datetime patterns)
- **Merge Readiness:** false
- Can be developed in parallel with Step 2 (SystemState backend) after Step 0 merges.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `manual_reports` table already exists with old schema (no `user_id`, `status`, `tags`) | `create_all` is additive for new columns on SQLite; if issues arise, drop and recreate table (no production data) |
| Large report body causes slow queries | Add `body` max length validation (50,000 chars) in `ManualReportCreate` |
| `associated_task_ids` references tasks not owned by user | Known limitation (tasks lack `user_id`); validate existence only |

## References

- [PDD.md — §3.2 ManualReport](../../PDD.md)
- [architecture.md — §1 Data Schema, §2 API Design](../../architecture.md)
- [Phase 3 Master](./master.md)
- [Step 0 — Tech Debt](./step-0-tech-debt-cleanup.md)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
- [ ] Author signoff
