# Step 1 — Backend Setup

## Purpose
Establish the foundational FastAPI backend with JWT authentication and SQLAlchemy ORM configured for local development.

## Deliverables
- requirements.txt with pinned dependencies for FastAPI, SQLAlchemy, Pydantic, and JWT libraries.
- code/backend/app/main.py: FastAPI application instance with CORS and basic routing.
- code/backend/app/core/config.py: Configuration settings for database and JWT.
- code/backend/app/core/security.py: JWT token creation and validation functions.
- code/backend/app/db/session.py: SQLAlchemy engine and session management.
- code/backend/app/db/base.py: Base model class with common fields.

## Primary files to change
- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/app/main.py](code/backend/app/main.py)
- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [code/backend/app/core/security.py](code/backend/app/core/security.py)
- [code/backend/app/db/session.py](code/backend/app/db/session.py)
- [code/backend/app/db/base.py](code/backend/app/db/base.py)

## Detailed implementation steps
1. Create requirements.txt with dependencies: fastapi, uvicorn, sqlalchemy, pydantic, python-jose[cryptography], passlib[bcrypt], python-multipart.
2. In main.py, initialize FastAPI app with title "Ambient AI Productivity Dashboard", enable CORS for frontend origin.
3. In config.py, define settings for DATABASE_URL (SQLite for dev), SECRET_KEY, ALGORITHM for JWT.
4. In security.py, implement create_access_token and verify_token functions using python-jose.
5. In session.py, create SQLAlchemy engine and sessionmaker with async support.
6. In base.py, define Base class inheriting from DeclarativeBase with id (UUID), created_at, updated_at fields.

## Integration & Edge Cases
- Ensure async SQLAlchemy for future scalability.
- No existing features; this is the initial setup.

## Acceptance Criteria
1. `pip install -r requirements.txt` succeeds without conflicts.
2. `uvicorn app.main:app --reload` starts server on port 8000.
3. GET /docs returns OpenAPI documentation.
4. JWT token creation and verification functions work correctly.

## Testing / QA
- Add unit test for JWT functions in code/backend/tests/test_security.py.
- Manual QA: Start server and verify /docs endpoint loads.

## Files touched
- [code/backend/requirements.txt](code/backend/requirements.txt)
- [code/backend/app/main.py](code/backend/app/main.py)
- [code/backend/app/core/config.py](code/backend/app/core/config.py)
- [code/backend/app/core/security.py](code/backend/app/core/security.py)
- [code/backend/app/db/session.py](code/backend/app/db/session.py)
- [code/backend/app/db/base.py](code/backend/app/db/base.py)

## Estimated effort
1 dev day

## Concurrency & PR strategy
- Branch: phase-1/step-1-backend-setup
- Can be parallel with other backend steps.

## Risks & Mitigations
- Dependency version conflicts; use pinned versions.

## References
- [architecture.md](../architecture.md)

## Author Checklist
- [x] Purpose filled
- [x] Deliverables listed
- [x] Primary files to change contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable</content>
<parameter name="filePath">/home/manny/Documents/projects/personalDash2026/project/.github/artifacts/phase1/plan/backend-setup.md