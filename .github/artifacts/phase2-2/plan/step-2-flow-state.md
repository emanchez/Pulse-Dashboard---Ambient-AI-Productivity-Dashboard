# Step 2 — Flow State Endpoint

## Purpose

Add a `GET /stats/flow-state` endpoint that queries the last 6 hours of `ActionLog` entries for the authenticated user, buckets them into 12 × 30-minute slots, and returns a normalised flow score (0–100%) plus a time-series array for the Recharts `AreaChart` in `ProductivityPulseCard`.

## Deliverables

- `code/backend/app/schemas/flow_state.py` — `FlowPointSchema` + `FlowStateSchema` Pydantic schemas
- `code/backend/app/services/flow_state.py` — bucketing + scoring service logic
- `code/backend/app/api/stats.py` — new `GET /stats/flow-state` route added to existing stats router
- New tests: `code/backend/tests/test_stats.py` additions (or a new `test_flow_state.py`)

## Primary files to change (required)

- [code/backend/app/schemas/flow_state.py](../../../../code/backend/app/schemas/flow_state.py) *(new)*
- [code/backend/app/services/flow_state.py](../../../../code/backend/app/services/flow_state.py) *(new)*
- [code/backend/app/api/stats.py](../../../../code/backend/app/api/stats.py)
- [code/backend/tests/test_stats.py](../../../../code/backend/tests/test_stats.py)

## Detailed implementation steps

1. **Create `code/backend/app/schemas/flow_state.py`**:
   ```python
   class FlowPointSchema(CamelModel):
       time: str           # e.g. "10:00 AM"
       activity_score: float   # 0.0 – 100.0

   class FlowStateSchema(CamelModel):
       flow_percent: int       # weighted avg of last 3 buckets, 0-100
       change_percent: int     # diff vs preceding 3 buckets (can be negative)
       window_label: str       # e.g. "Last 6 hours"
       series: list[FlowPointSchema]
   ```

2. **Create `code/backend/app/services/flow_state.py`** — `calculate_flow_state(db, user_id) -> FlowStateSchema`:
   - Compute `now = datetime.utcnow()` and `window_start = now - timedelta(hours=6)`.
   - Query: `SELECT timestamp FROM action_logs WHERE user_id = :user_id AND timestamp >= :window_start ORDER BY timestamp ASC`.
   - Build 12 empty buckets covering `window_start` to `now` in 30-minute steps; each bucket label is the slot start time formatted as `"%-I:%M %p"` (e.g. `"10:00 AM"`).
   - For each `ActionLog` timestamp, determine its bucket index: `idx = int((ts - window_start).total_seconds() // 1800)`, clamp to `[0, 11]`, increment bucket counter.
   - Normalise: `max_count = max(bucket counts, default=1)`; `activity_score = (count / max_count) * 100` per bucket.
   - `flow_percent = int(mean of last 3 bucket scores)`, clamped to `[0, 100]`.
   - `change_percent = int(mean of last 3 scores) - int(mean of preceding 3 scores)`.
   - When no action logs exist: return safe default `FlowStateSchema(flow_percent=0, change_percent=0, window_label="Last 6 hours", series=[])`.

3. **Add route to `code/backend/app/api/stats.py`**:
   ```python
   @router.get("/flow-state", response_model=FlowStateSchema)
   async def get_flow_state(
       user_id: str = Depends(get_current_user),
       db: AsyncSession = Depends(get_db),
   ) -> FlowStateSchema:
       return await calculate_flow_state(db, user_id)
   ```

4. **Add tests** — see Testing / QA section.

## Integration & Edge Cases

- **No logs:** Returns `FlowStateSchema` with `flowPercent=0`, `changePercent=0`, `series=[]` — never raises an exception. Frontend must handle empty `series` array gracefully (Recharts renders nothing without data).
- **Single log in window:** One bucket has count=1, all others 0. `flowPercent` will be low. This is correct behaviour.
- **All logs in same bucket:** `max_count > 1` normalisation handles this — that bucket scores 100, all others 0.
- **`action_logs` has no `user_id` for older rows:** If `user_id` is `NULL` for legacy rows, they will not be counted for any user — expected behaviour. No migration needed.
- **Timezone:** All timestamps stored as UTC; bucket labels formatted without timezone context — frontend displays them as local wall-clock using `time` string directly (no conversion needed for area chart labels).
- **Performance:** Query is bounded to the last 6 hours with a `WHERE timestamp >= :window_start` filter. Add a DB index on `(user_id, timestamp)` if not already present — see Risks.

## Acceptance Criteria

