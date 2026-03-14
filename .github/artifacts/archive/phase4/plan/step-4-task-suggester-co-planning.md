# Step 4 — Task Suggester & Co-Planning Backend

## Purpose

Implement the Task Suggester (Prompt B) and Co-Planning / Ambiguity Guard (Prompt C) endpoints. The Task Suggester generates AI-driven task recommendations with re-entry mode awareness. Co-Planning detects conflicting goals in manual reports and surfaces resolution questions.

## Deliverables

- `POST /ai/suggest-tasks` endpoint — returns 3–5 AI-generated task suggestions
- `POST /ai/co-plan` endpoint — analyzes a manual report for ambiguity and returns resolution questions
- `POST /ai/accept-tasks` endpoint — batch-accept suggested tasks into the user's real task list
- Re-entry mode logic: if `is_returning_from_leave == True`, bias suggestions toward low-friction tasks
- Extensions to `services/synthesis_service.py` or new `services/ai_service.py` for task suggestion and co-planning orchestration
- Backend tests with mocked OZ responses

## Primary files to change (required)

- [code/backend/app/api/ai.py](code/backend/app/api/ai.py) (extend with new endpoints)
- [code/backend/app/services/ai_service.py](code/backend/app/services/ai_service.py) (new)
- [code/backend/app/schemas/synthesis.py](code/backend/app/schemas/synthesis.py) (extend with suggestion/co-plan schemas)
- [code/backend/tests/test_ai.py](code/backend/tests/test_ai.py) (extend)

## Detailed implementation steps

1. **Extend `schemas/synthesis.py` with new request/response models:**
   ```python
   class TaskSuggestionRequest(CamelModel):
       """Optional context override for task suggestions."""
       focus_area: str | None = None  # e.g., "backend", "frontend", "documentation"
   
   class TaskSuggestionResponse(CamelModel):
       suggestions: list[SuggestedTask]
       is_re_entry_mode: bool  # True if suggestions are biased toward low-friction tasks
       rationale: str  # why these tasks were suggested
   
   class CoPlanRequest(CamelModel):
       report_id: int  # ID of the ManualReport to analyze
   
   class CoPlanResponse(CamelModel):
       has_conflict: bool
       conflict_description: str | None  # description of the detected conflict
       resolution_question: str | None  # question to resolve the ambiguity
       suggested_priority: str | None  # which path the AI recommends
   
   class AcceptTasksRequest(CamelModel):
       tasks: list[AcceptedTask]
   
   class AcceptedTask(CamelModel):
       name: str
       priority: str = "Medium"
       notes: str | None = None
   ```

2. **Create `services/ai_service.py`:**
   ```python
   class AIService:
       async def suggest_tasks(
           self, user_id: int, db: AsyncSession, focus_area: str | None = None
       ) -> TaskSuggestionResponse:
           """Generate task suggestions using Prompt B.
           
           0. Check rate limit: AIRateLimiter().check_limit(user_id, 'suggest', db)
              Raises HTTP 429 before any OZ call if daily limit (default: 5) is reached.
           1. Build inference context (Step 2)
           2. Check is_returning_from_leave → set re-entry mode
           3. Build Prompt B with context + re-entry flag
           4. Submit to OZ → parse response
           5. Record usage in ai_usage_logs (only on success)
           6. Return structured suggestions
           """
       
       async def co_plan(
           self, user_id: int, report_id: int, db: AsyncSession
       ) -> CoPlanResponse:
           """Analyze a manual report for ambiguity using Prompt C.
           
           0. Validate report ownership and minimum word count (< 20 words → return early, no OZ call)
           1. Check rate limit: AIRateLimiter().check_limit(user_id, 'coplan', db)
              Raises HTTP 429 before any OZ call if daily limit (default: 3) is reached.
           2. Fetch the ManualReport by ID (user-scoped)
           3. Fetch open tasks for context
           4. Build Prompt C with report body (max 1000 chars) + task list
           5. Submit to OZ → parse response
           6. Record usage in ai_usage_logs (only on success)
           7. Return conflict analysis
           
           NOTE: Short report check (step 0) happens BEFORE rate limit check.
           This intentional order means short reports don't consume a daily co-plan slot.
           """
       
       async def accept_tasks(
           self, user_id: int, tasks: list[AcceptedTask], db: AsyncSession
       ) -> list[int]:
           """Create real Task rows from accepted AI suggestions.
           Returns list of created task IDs.
           Uses the existing Task model creation pattern from tasks.py."""
   ```

