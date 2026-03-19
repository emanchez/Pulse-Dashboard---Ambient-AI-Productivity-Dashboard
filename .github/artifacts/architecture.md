# Technical Architecture

## 1. Data Schema (SQLAlchemy Models)

### Task
- id: UUID (PK)
- name: String
- priority: Enum (Low, Medium, High)
- tags: String (CSV)
- isCompleted: Boolean
- dateCreated: DateTime
- dateUpdated: DateTime
- deadlineDate: DateTime (Nullable)
- notes: Text

### ActionLog
- id: UUID (PK)
- timestamp: DateTime
- taskId: UUID (FK -> Task.id)
- actionType: Enum (Created, Edited, Completed, Deleted)
- changeSummary: Text (e.g., "Priority changed Low -> High")

### ManualReport
- id: UUID (PK)
- title: String
- body: Text
- wordCount: Integer
- associatedTaskIds: JSON (List[UUID])
- createdAt: DateTime

### SystemState
- id: UUID (PK)
- modeType: Enum (Active, Vacation, Leave)
- startDate: DateTime
- endDate: DateTime
- requiresRecovery: Boolean (Default: True)
- description: Text

## 2. API Design (FastAPI)

### Authentication
- POST /auth/login: Returns JWT Access Token.
- Middleware: Validates Authorization: Bearer <token> on all protected routes.

### Tasks & Logs
- GET /tasks: List all tasks (filter by completion).
- POST /tasks: Create new task -> Triggers ActionLog.
- PATCH /tasks/{id}: Update task -> Triggers ActionLog.
- GET /stats/pulse: Returns time since last ActionLog entry.

### Reports & AI
- POST /reports: Submit manual report.
- POST /ai/synthesize: Trigger on-demand Sunday Report (calls Ollama).
- GET /ai/suggestions: Get AI-generated task list.

## 3. Synchronization (Type Sync)

**Tool:** openapi-ts (or @hey-api/openapi-ts).

**Workflow:**
- FastAPI generates openapi.json at build time.
- Frontend script runs npm run generate-client.
- TypeScript interfaces (e.g., Task, ActionLog) are auto-updated to match Backend Pydantic models.

## 4. Security (ADR)

- **Local-First:** All data stored in SQLite (`dev.db`) in development, PostgreSQL in production.
- **Auth:** JWT is strictly enforced on all routes except `/login` and `/health`, even in single-user mode — this ensures zero refactoring cost when moving to a VPS or multi-user deployment.
- **Secrets:** `JWT_SECRET`, `DATABASE_URL`, and all credentials stored in `.env`; never committed to version control. In production, inject via environment variables or a secrets manager (Vault, AWS Secrets Manager, etc.).
- **JWT Claims:** All tokens MUST include `iss` (issuer), `aud` (audience), `sub` (user UUID), `iat`, and `exp`. The `sub` claim is the authoritative user identity used for all DB queries. Tokens have an 8-hour TTL in dev; reduce to 1 hour in production with a `/refresh` endpoint.
- **Token validation on the client:** On mount, the frontend must validate the stored token against `/me`. If the server returns 401/403, the token is wiped from storage and the user is redirected to login. This catches expired tokens, algorithm/claim changes, and deleted users.
- **CORS:** `FRONTEND_CORS_ORIGINS` is a comma-separated string (never `List[str]` — pydantic-settings would JSON-parse it). In non-dev environments, `get_cors_origins()` raises `ValueError` if any localhost origin is present.
- **Rate limiting:** SlowAPI enforces a global 200 req/min cap (S-7). `/login` is further capped at 5/min in prod.
- **Request body size:** All POST/PUT/PATCH requests are limited to 512 KB by `_ContentSizeLimitMiddleware` (S-13).

---

## 5. Data Integrity & Migration Policy

### 5.1 Foreign Key Discipline

Every table that stores user-owned data (`tasks`, `manual_reports`, `action_logs`, `session_logs`, `ai_usage_logs`, `synthesis_reports`, `system_states`) carries a `user_id` column that references `users.id`. This is the **single ownership link** for the entire app.

**Rules:**
- `user_id` must never be nullable on any user-owned table.
- Every API query that returns user-owned data MUST include `WHERE user_id = <jwt_sub>` on the root table. Ownership via join is not acceptable.
- Deleting a user must cascade-delete or explicitly clean up all related rows. Orphaned rows (rows whose `user_id` references a non-existent user) are silent data loss.
- SQLite does not enforce foreign key constraints by default. Always enable them at connection time in production: `PRAGMA foreign_keys = ON`.

