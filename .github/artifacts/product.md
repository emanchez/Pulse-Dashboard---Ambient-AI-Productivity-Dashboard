# Product Design Document (PDD)

## 1. Strategic Vision

**The Problem:** The user experiences a "Loss of Drive" and "Directionless Development" after the 9-to-5 workday.

**The Solution:** A dashboard that shifts from Active Data Entry (friction) to Passive Strategic Observation (ambient). The system acts as a "Spectrum Analyzer" for productivity, using AI to infer commitment levels from silence gaps.

## 2. User Personas

- **The Power User (Tactical):** Logs into the dashboard to CRUD tasks, move cards, and write detailed manual reports.
- **The Passive Observer (Strategic):** Checks the dashboard only for the "Sunday Synthesis" to understand weekly trends and receive AI-generated tasks.

## 3. Core Features

### 3.1 Ambient Data Ingestion

- **Action Logging:** Every meaningful interaction (Task Complete, Priority Change) is logged invisibly.
- **Silence Detection:** The system monitors the time delta ($T_{gap}$) between logs. A gap > 48h triggers a "Stagnation" state.

### 3.2 Manual Reporting (The "Brain Dump")

- **Structured Input:** A text interface for qualitative updates (Blockers, Sketches, Doubts).
- **Density Analysis:** AI evaluates word count and task links to determine if the user is "Engaged" or "Slipping."

### 3.3 System Pause (Vacation Mode)

- **Authorized Rest:** User can schedule "Leave" dates.
- **Logic Override:** During these dates, Silence Detection is paused.
- **Re-entry Protocol:** AI suggests low-friction "ramp-up" tasks upon return (Opt-out available).

### 3.4 Sunday Synthesis

- **Weekly Narrative:** A generated story of the week's effort.
- **Task Suggestion:** 3-5 tasks generated based on the previous week's stuck points.

## 4. UI/UX Specification

**Layout:** The Bento Box Grid

- **Zone A (Pulse):** Top-Left. System Health, Silence Indicator (Time since last action), Auth Status.
- **Zone B (Inbox):** Center. Active Task List with priority color codes (Red/Yellow/Blue).
- **Zone C (Reasoning):** Right Sidebar. AI Inference Cards (e.g., "You seem stuck on Backend, switch to Drawing?").
- **Zone D (Report Hub):** Bottom/Floating. Quick-entry text area for daily reports.

**State-Aware Styling**

- **Engaged (Green/Slate):** High velocity, recent logs.
- **Stagnant (Amber/Charcoal):** Gap > 48h.
- **Paused (Blue/Gray):** Vacation mode active.

## 5. MVP Roadmap

- **Phase 1:** Skeleton, JWT Auth, Type Sync.
- **Phase 2:** Task CRUD, ActionLog Middleware, Silence Indicator.
- **Phase 3:** Manual Reporting, System Pause Scheduler.
- **Phase 4:** LLM Inference Layer (LLMClient), Sunday Synthesis Modal.