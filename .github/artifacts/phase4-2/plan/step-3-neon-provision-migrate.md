# Step 3 — Provision Neon Database & Migrate Data from SQLite

## Purpose

Provision a Neon serverless PostgreSQL database, run Alembic migrations to create the production schema, and migrate all existing data from the local `dev.db` (SQLite) to the cloud database. This step transitions the project's data layer from a local file to a managed, production-grade PostgreSQL instance.

## 🔴 ABSOLUTE BLOCKER — User Action Required

> **This step cannot begin until the user has:**
> 1. Created a **Neon account** at [console.neon.tech](https://console.neon.tech)
> 2. Created a **Neon project** (e.g. "pulse-prod")
> 3. Obtained the **PostgreSQL connection string** (with pooled endpoint) from the Neon dashboard
>
> The connection string format: `postgresql+asyncpg://<user>:<pass>@<host>/<dbname>?sslmode=require`
>
> **Agents cannot create cloud accounts or obtain credentials.**

## Deliverables

- Neon PostgreSQL project provisioned with production database
- `data/dev.db` backed up as `data/dev.db.pre-deploy.bak`
- Migration script (`scripts/migrate_sqlite_to_pg.py`) that exports all SQLite data and imports it into PostgreSQL
- All Alembic migrations run against the Neon database (`alembic upgrade head`)
- Row count validation confirming data integrity post-migration
- Production `DATABASE_URL` documented (not committed to git)

## Primary files to change

- [code/backend/scripts/migrate_sqlite_to_pg.py](code/backend/scripts/migrate_sqlite_to_pg.py) (new)
- [code/backend/.env.production.example](code/backend/.env.production.example) (new)

## Detailed implementation steps

1. **🔴 USER: Create Neon project:**
   - Go to [console.neon.tech](https://console.neon.tech)
   - Click "New Project"
   - Name: `pulse-prod`
   - Region: Choose closest to your location (e.g. `us-east-1` for US East)
   - PostgreSQL version: 16 (latest)
   - Copy the **pooled connection string** from the dashboard

2. **🔴 USER: Provide the connection string to the agent/script:**
   - Format: `postgresql+asyncpg://neondb_owner:<password>@<endpoint-id>-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require`
   - **Never commit this to git.** Store it in a `.env.production` file (gitignored) or provide it as an argument.

3. **Back up dev.db:**
   ```bash
   cp code/backend/data/dev.db code/backend/data/dev.db.pre-deploy.bak
   ```

4. **Create `.env.production.example`:**
   ```env
   # Production environment configuration
   # Copy to .env.production and fill in actual values
   APP_ENV=prod
   DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>/<db>?sslmode=require
   JWT_SECRET=<generate with: openssl rand -hex 32>
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   FRONTEND_CORS_ORIGINS=https://<your-frontend-domain>
   LLM_PROVIDER=anthropic
   LLM_API_KEY=<your-llm-api-key>
   LLM_MODEL_ID=claude-3-5-haiku-latest
   AI_ENABLED=true
   ```

5. **Run Alembic migrations against Neon:**
   ```bash
   cd code/backend
   DATABASE_URL="postgresql+asyncpg://..." alembic upgrade head
   ```
   This creates all tables with the hardened schema (FKs, NOT NULL, indexes) from Steps 1–2.

6. **Create and run the SQLite → PostgreSQL migration script** (`scripts/migrate_sqlite_to_pg.py`):
   - Opens `dev.db` with `sqlite3` (synchronous read)
   - Opens a connection to the Neon PostgreSQL database with `asyncpg`
   - For each table in order (respecting FK dependencies):
     1. `users` (no dependencies)
     2. `tasks` (depends on `users`)
     3. `action_logs` (depends on `users`, `tasks`)
     4. `session_logs` (depends on `users`, `tasks`)
     5. `manual_reports` (depends on `users`)
     6. `system_states` (depends on `users`)
     7. `ai_usage_logs` (depends on `users`)
     8. `synthesis_reports` (depends on `users`)
   - For each table:
     - `SELECT *` from SQLite
     - `INSERT INTO` PostgreSQL (use `ON CONFLICT DO NOTHING` for idempotency)
   - Handle type conversions:
     - SQLite `TEXT` datetime → PostgreSQL `TIMESTAMP`
     - SQLite `INTEGER` boolean (0/1) → PostgreSQL `BOOLEAN`
     - SQLite `TEXT` JSON → PostgreSQL `JSONB` (if column type differs)
   - Print row counts per table for verification

7. **Validate migration:**
   ```bash
   # Compare row counts
   python scripts/migrate_sqlite_to_pg.py --validate-only
   ```
   Expected output:
   ```
   users:             SQLite=1   PostgreSQL=1   ✓
   tasks:             SQLite=N   PostgreSQL=N   ✓
   action_logs:       SQLite=N   PostgreSQL=N   ✓
   ...
   ```

8. **Verify with a direct query:**
   ```bash
   # Using psql or neon's SQL editor:
   SELECT COUNT(*) FROM tasks;
   SELECT id, username FROM users;
   ```

## Integration & Edge Cases

- **UUID format:** SQLite stores UUIDs as `VARCHAR(36)`. PostgreSQL can handle these as `TEXT`/`VARCHAR` — no conversion needed since our models use `String(36)` not native `UUID`.
- **DateTime format:** SQLite stores datetimes as ISO-8601 strings. PostgreSQL `TIMESTAMP` accepts these. The `asyncpg` driver handles the conversion.
- **JSON columns:** `manual_reports.associated_task_ids`, `manual_reports.tags` are stored as JSON. SQLite stores as `TEXT`, PostgreSQL uses `JSON` type. Alembic migration should declare the column as `JSON` on PostgreSQL.
- **Boolean columns:** SQLite uses `0`/`1` integers. `asyncpg` expects `True`/`False`. The migration script must convert.
- **Alembic version table:** Running `alembic upgrade head` on Neon creates the `alembic_version` table. This is expected and should not be migrated from SQLite.
- **Neon connection pooling:** Use the `-pooler` endpoint (not direct) for better connection management. Neon's free tier limits direct connections.

## Acceptance Criteria

1. 🔴 Neon project exists and connection string is valid (user-verified).
2. `alembic upgrade head` completes successfully against the Neon database.
3. All 8 tables exist in Neon with correct schemas (FKs, NOT NULL, indexes from Step 2).
4. Row counts match between `dev.db` and the Neon database for all tables.
5. `SELECT * FROM users` returns the `devuser` record with the correct UUID.
6. `dev.db.pre-deploy.bak` backup file exists.
7. `.env.production.example` contains all required environment variables with placeholder values.

## Testing / QA

### Automated
```bash
cd code/backend

# Backup
cp data/dev.db data/dev.db.pre-deploy.bak

# Run migrations on Neon
DATABASE_URL="postgresql+asyncpg://..." alembic upgrade head

# Migrate data
python scripts/migrate_sqlite_to_pg.py \
  --sqlite-path data/dev.db \
  --pg-url "postgresql+asyncpg://..."

# Validate
python scripts/migrate_sqlite_to_pg.py \
  --sqlite-path data/dev.db \
  --pg-url "postgresql+asyncpg://..." \
  --validate-only
```

### Manual
1. Open the Neon dashboard SQL editor and run `SELECT COUNT(*) FROM tasks;` — should match local count.
2. Run `SELECT id, username FROM users;` — should show `devuser` with the same UUID as in local `dev.db`.
3. Verify the `alembic_version` table exists and contains the latest migration hash.

## Files touched

- [code/backend/scripts/migrate_sqlite_to_pg.py](code/backend/scripts/migrate_sqlite_to_pg.py) (new)
- [code/backend/.env.production.example](code/backend/.env.production.example) (new)
- [code/backend/data/dev.db.pre-deploy.bak](code/backend/data/dev.db.pre-deploy.bak) (new, backup)

## Estimated effort

1 dev day (excluding user account setup time)

## Concurrency & PR strategy

- Branch: `phase-4.2/step-3-neon-provision-migrate`
- Blocking steps:
  - `Blocked until: .github/artifacts/phase4-2/plan/step-2-schema-hardening.md`
  - **🔴 Blocked until: User provides Neon DATABASE_URL**
- Merge Readiness: true

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Neon free tier storage limit (0.5 GB) exceeded | Single-user app with text data — unlikely to exceed 0.5 GB for years. Monitor in Neon dashboard. |
| Connection string accidentally committed to git | `.env.production` is gitignored. `.env.production.example` has placeholders only. Add a pre-commit hook check. |
| Data corruption during migration | Backup exists (`dev.db.pre-deploy.bak`). Migration script uses `ON CONFLICT DO NOTHING` for idempotency. Validate row counts after. |
| Neon scale-to-zero causes first-request latency | Cold start is ~500ms on Neon free tier. Acceptable for single-user. |
| SQLite → PostgreSQL type incompatibility | Migration script handles type conversions explicitly (boolean, datetime, JSON). |

## References

- [Neon documentation](https://neon.tech/docs) — Connection pooling, free tier limits
- [architecture.md §5.2](../../architecture.md) — Migration Discipline
- [copilot-instructions.md](../../copilot-instructions.md) — Hard-won lesson: `create_all` does not migrate

## Author Checklist (must complete before PR)
- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
