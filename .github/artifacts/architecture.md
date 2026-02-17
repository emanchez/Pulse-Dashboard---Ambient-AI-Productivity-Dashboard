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

- **Local-First:** All data stored in SQLite (ambient.db) initially.
- **Auth:** Even for a single user, JWT is strictly enforced to allow for future migration to a VPS/Cloud without refactoring.
- **Secrets:** SECRET_KEY and DB connection strings stored in .env.