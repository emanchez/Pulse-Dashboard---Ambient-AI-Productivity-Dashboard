# Step 5 — Ghost List & Analytics Optimization

## Purpose

Implement the Ghost List feature (tasks showing signs of wheel-spinning) and optimize the analytics layer by adding composite indexes and moving the flow calculation from Python-memory to SQL aggregation. This step addresses pre-existing tech debt items M-1, M-2, and M-3 from the Phase 3.2 audit.

## Deliverables

- `GET /stats/ghost-list` endpoint — returns tasks with low activity relative to age, flagging "wheel-spinning" patterns
- `GET /stats/weekly-summary` endpoint — lightweight summary stats for the current week (useful for both UI display and context building)
- Composite index on `action_logs(user_id, timestamp)` (M-1)
- Composite index on `session_logs(user_id, ended_at)` (M-2)
- Optimized flow state calculation using SQL `GROUP BY` aggregation (M-3)
- Backend tests for ghost list, weekly summary, and index presence

## Primary files to change (required)

- [code/backend/app/api/stats.py](code/backend/app/api/stats.py) (add ghost-list and weekly-summary endpoints)
- [code/backend/app/services/ghost_list_service.py](code/backend/app/services/ghost_list_service.py) (new)
- [code/backend/app/schemas/stats.py](code/backend/app/schemas/stats.py) (extend with ghost list and weekly summary schemas)
- [code/backend/app/models/action_log.py](code/backend/app/models/action_log.py) (add composite index)
- [code/backend/app/models/session_log.py](code/backend/app/models/session_log.py) (add composite index)
- [code/backend/app/services/flow_state.py](code/backend/app/services/flow_state.py) (optimize calculation)
- [code/backend/tests/test_ghost_list.py](code/backend/tests/test_ghost_list.py) (new)
- [code/backend/tests/test_stats.py](code/backend/tests/test_stats.py) (extend)

## Detailed implementation steps

1. **Add composite indexes:**

   In `models/action_log.py`:
   ```python
   __table_args__ = (
       Index('ix_action_logs_user_ts', 'user_id', 'timestamp'),
   )
   ```

   In `models/session_log.py`:
   ```python
   __table_args__ = (
       Index('ix_session_logs_user_ended', 'user_id', 'ended_at'),
   )
   ```

   **Migration note:** These indexes won't be auto-created on existing tables by `create_all`. Add a migration script `scripts/migrate_add_indexes.py`:
   ```python
   # CREATE INDEX IF NOT EXISTS ix_action_logs_user_ts ON action_logs(user_id, timestamp);
   # CREATE INDEX IF NOT EXISTS ix_session_logs_user_ended ON session_logs(user_id, ended_at);
   ```

2. **Create `services/ghost_list_service.py`:**
   ```python
   class GhostListService:
       """Identifies 'wheel-spinning' tasks — open tasks with suspicious activity patterns."""
       
       STALE_DAYS_THRESHOLD: int = 14  # open for > 14 days
       LOW_ACTIVITY_THRESHOLD: int = 2  # fewer than 2 actions in the last 14 days
       
       async def get_ghost_list(self, user_id: int, db: AsyncSession) -> list[GhostTask]:
           """Find tasks that show signs of wheel-spinning:
           1. Open (not completed) for > STALE_DAYS_THRESHOLD days
           2. With fewer than LOW_ACTIVITY_THRESHOLD actions in that period
           3. OR tasks with many edits but no status progression (edited > 3 times but still open)
           """
           # Query: 
           # SELECT t.id, t.name, t.priority, t.date_created, 
           #        COUNT(al.id) as action_count,
           #        MAX(al.timestamp) as last_action
           # FROM tasks t
           # LEFT JOIN action_logs al ON al.task_id = t.id AND al.user_id = t.user_id
           # WHERE t.user_id = :user_id AND t.is_completed = False
           # GROUP BY t.id
           # HAVING (julianday('now') - julianday(t.date_created)) > 14
           #   AND (COUNT(al.id) < 2 OR COUNT(al.id) > 5)
   ```

