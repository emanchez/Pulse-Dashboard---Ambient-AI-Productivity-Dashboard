# Step 3 — API Skeleton

## Purpose
Create basic CRUD API endpoints for tasks with JWT authentication and action logging middleware.

## Deliverables
- code/backend/app/api/tasks.py: Task CRUD endpoints.
- code/backend/app/api/auth.py: Login endpoint.
- code/backend/app/middlewares/action_log.py: Middleware to log actions.
- code/backend/app/main.py: Include routers and middleware.

## Primary files to change
- [code/backend/app/api/tasks.py](code/backend/app/api/tasks.py)
- [code/backend/app/api/auth.py](code/backend/app/api/auth.py)
- [code/backend/app/middlewares/action_log.py](code/backend/app/middlewares/action_log.py)
- [code/backend/app/main.py](code/backend/app/main.py)

## Detailed implementation steps
1. In auth.py, create POST /login endpoint that returns JWT token (dummy user for now).
2. In tasks.py, create GET /tasks, POST /tasks, PUT /tasks/{id}, DELETE /tasks/{id} with JWT dependency.
3. In action_log.py, create middleware that logs task updates to ActionLog table.
4. Update main.py to include routers and middleware.

## Integration & Edge Cases
- All endpoints except /login require JWT.
- ActionLog triggers on task saves.

## Acceptance Criteria
1. POST /login returns JWT token.
2. GET /tasks requires auth and returns empty list initially.
3. Task CRUD operations work and log actions.

## Testing / QA
- Add API tests in code/backend/tests/test_api.py.
- Manual QA: Use /docs to test endpoints.

## Files touched
- [code/backend/app/api/tasks.py](code/backend/app/api/tasks.py)
- [code/backend/app/api/auth.py](code/backend/app/api/auth.py)
- [code/backend/app/middlewares/action_log.py](code/backend/app/middlewares/action_log.py)
- [code/backend/app/main.py](code/backend/app/main.py)

## Estimated effort
1-2 dev days

## Concurrency & PR strategy
- Branch: phase-1/step-3-api-skeleton
- Depends on steps 1 and 2.

## Risks & Mitigations
- Auth failures; test thoroughly.

## References
- [architecture.md](../architecture.md)

## Author Checklist
- [x] Purpose filled
- [x] Deliverables listed
- [x] Primary files to change contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable</content>
<parameter name="filePath">/home/manny/Documents/projects/personalDash2026/project/.github/artifacts/phase1/plan/api-skeleton.md