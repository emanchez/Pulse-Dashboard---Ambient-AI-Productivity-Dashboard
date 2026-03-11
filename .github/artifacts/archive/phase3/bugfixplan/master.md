# Phase 3 Bugfix — Master Plan

**Date:** 2026-03-06  
**Phase owner:** TBD  
**Branch convention:** `phase-3/bugfix/step-<n>-<short-desc>`

---

## Scope

Two distinct bugs were observed after the Phase 3 Postplan Group A & B session:

1. **Task selection broken in the Report modal** — the "Link Tasks" dropdown shows "No tasks available" regardless of whether tasks exist.
2. **CORS error + HTTP 500 when saving or fetching reports** — the browser reports a missing `Access-Control-Allow-Origin` header; the backend returns a 500.

Both bugs interact: the CORS/500 failure on `/tasks/` silently kills the task-list fetch in `reports/page.tsx`, which is why tasks never appear in the form. Fixing the backend first resolves the primary cause; the frontend error-handling fixes make the system resilient to future partial failures.

This plan covers **no new features** — only bug fixes and defensive hardening within the scope of existing Phase 3 deliverables.

---

## Phase-level Deliverables

- CORS configuration correctly loads all 4 dev origins from `.env` under both shell-env and clean-env conditions.
- `FRONTEND_CORS_ORIGINS` env var supports a comma-separated string so it survives the existing `env_file = None` vs. shell-export ambiguity.
- DB-layer exceptions in `report_service.py` are caught and re-raised as structured `HTTPException(500)` so FastAPI always sends a CORS-headered response.
- `reports/page.tsx` splits fetches, surfaces an error banner on partial failure, and never silently drops tasks to `[]` without user feedback.
- `TaskSchema.id` nullability is guarded in `ReportForm.tsx` before use in checkbox logic.
- `pytest -q` — 75+ tests pass.
- `npm run build` — 0 TypeScript errors.

---

## Steps (ordered)

1. Step 1 — [step-1-backend-cors-and-error-handling.md](./step-1-backend-cors-and-error-handling.md)
2. Step 2 — [step-2-frontend-error-handling-and-type-safety.md](./step-2-frontend-error-handling-and-type-safety.md)

---

## Merge Order

Steps can be **developed in parallel** (no shared modified files) but must be **deployed in order**:

1. `.github/artifacts/phase3/bugfixplan/step-1-backend-cors-and-error-handling.md` — branch: `phase-3/bugfix/step-1-backend-cors`
2. `.github/artifacts/phase3/bugfixplan/step-2-frontend-error-handling-and-type-safety.md` — branch: `phase-3/bugfix/step-2-frontend-errors`

Step 2 has no compile-time dependency on Step 1 (no generated artifacts), so both PRs may be opened simultaneously. Step 2 must not be merged to a deployed environment before Step 1 is live, because the frontend improvements rely on the backend correctly returning CORS headers and non-500 responses.

---

## Phase Acceptance Criteria

1. `GET http://localhost:8000/reports?offset=0&limit=20` from origin `http://localhost:3000` returns 200 with `Access-Control-Allow-Origin: http://localhost:3000` header.
2. `GET http://localhost:8000/reports?offset=0&limit=20` from origin `http://127.0.0.1:3000` returns 200 with `Access-Control-Allow-Origin: http://127.0.0.1:3000` header.
3. A simulated DB error in `create_report` returns HTTP 500 with a JSON body — **not** an unhandled exception trace — and the response includes the CORS origin header.
4. Opening the Reports page shows a task list in the "Link Tasks" dropdown (given tasks exist for the user).
5. If the `/tasks/` fetch fails independently, the Reports page displays an inline error banner rather than silently showing an empty task list.
6. Selecting tasks in the Link Tasks dropdown toggles their checkbox state correctly for tasks whose `id` is a non-null UUID string.
7. `pytest -q` in `code/backend` — 75 or more tests pass, 0 failures.
8. `npm run build` in `code/frontend` — 0 TypeScript errors, all pages compiled.

---

## Concurrency groups & PR strategy

| Group | Steps | Can parallelize? | Merge before |
|---|---|---|---|
| A | Step 1 (backend) | Yes — sole backend modifier | — |
| A | Step 2 (frontend) | Yes — sole frontend modifier | Step 1 deployed |

Both steps touch entirely different files. Open PRs simultaneously; merge Step 1 first in a deployed environment; merge Step 2 immediately after.

---

## Verification Plan

### Backend smoke tests (after Step 1 merge)

```bash
cd code/backend
pytest -q
```

```bash
# Start the backend
uvicorn app.main:app --reload --port 8000

# Test CORS from localhost origin
curl -sS -H "Origin: http://localhost:3000" \
  -H "Authorization: Bearer <token>" \
  "http://localhost:8000/reports?offset=0&limit=20" \
  -I | grep -i "access-control"

# Test CORS from 127.0.0.1 origin
curl -sS -H "Origin: http://127.0.0.1:3000" \
  -H "Authorization: Bearer <token>" \
  "http://localhost:8000/reports?offset=0&limit=20" \
  -I | grep -i "access-control"
```

### Frontend smoke tests (after Step 2 merge)

```bash
cd code/frontend
npm run build
```

Manual:
1. Open `http://localhost:3000/reports`.
2. Confirm tasks populate in the "Link Tasks" dropdown.
3. Disable the backend `/tasks/` route temporarily; refresh the page. Confirm an error banner appears (does not silently show empty dropdown).
4. Re-enable and confirm normal operation.

---

## Risks, Rollbacks & Migration Notes

- **No persistence changes** — no database migrations required.
- **CORS change risk:** Widening CORS origins is low-risk (dev only). If an incorrect `FRONTEND_CORS_ORIGINS` value is set in production, the rollback is to revert `config.py` to the hardcoded default list and re-deploy.
- **Service exception wrapping risk:** Converting unhandled exceptions to `HTTPException(500)` changes error response shape. Confirm no tests assert on the raw FastAPI error body format before merging.
- **Frontend fetch split risk:** Splitting `Promise.all` into independent fetches means `setLoading(false)` must be called only after both settle. The implementation must use `Promise.allSettled` or two sequential `finally` blocks to avoid the spinner disappearing before the second fetch resolves.

---

## References

- [observations.txt](./../bugfixplan/observations.txt) — raw bug observations
- [step-1-backend-cors-and-error-handling.md](./step-1-backend-cors-and-error-handling.md)
- [step-2-frontend-error-handling-and-type-safety.md](./step-2-frontend-error-handling-and-type-safety.md)
- [PLANNING.md](../../PLANNING.md)
- [code/backend/app/core/config.py](../../../../code/backend/app/core/config.py)
- [code/backend/app/services/report_service.py](../../../../code/backend/app/services/report_service.py)
- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx)
- [code/frontend/components/reports/ReportForm.tsx](../../../../code/frontend/components/reports/ReportForm.tsx)
- [postplan-group-a-summary.md](../summary/postplan-group-a-summary.md)
- [postplan-group-b-implementation-summary.md](../summary/postplan-group-b-implementation-summary.md)

---

## Author Checklist (master)

- [x] All step files created and linked
- [x] Phase-level acceptance criteria are measurable
- [x] PR/merge order documented