3. **Extend `schemas/stats.py`:**
   ```python
   class GhostTask(CamelModel):
       id: int
       name: str
       priority: str
       days_open: int
       action_count: int
       last_action_at: datetime | None
       ghost_reason: str  # "stale" | "wheel-spinning" | "abandoned"
   
   class GhostListResponse(CamelModel):
       ghosts: list[GhostTask]
       total: int
   
   class WeeklySummaryResponse(CamelModel):
       total_actions: int
       tasks_completed: int
       tasks_created: int
       reports_written: int
       sessions_completed: int
       longest_silence_hours: float
       active_days: int
       period_start: datetime
       period_end: datetime
   ```

4. **Add endpoints to `api/stats.py`:**
   ```python
   @router.get("/stats/ghost-list")
   async def ghost_list(
       current_user = Depends(get_current_user),
       db = Depends(get_db)
   ):
       result = await GhostListService().get_ghost_list(current_user.id, db)
       return GhostListResponse(ghosts=result, total=len(result))
   
   @router.get("/stats/weekly-summary")
   async def weekly_summary(
       current_user = Depends(get_current_user),
       db = Depends(get_db)
   ):
       """Aggregate stats for the current week (Mon-Sun)."""
       result = await GhostListService().get_weekly_summary(current_user.id, db)
       return result
   ```

5. **Optimize flow state calculation (M-3):**

   Current implementation in `services/flow_state.py` fetches all `ActionLog.timestamp` values into Python memory, then loops to bucket them into 30-minute intervals.

   Optimized approach — SQL aggregation:
   ```python
   # SQLite: strftime('%H', timestamp) for hour extraction
   # GROUP BY hour-bucket, count actions per bucket
   # This reduces memory footprint from O(n) to O(buckets)
   
   stmt = (
       select(
           func.strftime('%Y-%m-%d %H:%M', 
               func.datetime(ActionLog.timestamp, 
                   func.printf('-%d minutes', func.cast(func.strftime('%M', ActionLog.timestamp), Integer) % 30)
               )
           ).label('bucket'),
           func.count().label('action_count')
       )
       .where(ActionLog.user_id == user_id)
       .where(ActionLog.timestamp >= since)
       .where(ActionLog.action_type.notin_(AUTH_ACTION_TYPES))
       .group_by('bucket')
       .order_by('bucket')
   )
   ```
   Fallback: If the SQL aggregation proves too complex for SQLite's limited `date_trunc` support, use a simpler approach — `GROUP BY strftime('%H', timestamp)` for hourly buckets and interpolate.

6. **Fix deprecated `datetime.utcnow()` in tests (M-4):**
   While touching `test_stats.py`, replace all `datetime.utcnow()` calls with `datetime.now(timezone.utc).replace(tzinfo=None)`.

## Integration & Edge Cases

- **Empty ghost list:** If no tasks match the criteria, return `{ "ghosts": [], "total": 0 }` — not a 404.
- **New user with no tasks:** Ghost list returns empty. Weekly summary returns zeros.
- **Index migration on existing DB:** The `CREATE INDEX IF NOT EXISTS` script is idempotent. Include in the migration script and document in the pre-merge checklist.
- **Flow state optimization backward compatibility:** The response shape of `GET /stats/flow-state` must not change. Only the internal calculation method changes.
- **`task_id` column in ActionLog:** Currently conflates task IDs with report/system-state IDs (finding M-5). Ghost list query must handle this — only join where `action_type` relates to task actions.

## Acceptance Criteria (required)

1. `GET /stats/ghost-list` with valid JWT returns 200 with `{ "ghosts": [...], "total": int }`.
2. Ghost tasks have `id`, `name`, `priority`, `daysOpen`, `actionCount`, `lastActionAt`, `ghostReason`.
3. Tasks open > 14 days with < 2 actions are flagged as `ghostReason: "stale"`.
4. Tasks with > 5 edits but still open are flagged as `ghostReason: "wheel-spinning"`.
5. Completed tasks never appear in the ghost list.
6. `GET /stats/weekly-summary` returns 200 with weekly aggregate stats.
7. `PRAGMA index_list(action_logs)` includes `ix_action_logs_user_ts`.
8. `PRAGMA index_list(session_logs)` includes `ix_session_logs_user_ended`.
9. `GET /stats/flow-state` returns the same response shape as before (backward compatible).
10. Flow state query no longer materializes all timestamps in Python (verified by code review).
11. `test_stats.py` has zero `DeprecationWarning` for `datetime.utcnow()`.
12. All existing tests pass with zero regressions.
13. `test_ghost_list.py` adds ≥6 new tests.

