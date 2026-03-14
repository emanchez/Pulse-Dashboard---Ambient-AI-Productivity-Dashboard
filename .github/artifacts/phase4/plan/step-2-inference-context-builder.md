# Step 2 — Inference Context Builder

## Purpose

Create the data collection and aggregation service that assembles all ambient signals (tasks, action logs, silence gaps, manual reports, system states) into structured JSON context suitable for injection into OZ prompts.

## Deliverables

- `services/inference_context.py` — async service that queries all relevant data sources and returns a unified `InferenceContext` Pydantic model
- `schemas/inference.py` — Pydantic models for the inference context structure (`InferenceContext`, `SilenceGap`, `TaskSummary`, `ReportSummary`, `WeeklySummary`)
- Backend tests for the context builder with known seed data

## Primary files to change (required)

- [code/backend/app/services/inference_context.py](code/backend/app/services/inference_context.py) (new)
- [code/backend/app/schemas/inference.py](code/backend/app/schemas/inference.py) (new)
- [code/backend/tests/test_inference_context.py](code/backend/tests/test_inference_context.py) (new)

## Detailed implementation steps

1. **Create `schemas/inference.py`:**
   ```python
   class TaskSummary(CamelModel):
       id: int
       name: str
       priority: str
       is_completed: bool
       days_open: int
       action_count: int  # number of ActionLog entries for this task
       last_action_at: datetime | None
   
   class SilenceGap(CamelModel):
       start: datetime
       end: datetime
       duration_hours: float
       explained: bool  # True if a ManualReport exists within the gap
       explanation: str | None  # Report title if explained
   
   class ReportSummary(CamelModel):
       id: int
       title: str
       body_preview: str  # first 200 chars — for co-planning ONLY; PromptBuilder omits this field from synthesis prompts
       word_count: int
       associated_task_ids: list[int]
       created_at: datetime
   
   class SystemStateSummary(CamelModel):
       mode_type: str
       start_date: datetime
       end_date: datetime
       requires_recovery: bool
       is_active: bool
   
   class WeeklySummary(CamelModel):
       total_actions: int
       tasks_completed: int
       tasks_created: int
       reports_written: int
       longest_silence_hours: float
       active_days: int  # days with at least 1 action
   
   class InferenceContext(CamelModel):
       """Complete context payload for OZ prompt injection."""
       period_start: datetime
       period_end: datetime
       tasks: list[TaskSummary]
       completed_tasks: list[TaskSummary]
       open_tasks: list[TaskSummary]
       silence_gaps: list[SilenceGap]
       reports: list[ReportSummary]
       system_state: SystemStateSummary | None
       weekly_summary: WeeklySummary
       is_returning_from_leave: bool  # True if a SystemState with requiresRecovery ended in the last 48h
   ```

2. **Create `services/inference_context.py`:**

   > **Cost note:** This service only queries and structures data — it never calls OZ. Its output feeds `PromptBuilder`, which enforces the `oz_max_context_chars` hard cap before any token is sent to OZ. Keep field sizes lean here to make that cap easier to stay within: `body_preview` is 200 chars max; task names are not truncated but notes are excluded entirely; silence gaps only include `start`, `end`, `duration_hours`, `explained`.

   ```python
   class InferenceContextBuilder:
       """Assembles ambient data into structured context for AI prompts."""
       
       LOOKBACK_DAYS: int = 7
       MAX_ACTIONS: int = 50
       MAX_REPORTS: int = 5
       SILENCE_THRESHOLD_HOURS: float = 48.0
       
       async def build(self, user_id: int, db: AsyncSession) -> InferenceContext:
           """Build full inference context for a user's last LOOKBACK_DAYS."""
           
       async def _get_tasks(self, user_id: int, db: AsyncSession) -> list[TaskSummary]:
           """Fetch all tasks with action counts."""
           
       async def _get_action_logs(self, user_id: int, db: AsyncSession, since: datetime) -> list[ActionLog]:
           """Fetch recent action logs, excluding auth events."""
           
       async def _compute_silence_gaps(self, 
           actions: list[ActionLog], 
           reports: list[ManualReport],
           system_states: list[SystemState]
       ) -> list[SilenceGap]:
           """Identify gaps > SILENCE_THRESHOLD_HOURS.
           Cross-reference with reports to mark gaps as 'explained'.
           Exclude gaps during active SystemState periods."""
           
       async def _get_reports(self, user_id: int, db: AsyncSession, since: datetime) -> list[ReportSummary]:
           """Fetch recent manual reports with body preview."""
           
       async def _get_system_state(self, user_id: int, db: AsyncSession) -> SystemStateSummary | None:
           """Get current active system state, if any."""
           
       async def _check_returning_from_leave(self, user_id: int, db: AsyncSession) -> bool:
           """Check if a SystemState with requiresRecovery ended in the last 48 hours."""
           
       async def _build_weekly_summary(self, 
           actions: list[ActionLog],
           tasks: list[TaskSummary],
           reports: list[ReportSummary],
           silence_gaps: list[SilenceGap]
       ) -> WeeklySummary:
           """Aggregate weekly statistics from collected data."""
   ```

3. **Silence Gap Algorithm:**
   - Fetch all `ActionLog` entries for the user in the last 7 days, ordered by `timestamp ASC`.
   - Walk the sorted list, computing `T_gap = actions[i+1].timestamp - actions[i].timestamp`.
   - If `T_gap > 48 hours`:
     - Check if any `ManualReport.created_at` falls within the gap window → mark `explained=True`.
     - Check if any `SystemState` overlaps the gap → exclude the gap entirely (intentional rest).
   - Also check the gap from the last action to `now()` — this is the "current silence."

