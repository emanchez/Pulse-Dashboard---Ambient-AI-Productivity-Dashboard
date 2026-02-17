# Sprint Plan: [Sprint Name/Number]

## 1. High-Level Objective
**Goal:** [One sentence summary of what "Done" looks like]
**PDD Reference:** [Link to specific PDD Section, e.g., "Phase 1: Skeleton & Auth"]
**Timeline:** [Start Date] - [End Date]

## 2. Architectural Constraints (Guardrails)
* **Tech Stack:** [e.g., FastAPI, Next.js, SQLite, Ollama]
* **Critical Rules:**
    * [ ] No external AI APIs (Ollama only).
    * [ ] Strict Typing (Python Pydantic / TypeScript Interfaces).
    * [ ] Mobile-First "Bento Box" responsive design.
    * [ ] [Any specific constraint for this sprint, e.g., "No UI styling yet, logic only"]

## 3. Execution Roadmap
*Instructions for Agent: Do not write code here. Describe logical steps only.*

### Phase [X]: [Phase Name]

#### Stage A: [Stage Name - e.g., Database Models]
- [ ] **TASK-[ID]**: [Task Name]
    - **Logic:** [Brief description of what data changes or logic flows]
    - **File Targets:** `backend/app/models/...`, `backend/app/api/...`
    - **Dependency:** [Must be done after Task X]

#### Stage B: [Stage Name - e.g., API Endpoints]
- [ ] **TASK-[ID]**: [Task Name]
    - **Logic:** [Brief description of inputs/outputs]
    - **File Targets:** `backend/app/api/routes/...`
    - **Validation:** [How to verify success without running the app? e.g., "Endpoint returns 200 OK"]

#### Stage C: [Stage Name - e.g., Frontend Integration]
- [ ] **TASK-[ID]**: [Task Name]
    - **Logic:** [UI Component behavior]
    - **File Targets:** `frontend/components/...`
    - **Visual Check:** [Description of expected UI state]

## 4. Verification Checklist (Definition of Done)
- [ ] All Typescript interfaces match Pydantic models (Type Sync run).
- [ ] Application builds without linting errors.
- [ ] Critical path (e.g., Login -> Save Task) functions end-to-end.

## 5. Risk Assessment (Agent Reasoning)
* **Ambiguity:** [Identify any vague requirements in the PDD]
* **Complexity:** [Identify the hardest part of this sprint]