### 5.2 Migration Discipline (Alembic — Required for Production)

`Base.metadata.create_all` is **development scaffolding only**. It creates missing tables but never:
- Adds columns to existing tables
- Drops or renames columns
- Adds or removes constraints
- Runs data migrations

For any schema change in a table that already holds data, an Alembic migration is required:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

**Pre-migration checklist (mandatory before any schema PR):**
1. Back up `dev.db`: `cp data/dev.db data/dev.db.pre-<change>.bak`
2. Generate the migration and inspect the generated file — never blindly apply autogenerate output.
3. Verify data continuity: if a column is added, ensure existing rows receive a sensible default (not NULL on a NOT NULL column).
4. Test rollback: `alembic downgrade -1` must succeed without data corruption.
5. Document the migration file path in the step document.

### 5.3 Seeding Script Safety Contract

All scripts in `code/backend/scripts/` MUST satisfy:

| Rule | Rationale |
|------|-----------|
| **Idempotent:** safe to re-run any number of times | Re-running during setup/CI must not corrupt data |
| **Upsert, not delete+insert:** if a record exists, update only mutable fields | Preserves the auto-generated UUID (`id`), keeping all related rows intact |
| **Never regenerate PKs for existing records** | A new UUID for an existing user/entity orphans everything referencing the old UUID |
| **Print the preserved `id` on update** | Provides observability; easy to verify the ID did not change |
| **Explicit reset must be opt-in** | If a "full reset" is needed, it must be a separate `--reset` flag with a confirmation prompt, not the default behavior |

### 5.4 Backup & Recovery

- **Automated pre-migration backup:** Any Makefile target or script that modifies the schema or seeds data must first copy `dev.db` to `dev.db.pre-<timestamp>.bak`.
- **Production backups:** `pg_dump` on a schedule (daily minimum). Encrypt at rest. Test restore quarterly.
- **Point-in-time recovery:** For PostgreSQL, enable WAL archiving so any moment in the last 7 days is recoverable.
- **Backup validation:** A backup is only as good as its last successful restore test. Automate a restore-to-staging check weekly.

---

## 6. Multi-User Upgrade Path

The app is designed single-user today, but the codebase is structured to support multi-tenancy with minimal refactoring. The following plan applies when/if the app is opened to additional users.

### 6.1 What is already in place
- Every user-owned table includes `user_id` (no global tables without an owner).
- All API queries are already scoped by `user_id` from the JWT `sub` claim.
- JWT uses `iss`/`aud`/`sub` claims per RFC 7519 — no app-specific token format changes needed.
- Password hashing uses `bcrypt` — production-grade, no changes needed.

### 6.2 What changes are needed for multi-user launch

| Area | Change Required |
|------|----------------|
| **Registration endpoint** | Add `POST /register` (currently only `POST /login`). Add email verification flow. |
| **Token storage** | Migrate from `localStorage` to `httpOnly + Secure + SameSite=Strict` cookies to prevent XSS token theft. Implement `/refresh` for session renewal. |
| **Rate limiting** | Scope `/login` rate limits per IP + per username, not just globally. |
| **Foreign key enforcement** | Enable `PRAGMA foreign_keys = ON` in SQLite (dev) and define `ON DELETE CASCADE` on all `user_id` FKs in PostgreSQL (prod). |
| **Row-level security (PostgreSQL)** | Enable RLS policies on all user-owned tables as a defence-in-depth layer, even though the app already filters by `user_id` in queries. |
| **Data isolation audit** | Run a full query audit: every `SELECT`/`UPDATE`/`DELETE` on user-owned tables must have `user_id = :sub` in the WHERE clause. Missing filters = data breach. |
| **AI context isolation** | Inference prompts must be assembled strictly from rows belonging to the authenticated user. Add a unit test per endpoint that asserts cross-user data does not appear in the context payload sent to the model. |
| **Password policy** | Enforce minimum length (12+ chars), breach detection (haveibeenpwned API or equivalent), and account lockout after N failed attempts. |
| **Audit log scoping** | `action_logs` must remain per-user. Add an admin-only audit log for registration, password resets, and account deletion events. |
| **GDPR / data deletion** | Implement `DELETE /account` that hard-deletes the user and all related rows (or soft-deletes with a 30-day grace period). |
| **Secrets rotation** | `JWT_SECRET` rotation requires invalidating all existing tokens. Implement `kid` (key ID) in the JWT header so multiple keys can be valid during rotation. |