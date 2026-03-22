# Agentic Reasoning & Prompts

## 1. The Inference Engine (OZ)

**Platform:** OZ (Warp cloud agent platform) via the `dashboard-assistant` Skill.

**Default Model:** claude-haiku-4 (cheapest capable model; configurable via `OZ_MODEL_ID`).

**Context Window:** ~8k characters (enforced by `oz_max_context_chars` config cap).

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

---

## 4. Data Privacy & Inference Isolation

### 4.1 The Golden Rule

**An inference payload must only ever contain data belonging to the authenticated user.** This is a hard constraint with no exceptions, regardless of whether the app is currently single-user. If this rule is violated at scale, it constitutes a data breach.

### 4.2 How Context is Assembled (Required Pattern)

All inference context (tasks, reports, action logs, system states, silence gaps) MUST be fetched using the `user_id` extracted from the JWT `sub` claim:

```python
# CORRECT — always scope queries by user_id before sending to OZ
tasks = await session.execute(
    select(Task)
    .where(Task.user_id == user_id)       # explicit user scope
    .where(Task.is_completed == False)
    .limit(50)
)

# NEVER do this — unscoped fetch
tasks = await session.execute(select(Task).limit(50))
```

The `inference_context.py` service is the single authorised builder of inference payloads. Any route that calls the inference engine MUST go through this service — never build a prompt inline in a route handler.

### 4.3 Context Size & Truncation

The model context window is 8k tokens. The `oz_max_context_chars` config cap (default 8000) enforces this at the service layer. When assembling context:

1. Prioritise recent data: last 7 days of action logs, 3 most recent reports.
2. Truncate oldest entries first when over the character budget.
3. Log the final character count at DEBUG level before dispatch.
4. Never silently drop data — if the context is truncated, include a metadata note (e.g. `"[N older actions omitted]"`) so the model knows the view is partial.

### 4.4 Audit Requirements for Multi-User

When the app is extended to multiple users, the following MUST be enforced per inference request:

| Check | How |
|-------|-----|
| Context rows belong to authenticated user | Assert `all(row.user_id == sub for row in context_rows)` before building prompt |
| No cross-user task/report IDs in the payload | Validate task IDs in synthesis input against the user's own task list |
| Inference result stored with correct `user_id` | `SynthesisReport.user_id = sub` on every write |
| Model response never echoed to a different user | Response is always returned only to the requesting user's session |

### 4.5 Sensitive Data Handling in Prompts

- **Reports and task names may contain personal/private content** (health issues, personal goals, financial data). Treat all inference inputs as sensitive PII.
- Never log the full prompt text at INFO or higher — log only metadata (user_id, context char count, model, timestamp).
- In production, ensure the OZ API key is stored securely and never committed to version control. Use environment variables or a secrets manager.
- If switching to a different cloud model provider in the future, require explicit user consent and document that data handling may change in the product UI and privacy policy.

---

## 5. Inference Rate Limiting & Abuse Prevention

### 5.1 Per-User Rate Caps

Rate limits are enforced at the service layer (`AIRateLimiter`) and tracked in `ai_usage_logs`, scoped by `user_id`. Current defaults:

| Feature | Cap | Window |
|---------|-----|--------|
| Sunday Synthesis | 3 | per week |
| Task Suggestions | 5 | per day |
| Co-Planning | 3 | per day |

### 5.2 Circuit Breaker

`OzClient` implements a circuit breaker that opens after repeated failures (timeout or 5xx from the model backend). When open:
- Return a `ServiceUnavailableError` rather than hanging.
- Surface a user-friendly message in the UI (not raw exception text).
- Log the failure reason server-side at ERROR level.

### 5.3 Multi-User Fairness (Future)

When multiple users are present, rate limits must be per-user (already the case via `user_id` scoping in `ai_usage_logs`). Add a global daily cap to prevent a single user from monopolising model capacity:

```python
# Example: global cap across all users
GLOBAL_SYNTHESIS_DAILY_CAP = 50  # adjust based on hardware
```

Add this as a configurable setting (`OZ_GLOBAL_DAILY_CAP`) and enforce it in `AIRateLimiter` before the per-user check.