3. **Add endpoints to `api/ai.py`:**
   ```python
   @router.post("/suggest-tasks")
   async def suggest_tasks(
       body: TaskSuggestionRequest = TaskSuggestionRequest(),
       current_user = Depends(get_current_user),
       db = Depends(get_db)
   ):
       if not settings.ai_enabled:
           raise HTTPException(503, "AI features are disabled")
       # Rate limit enforced inside AIService.suggest_tasks() — raises 429 if daily cap reached
       result = await AIService().suggest_tasks(current_user.id, db, body.focus_area)
       return result
   
   @router.post("/co-plan")
   async def co_plan(
       body: CoPlanRequest,
       current_user = Depends(get_current_user),
       db = Depends(get_db)
   ):
       if not settings.ai_enabled:
           raise HTTPException(503, "AI features are disabled")
       # Short-report check happens first in AIService.co_plan() (no rate limit slot consumed for short reports)
       # Rate limit enforced inside AIService.co_plan() after validation — raises 429 if daily cap reached
       result = await AIService().co_plan(current_user.id, body.report_id, db)
       return result
   
   @router.post("/accept-tasks", status_code=201)
   async def accept_tasks(
       body: AcceptTasksRequest,
       current_user = Depends(get_current_user),
       db = Depends(get_db)
   ):
       """Accept AI-suggested tasks and add them to the user's task list."""
       task_ids = await AIService().accept_tasks(current_user.id, body.tasks, db)
       return {"created_task_ids": task_ids}
   ```

4. **Re-entry mode logic in `suggest_tasks`:**
   - If `InferenceContext.is_returning_from_leave == True`:
     - Append to Prompt B: `"The user is returning from leave. Suggest 'Low Friction' tasks only (e.g., 'Update Readme', 'Organize Tags', 'Fix one UI padding issue')."`
     - Set `SuggestedTask.is_low_friction = True` for all returned suggestions.
     - Set `TaskSuggestionResponse.is_re_entry_mode = True`.

5. **Co-planning report validation:**
   - Fetch `ManualReport` by ID, verify `user_id` matches `current_user.id`.
   - If not found or wrong user, return 404.
   - If report body is too short (< 20 words), return `{ "has_conflict": false, "resolution_question": null }` — not enough content to analyze.

6. **`accept_tasks` creates real task rows:**
   - For each accepted task, create a `Task` with `user_id`, `name`, `priority`, `notes`.
   - This triggers the ActionLog middleware (event sourcing), recording the AI-suggested task creation.

## Integration & Edge Cases

- **Empty suggestions from OZ:** If OZ returns no suggestions or invalid JSON, return `{ "suggestions": [], "rationale": "Unable to generate suggestions at this time." }`.
- **Co-plan on archived reports:** Archived reports can still be analyzed — no status filter on the query.
- **Task name conflicts:** Accepted task names are not deduplicated against existing tasks. The user is responsible for reviewing suggestions before accepting.
- **ActionLog integration:** `POST /ai/accept-tasks` creates tasks, which the ActionLog middleware will capture. The action type will be "Created" — no special handling needed.
- **No new DB tables:** This step uses the existing `Task` model for accepted tasks and reads from `ManualReport`. No schema changes.- **Rate limit order of operations (cost):** The short-report check (`< 20 words`) in `co_plan` runs **before** the rate limit check. This ensures a bad request doesn't consume a daily co-plan slot. For `suggest_tasks`, the rate limit check is the very first thing — before context building — because there is no equivalent cheap pre-check. `accept_tasks` does **not** call OZ and has no rate limit.
- **Failed OZ calls are never recorded against limits:** Both `suggest_tasks` and `co_plan` only call `AIRateLimiter().record_usage()` after a successful OZ response is parsed. Errors from OZ (timeout, malformed JSON, circuit breaker open) do not consume a daily slot.
## Acceptance Criteria (required)

1. `POST /ai/suggest-tasks` with valid JWT returns 200 with `{ "suggestions": [...], "isReEntryMode": bool, "rationale": str }`.
2. Each suggestion in the array has `name`, `priority`, `rationale`, `isLowFriction`.
3. `POST /ai/suggest-tasks` without JWT returns 401.
4. `POST /ai/suggest-tasks` with `AI_ENABLED=false` returns 503.
5. `POST /ai/suggest-tasks` when the daily limit is exhausted returns 429 with reset time in message.
6. When `is_returning_from_leave == True`, all suggestions have `isLowFriction: true` and `isReEntryMode: true`.
7. `POST /ai/co-plan` with a valid `report_id` returns 200 with `{ "hasConflict": bool, "conflictDescription": str|null, "resolutionQuestion": str|null }`.
8. `POST /ai/co-plan` with an invalid or other user's `report_id` returns 404.
9. `POST /ai/co-plan` with a report shorter than 20 words returns `{ "hasConflict": false }` WITHOUT calling OZ and WITHOUT consuming a rate limit slot.
10. `POST /ai/co-plan` when the daily limit is exhausted returns 429 with reset time in message.
11. `POST /ai/accept-tasks` with a list of tasks returns 201 with `{ "createdTaskIds": [int, ...] }`. (`accept-tasks` has no rate limit.)
12. Accepted tasks appear in `GET /tasks/` for the authenticated user.
13. Accepted tasks are recorded in the ActionLog.
14. All existing tests pass with zero regressions.
15. `test_ai.py` extends to ≥20 total tests (9 from Step 3 + ≥11 new).