1. `GET /stats/flow-state` with a valid JWT returns `200` with body matching:
   ```json
   {
     "flowPercent": <integer 0-100>,
     "changePercent": <integer>,
     "windowLabel": "Last 6 hours",
     "series": [{"time": "<string>", "activityScore": <float>}]
   }
   ```
2. With zero `ActionLog` rows for the user, `GET /stats/flow-state` returns `200` with `flowPercent: 0`, `changePercent: 0`, and `series: []`.
3. After inserting 5 `ActionLog` rows for the user within the last 30 minutes, `flowPercent > 0`.
4. `GET /stats/flow-state` without a JWT returns `401`.
5. `GET /stats/pulse` (existing endpoint) still returns `200` with correct schema after this change (regression).
6. `series` array length is ≤ 12 (one per 30-minute bucket in a 6-hour window).

## Testing / QA

### Automated tests — additions to `code/backend/tests/test_stats.py`

```python
def test_flow_state_empty(client, auth_headers):
    r = client.get("/stats/flow-state", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["flowPercent"] == 0
    assert data["changePercent"] == 0
    assert data["windowLabel"] == "Last 6 hours"
    assert data["series"] == []

def test_flow_state_with_logs(client, auth_headers, db_session, test_user_id):
    # Insert 3 ActionLog rows within the last 15 minutes
    from datetime import datetime, timedelta
    from app.models.action_log import ActionLog
    for _ in range(3):
        db_session.add(ActionLog(user_id=test_user_id, action_type="task_update",
                                 timestamp=datetime.utcnow() - timedelta(minutes=5)))
    db_session.commit()
    r = client.get("/stats/flow-state", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["flowPercent"] > 0
    assert len(r.json()["series"]) <= 12

def test_flow_state_no_auth(client):
    r = client.get("/stats/flow-state")
    assert r.status_code == 401

def test_pulse_still_works(client, auth_headers):
    r = client.get("/stats/pulse", headers=auth_headers)
    assert r.status_code == 200
    assert "silenceState" in r.json()
```

**Run command:**

```bash
cd code/backend
pytest tests/test_stats.py -v
```

### Manual QA checklist

1. Start backend: `uvicorn app.main:app --reload`
2. `POST /login` → copy token
3. `GET /stats/flow-state` with no prior activity → expect `{"flowPercent":0,"changePercent":0,"windowLabel":"Last 6 hours","series":[]}`
4. Perform a task update (via `PUT /tasks/{id}`) to generate an `ActionLog` entry
5. `GET /stats/flow-state` again → `series` should have at least one `activityScore > 0`
6. Verify `GET /stats/pulse` still returns correct `silenceState`

## Files touched

- [code/backend/app/schemas/flow_state.py](../../../../code/backend/app/schemas/flow_state.py) *(new)*
- [code/backend/app/services/flow_state.py](../../../../code/backend/app/services/flow_state.py) *(new)*
- [code/backend/app/api/stats.py](../../../../code/backend/app/api/stats.py)
- [code/backend/tests/test_stats.py](../../../../code/backend/tests/test_stats.py)

## Estimated effort

0.5–1 dev day

## Concurrency & PR strategy

- **Blocking steps:** None — independent of Step 1; can be developed and merged in parallel.
- **Merge Readiness: false** *(flip to `true` when all Acceptance Criteria pass and tests are green)*
- Suggested branch: `phase-2-2/step-2-flow-state`

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `action_logs` table grows large; 6-hour query becomes slow | Add composite index `CREATE INDEX ix_action_logs_user_ts ON action_logs(user_id, timestamp)` in the migration or a standalone Alembic script |
| `user_id` is NULL on old ActionLog rows (middleware best-effort) | Filter `WHERE user_id IS NOT NULL AND user_id = :user_id` — NULL rows are silently excluded |
| `mean()` call on empty list raises `StatisticsError` | Guard: `statistics.mean(lst) if lst else 0` |
| Bucket label formatting differs across Python versions | Use `strftime("%-I:%M %p")` on Linux; add a format helper with a fallback for Windows dev environments |

## References

- [PDD.md — §4.1 Silence Gap Analysis](../PDD.md)
- [code/backend/app/models/action_log.py](../../../../code/backend/app/models/action_log.py)
- [code/backend/app/api/stats.py](../../../../code/backend/app/api/stats.py)
- [code/backend/app/schemas/stats.py](../../../../code/backend/app/schemas/stats.py) *(pattern reference)*
- [master.md](./master.md)

## Author Checklist

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/` (happy path + validation)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected
