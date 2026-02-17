# Phase 1 — Skeleton & Agentic Prototyping

## Scope
Establish the foundational architecture for the Ambient AI Productivity Dashboard, including backend API skeleton, data models, and basic frontend shell with type synchronization.

## Phase-level Deliverables
- Backend: FastAPI application with JWT authentication and SQLAlchemy ORM configured for SQLite/PostgreSQL.
- Data Models: Pydantic models for Task, ActionLog, ManualReport, and SystemState with camelCase JSON serialization.
- API Skeleton: Basic CRUD endpoints for tasks and action logging middleware.
- Frontend: Next.js application with Bento Box grid layout and Lucide icons.
- Type Sync: Automated generation of TypeScript clients from FastAPI openapi.json using @hey-api/openapi-ts.

## Steps (ordered)
1. Step 1 — [backend-setup.md](./backend-setup.md)
2. Step 2 — [data-models.md](./data-models.md)
3. Step 3 — [api-skeleton.md](./api-skeleton.md)
4. Step 4 — [frontend-setup.md](./frontend-setup.md)
5. Step 5 — [type-sync.md](./type-sync.md)

## Phase Acceptance Criteria
- Backend server starts successfully and serves OpenAPI documentation at /docs.
- All Pydantic models serialize to camelCase JSON and validate correctly.
- API endpoints return proper HTTP status codes and JSON responses.
- Frontend renders Bento Box grid with placeholder components.
- TypeScript client generated and imports successfully in frontend without type errors.

## Concurrency groups & PR strategy
- Steps 1-3 (backend) can be parallelized as they are interdependent.
- Step 4 (frontend) depends on Step 5 (type-sync) completion.
- Merge order: Backend steps first, then frontend after type sync is ready.

## Verification Plan
- Run backend tests: `pytest` in /code/backend
- Start backend server: `uvicorn app.main:app --reload` and verify /docs endpoint.
- Build frontend: `npm run build` in /code/frontend and check for TypeScript errors.
- Integration test: Frontend can fetch from backend API endpoints.

## Risks, Rollbacks & Migration Notes
- No data migration needed as this is initial setup.
- Rollback: Delete created files and revert to empty /code directory.
- Risk: Dependency conflicts; mitigate by using pinned versions in requirements.txt and package.json.

## References
- [PDD.md](../PDD.md) — Product Design Document
- [architecture.md](../architecture.md) — Technical Architecture
- Step files in this directory.

## Author Checklist (master)
- [x] All step files created and linked
- [x] Phase-level acceptance criteria are measurable
- [x] PR/merge order documented</content>
<parameter name="filePath">/home/manny/Documents/projects/personalDash2026/project/.github/artifacts/phase1/plan/master.md