4. **Return-from-leave detection:**
   - Query `SystemState` where `end_date <= now()` AND `end_date >= now() - 48h` AND `requires_recovery == True`.
   - If found, set `is_returning_from_leave = True`. This flag drives the Task Suggester's "Low Friction" mode (Step 4).

5. **Body preview for reports:**
   - `body_preview = report.body[:200].rstrip() + ("..." if len(report.body) > 200 else "")`
   - Strip HTML (already sanitized by bleach in Phase 3.2, but defensive).

## Integration & Edge Cases

- **Empty data:** If the user has no actions, tasks, or reports in the lookback window, the context should still be valid — `WeeklySummary` with all zeros, empty lists.
- **Action log auth exclusion:** Use the same `AUTH_ACTION_TYPES` filter from `stats.py` to exclude `LOGIN_SUCCESS`/`LOGIN_FAILED` events from the context.
- **Timezone consistency:** All datetime comparisons use naive UTC (matching the existing codebase pattern from Phases 1–3).
- **No persistence changes:** This step reads data only. No new tables or columns.
- **Context size discipline (cost):** `InferenceContextBuilder` is the last line of defence before tokens inflate the prompt. Never include full report bodies, task notes, or raw action log text. `PromptBuilder` (Step 1) enforces the `oz_max_context_chars` hard cap on serialised output, but the smaller the raw context, the less likely truncation silently drops important data. Prefer counts and summaries over raw values wherever the prompt wording allows it.

## Acceptance Criteria (required)

1. `from app.services.inference_context import InferenceContextBuilder` imports without error.
2. `InferenceContextBuilder.build(user_id, db)` returns an `InferenceContext` object with all fields populated.
3. Silence gaps correctly identify gaps > 48h from action log timestamps.
4. Silence gaps during an active `SystemState` are excluded.
5. Silence gaps with overlapping `ManualReport` entries are marked `explained=True`.
6. `is_returning_from_leave` is `True` when a `SystemState` with `requires_recovery=True` ended within 48h.
7. `weekly_summary.active_days` counts distinct days with at least one action log entry.
8. Context truncation: `tasks` list is capped at 100, `reports` at `MAX_REPORTS`, action logs at `MAX_ACTIONS`.
9. `InferenceContext.model_dump(by_alias=True)` produces valid camelCase JSON.
10. All existing 89+ tests pass with zero regressions.
11. `test_inference_context.py` adds ≥8 new tests.

## Testing / QA (required)

**New test file:** `code/backend/tests/test_inference_context.py`

Tests to add:
- `test_build_context_with_full_data` — seed user with tasks, actions, reports, system state → assert all fields populated correctly.
- `test_silence_gap_detection` — create actions with a 72h gap → assert one `SilenceGap` with `duration_hours ≈ 72`.
- `test_silence_gap_excluded_during_system_state` — create a gap overlapping a vacation → assert gap is not in result.
- `test_silence_gap_explained_by_report` — create a gap with a report in the middle → assert `explained=True`.
- `test_returning_from_leave_true` — create ended SystemState with `requires_recovery=True`, `end_date = now - 24h` → assert `is_returning_from_leave=True`.
- `test_returning_from_leave_false` — no recent ended SystemState → assert `False`.
- `test_empty_data` — user with no activity → assert valid context with zero values and empty lists.
- `test_context_serialization` — assert `model_dump(by_alias=True)` produces camelCase keys.
- `test_action_log_auth_exclusion` — seed auth events → assert they don't appear in action counts or silence gap calculation.

```bash
cd code/backend && python -m pytest tests/test_inference_context.py -v
```

**Manual QA checklist:**
1. With a seeded dev database, instantiate `InferenceContextBuilder` and call `build()` → inspect JSON output for completeness.
2. Verify silence gap calculation against manually counted gaps in the action log.

## Files touched (repeat for reviewers)

- [code/backend/app/services/inference_context.py](code/backend/app/services/inference_context.py) (new)
- [code/backend/app/schemas/inference.py](code/backend/app/schemas/inference.py) (new)
- [code/backend/tests/test_inference_context.py](code/backend/tests/test_inference_context.py) (new)

## Estimated effort

1–2 dev days

## Concurrency & PR strategy

- **Blocking steps:** `Blocked until: .github/artifacts/phase4/plan/step-1-oz-integration-layer.md` (uses `PromptBuilder` and `CamelModel` patterns established in Step 1)
- **Merge Readiness:** false (draft)
- **Branch:** `phase-4/step-2-inference-context-builder`
- Steps 3, 4, 5 depend on this step's `InferenceContext` model.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Silence gap algorithm is O(n) on action logs | Capped at `MAX_ACTIONS=50` most recent entries. Acceptable for single-user weekly cadence. |
| Large report bodies bloat context | `body_preview` truncates to 200 chars. Full body is never included in prompt context. |
| Cross-reference logic is complex | Each sub-query is independently tested. Integration test covers the full `build()` pipeline. |

## References

- [agents.md](../../agents.md) — Silence gap analysis logic, report density analysis
- [PDD.md](../../PDD.md) — §4.1 Silence Gap Analysis, §4.2 Dynamic Ambiguity Guard
- [step-1-oz-integration-layer.md](./step-1-oz-integration-layer.md) — PromptBuilder dependency

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
