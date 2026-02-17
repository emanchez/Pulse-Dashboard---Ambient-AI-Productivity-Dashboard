# Agentic Reasoning & Prompts

## 1. The Inference Engine (Ollama)

**Model:** Llama 3 (8B) or Mistral (7B) optimized for instruction following.

**Context Window:** 8k tokens (sufficient for 1 week of logs).

## 2. Inferred Commitment Analysis

### Logic: Silence Gap

- Fetch ActionLog entries for the last 7 days.
- Calculate $T_{gap}$ (Time delta between consecutive logs).
- **Rule:** If SystemState == Vacation, ignore gaps.
- **Rule:** If $T_{gap} > 48h$ AND SystemState != Vacation, flag as Stagnation.

### Logic: Report Density

- Analyze ManualReport.body.
- **Rule:** If wordCount < 50 AND associatedTaskIds is Empty -> Flag as Low Context.
- **Rule:** If body contains keywords ("Stuck", "Error", "Hard") -> Flag as Blocked (Not Stagnant).

## 3. Prompt Engineering

### Prompt A: Sunday Synthesis (The Narrator)

**Role:** You are an analytical productivity coach.

**Input:**
- A list of completed tasks (JSON).
- A list of "Silence Gaps" > 48 hours.
- A list of Manual Reports.
- Current System State (Active/Vacation).

**Task:**
1. Write a 1-paragraph narrative summary of the user's week.
2. Identify the "Theme" of the week (e.g., "Heavy Backend Focus" or "Creative Stagnation").
3. If there are silence gaps, cross-reference them with Manual Reports.
   - If a report explains the gap (e.g., "I was sketching"), praise the "Unlogged Effort."
   - If no report exists, gently highlight the "Lost Time."

**Output Format:** JSON { "summary": str, "theme": str, "commitmentScore": 1-10 }

### Prompt B: Task Suggester (The Architect)

**Role:** You are a technical project manager.

**Input:** User's current open tasks and last week's "Stuck Points".

**Task:**
1. Suggest 3 discrete tasks for next week.
2. If the user is returning from Vacation (SystemState.requiresRecovery == True), suggest "Low Friction" tasks (e.g., "Update Readme", "Organize Tags").
3. If the user is Stagnant, suggest a "Small Win" (e.g., "Fix one UI padding issue").

**Output Format:** JSON List of Task Objects.

### Prompt C: Co-Planning (Ambiguity Guard)

**Role:** You are a decision support assistant.

**Input:** A Manual Report containing conflicting goals (e.g., "I want to do X and Y").

**Task:**
1. Identify the conflict.
2. Generate a question to resolve it.

**Output:** "I noticed you want to do X and Y. Which is the priority for Monday?"
