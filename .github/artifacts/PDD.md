# Product Design Document: Ambient AI Productivity Dashboard

## 1. Strategic Foundation: The "Goal-First" Lighthouse

The primary objective is to transition from Active Data Entry (high friction) to Passive Strategic Observation (low friction). The system acts as a "Spectrum Analyzer" for personal productivity, using Ambient AI to infer behavioral patterns from interaction gaps rather than subjective self-reporting.

### 1.1 User Story Mapping

- As a Power User, I want Agentic Orchestration so that I can automate the synthesis of my week's work without manual calculation.
- As a Passive Observer, I want Autonomous Background Ingestion so that the system identifies "Stagnation Gaps" without me needing to log into the dashboard daily.
- As a Sole User, I want Human-in-the-Loop (HITL) Verification so that I can validate significant AI suggestions before they are added to my permanent task list.

## 2. Technical Architecture & ADRs

| Layer      | Technology          | Role |
|------------|---------------------|------|
| Frontend   | Next.js (TypeScript)| Hybrid UI utilizing Progressive Disclosure. |
| Backend    | FastAPI (Python)    | High-performance orchestration of Pydantic AI agents. |
| Database   | SQLAlchemy          | Local event-sourcing via SQLite/Postgres. |
| Intelligence| Ollama             | Local-first LLM to prioritize privacy and zero latency/cost. |
| Type Sync  | @hey-api/openapi-ts | Prevents "Maintenance Madness" by automating FE/BE parity. |

### 2.1 Architectural Decision Records (ADRs)

- **ADR-001: Local-First AI (Ollama).** Context: Privacy and cost. Decision: Use Ollama. Consequence: Reduced cloud dependencies; requires local GPU/CPU resources.
- **ADR-002: Event Logging (ActionLog).** Context: Need for ambient sensing. Decision: Every task update triggers an immutable log entry. Consequence: Enables deep historical analysis for Sunday Synthesis.

## 3. Core Data Models

### 3.1 Task Schema (The Unit of Work)

Defines core actionable items; the primary source of truth for work status.

- id: UUID
- name: String
- priority: Enum (Low, Medium, High)
- tags: String (CSV)
- isCompleted: Boolean
- dateCreated/Updated/Deadline: DateTime
- notes: Text

### 3.2 ActionLog (The Ambient Signal)

Captures every significant interaction to create a high-fidelity timeline for gap analysis.

- timestamp: DateTime
- taskId: UUID
- actionType: Enum
- changeSummary: Text

### 3.3 ManualReport (Inference Input)

Stores qualitative "brain dumps" parsed by AI to extract project context and blockers.

- id: UUID
- title: String
- body: Text
- wordCount: Integer
- associatedTaskIds: JSON Array
- createdAt: DateTime

### 3.4 SystemState (Pause/Vacation Mode)

Manages scheduled inactivity to distinguish intentional rest from stagnation.

- id: UUID
- modeType: Enum
- startDate: DateTime
- endDate: DateTime
- requiresRecovery: Boolean
- description: Text

## 4. Agentic Reasoning: Inferred Commitment & Co-Planning

### 4.1 Silence Gap Analysis

- **Metrics:** If $T_{gap} > 48$ hours, the AI flags a "Commitment Warning."
- **Inference:** Ollama reviews gaps to detect drive loss.

### 4.2 Dynamic Ambiguity Guard (HITL)

The system employs a "Proactive Pause" when faced with ambiguity:

- **Co-Planning:** If a Manual Report suggests multiple conflicting tasks, the AI surfaces a "Decision Card" asking: "I see two paths for the 'API refactor.' Should we prioritize the Auth layer or the DB layer first?"
- **Opt-In Recovery:** Upon a SystemState end date, the AI asks: "Resume normal operations or activate 'Re-entry Mode' (low-friction tasks) for 48 hours?"

### 4.3 Sunday Synthesis

- **Reasoning:** Ollama looks for the "Ghost in the Machine"—patterns where tasks move without logs or reports lacks density.
- **Output:** Strategic narrative and grounded Commitment Assumption.

## 5. UI/UX Strategy: The "Pulse" Dashboard

- **Layout:** "Bento Box" Grid (Zone A: Pulse, Zone B: Tasks, Zone C: Reasoning, Zone D: Reports).
- **Information Hierarchy:** Progressive Disclosure—surface KPIs first; allow drill-downs into raw logs.
- **State-Aware Styling:** Palette shifts from Emerald (Engaged) to Amber (Stagnant) or Sky Blue (Paused).

## 6. MVP Implementation Roadmap

### Phase 1: Skeleton & Agentic Prototyping

- **Backend:** FastAPI + JWT + SQLAlchemy.
- **Prototyping:** Utilize GitHub Copilot Agent Mode to generate Pydantic models and skeleton API.
- **UI/UX:** Basic Bento shell and Type Sync automation.

### Phase 2: Ambient Sensing & Tactical CRUD

- **Backend:** ActionLog middleware.
- **Frontend:** Task List with Batch Save interaction.
- **UI/UX:** Implement Silence Indicator and priority color-coding.

### Phase 3: Qualitative Inputs & System Pauses

- **Backend:** Manual Report & SystemState endpoints.
- **Frontend:** Report creation with Task Linking (drag-and-drop).
- **UI/UX:** State-aware palette shifting for Vacation Mode.

### Phase 4: Sunday Synthesis & Co-Planning

- **Backend:** Ollama orchestration for Synthesis and Ambiguity Guard.
- **Frontend:** Sunday Modal and Reasoning Sidebar for Inference Cards.
- **UI/UX:** Implement Ghost List to visualize wheel-spinning tasks.