## Testing / QA (required)

**Extend:** `code/backend/tests/test_ai.py`

New tests:
- `test_suggest_tasks_success` — mock OZ with 3 suggestions → assert 200 with correct shape.
- `test_suggest_tasks_unauthorized` — no JWT → assert 401.
- `test_suggest_tasks_ai_disabled` — assert 503.
- `test_suggest_tasks_re_entry_mode` — mock context with `is_returning_from_leave=True` → assert `isReEntryMode: true` and all `isLowFriction: true`.
- `test_suggest_tasks_rate_limited` — insert 5 `ai_usage_logs` rows for `endpoint="suggest"` today → assert 429 and OZ was never called.
- `test_co_plan_success` — create a report with conflicting content, mock OZ → assert 200 with conflict detected.
- `test_co_plan_report_not_found` — invalid report ID → assert 404.
- `test_co_plan_user_scoping` — report belongs to another user → assert 404.
- `test_co_plan_short_report` — report with < 20 words → assert `hasConflict: false` without calling OZ **and** assert NO `ai_usage_logs` entry was created.
- `test_co_plan_rate_limited` — insert 3 `ai_usage_logs` rows for `endpoint="coplan"` today → assert 429 and OZ was never called.
- `test_accept_tasks_success` — accept 2 tasks → assert 201 and tasks appear in `GET /tasks/`.
- `test_accept_tasks_action_log` — accept a task → assert ActionLog entry exists with type "Created".

```bash
cd code/backend && python -m pytest tests/test_ai.py -v
```

**Manual QA checklist:**
1. Create a few tasks and reports in the dashboard.
2. `POST /ai/suggest-tasks` → inspect suggestions for relevance.
3. Accept one suggestion → verify it appears in the task list.
4. Create a report with conflicting content ("I want to refactor auth AND rebuild the frontend") → `POST /ai/co-plan` → verify conflict detected.
5. Set a SystemState ending today with `requiresRecovery=True` → `POST /ai/suggest-tasks` → verify low-friction suggestions.

## Files touched (repeat for reviewers)

- [code/backend/app/api/ai.py](code/backend/app/api/ai.py) (extend)
- [code/backend/app/services/ai_service.py](code/backend/app/services/ai_service.py) (new)
- [code/backend/app/schemas/synthesis.py](code/backend/app/schemas/synthesis.py) (extend)
- [code/backend/tests/test_ai.py](code/backend/tests/test_ai.py) (extend)

## Estimated effort

2 dev days

## Concurrency & PR strategy

- **Blocking steps:**
  - `Blocked until: .github/artifacts/phase4/plan/step-3-sunday-synthesis.md` (ai router, OZ client integration patterns)
- **Merge Readiness:** false (draft)
- **Branch:** `phase-4/step-4-task-suggester-co-planning`
- Step 7 (Reasoning Sidebar UI) depends on this step's endpoints.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| OZ generates irrelevant or nonsensical task suggestions | Prompt includes clear format instructions. UI always requires user acceptance (HITL). Suggestions are never auto-added to the task list. |
| Co-planning prompt fails to detect conflicts | Short-circuit for short reports (< 20 words). For longer reports, include open tasks as context so the AI can cross-reference. If OZ returns no conflict, that's an acceptable answer. |
| `accept_tasks` could create duplicate tasks | Tasks are user-reviewed before acceptance. Name dedup is a future enhancement, not MVP. |

## References

- [agents.md](../../agents.md) — Prompt B (Task Suggester / The Architect), Prompt C (Co-Planning / Ambiguity Guard)
- [PDD.md](../../PDD.md) — §4.2 Dynamic Ambiguity Guard, §3.3 System Pause re-entry protocol
- [step-2-inference-context-builder.md](./step-2-inference-context-builder.md) — InferenceContext, `is_returning_from_leave`
- [step-3-sunday-synthesis.md](./step-3-sunday-synthesis.md) — AI router, OZ integration patterns

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