## Testing / QA (required)

**New test file:** `code/backend/tests/test_ghost_list.py`

Tests:
- `test_ghost_list_stale_task` — task open 20 days, 1 action → appears with `ghostReason: "stale"`.
- `test_ghost_list_wheel_spinning_task` — task open 15 days, 8 actions, not completed → appears with `ghostReason: "wheel-spinning"`.
- `test_ghost_list_excludes_completed` — completed task, even if old → not in list.
- `test_ghost_list_excludes_recent` — task open 3 days → not in list.
- `test_ghost_list_empty` — no tasks → returns `{ "ghosts": [], "total": 0 }`.
- `test_ghost_list_user_scoping` — ghost tasks belong only to the authenticated user.
- `test_weekly_summary` — seed actions, completed tasks, reports → assert correct counts.
- `test_weekly_summary_empty` — no activity → all zeros.

**Extend:** `code/backend/tests/test_stats.py`
- `test_flow_state_backward_compat` — assert response shape unchanged after optimization.

```bash
cd code/backend && python -m pytest tests/test_ghost_list.py tests/test_stats.py -v
```

**Manual QA checklist:**
1. Create a task, wait (or backdate `date_created`) > 14 days → `GET /stats/ghost-list` → verify it appears.
2. Create a recently active task → verify it does NOT appear.
3. `GET /stats/flow-state` → verify response is identical to pre-optimization.
4. Run `sqlite3 data/dev.db ".indexes action_logs"` → verify `ix_action_logs_user_ts` exists.

## Files touched (repeat for reviewers)

- [code/backend/app/api/stats.py](code/backend/app/api/stats.py)
- [code/backend/app/services/ghost_list_service.py](code/backend/app/services/ghost_list_service.py) (new)
- [code/backend/app/schemas/stats.py](code/backend/app/schemas/stats.py)
- [code/backend/app/models/action_log.py](code/backend/app/models/action_log.py) (index)
- [code/backend/app/models/session_log.py](code/backend/app/models/session_log.py) (index)
- [code/backend/app/services/flow_state.py](code/backend/app/services/flow_state.py) (optimization)
- [code/backend/scripts/migrate_add_indexes.py](code/backend/scripts/migrate_add_indexes.py) (new)
- [code/backend/tests/test_ghost_list.py](code/backend/tests/test_ghost_list.py) (new)
- [code/backend/tests/test_stats.py](code/backend/tests/test_stats.py) (fix deprecations)

## Estimated effort

1–2 dev days

## Concurrency & PR strategy

- **Blocking steps:** `Blocked until: .github/artifacts/phase4/plan/step-2-inference-context-builder.md` (shares ambient data query patterns)
- **Merge Readiness:** false (draft)
- **Branch:** `phase-4/step-5-ghost-list-analytics`
- **Parallelizable with:** Steps 3 and 4 (no dependencies between them). Can be developed concurrently after Step 2 merges.
- Step 7 (Reasoning Sidebar) depends on this step's ghost list endpoint.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `CREATE INDEX` on existing table locks DB | SQLite write lock is brief. Single-user app — no concurrent writers. `CREATE INDEX IF NOT EXISTS` is idempotent. |
| SQL-level flow aggregation is complex in SQLite | SQLite has limited date functions. Use `strftime` for bucketing. If too complex, keep the Python loop but add the composite index for the query. |
| Ghost list thresholds are arbitrary | Make thresholds configurable (`GHOST_STALE_DAYS`, `GHOST_LOW_ACTIVITY`). Good enough for MVP; tune based on real usage. |

**BEFORE MERGE:** Run `scripts/migrate_add_indexes.py` against `dev.db`. Backup first: `cp data/dev.db data/dev.db.pre-indexes.bak`.

## References

- [final-report-3-2.md](../../final-report-3-2.md) — M-1 (action_logs index), M-2 (session_logs index), M-3 (flow calculation optimization), M-4 (deprecated utcnow)
- [PDD.md](../../PDD.md) — Ghost List ("wheel-spinning" visualization)
- [architecture.md](../../architecture.md) — ActionLog schema, Task schema

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
