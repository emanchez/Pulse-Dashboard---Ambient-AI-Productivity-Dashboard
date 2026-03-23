# Phase 4.2 Step X — Task Deadline TZ Fix Summary

**Branch:** phase4-2/stepX-task-deadline-tz-fix
**Date:** 2026-03-23
**Status:** ✅ Complete

## Problem
POST /tasks/ with a timezone-aware deadline (e.g. `2026-03-27T00:00:00.000Z`) caused `500 Internal Server Error` in PostgreSQL with asyncpg:
`TypeError: can't subtract offset-naive and offset-aware datetimes`.

## Root cause
- `deadline` is declared as `DateTime` (no timezone) in SQLAlchemy and `TIMESTAMP WITHOUT TIME ZONE` in PostgreSQL.
- Frontend sends ISO8601 with `Z` (UTC-aware).
- Pydantic parsed the field as offset-aware datetime and asyncpg attempted to write it to naive column.

## Fix implemented
- In `code/backend/app/models/task.py`:
  - added `_strip_deadline_tz()` helper
  - added `@field_validator("deadline", mode="after")` to `TaskCreate` and `TaskUpdate`
  - validator converts aware timestamps to UTC and strips `tzinfo`.

## Regression test
- In `code/backend/tests/test_api.py`:
  - added `test_task_create_deadline_tz_aware`
  - verifies `POST /tasks/` with `"deadline": "2026-03-27T00:00:00.000Z"` now returns `201`.

## Validation
- `pytest -q` passes (171 passed, 0 failed).

## Notes
- Existing `test_task_update_clears_deadline` also now passes after changing mode from `before` to `after`.
- No DB migration needed for this fix.
