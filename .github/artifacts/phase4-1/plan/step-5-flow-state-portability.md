# Step 5 — Flow State Portability: Replace SQLite-Specific SQL

## Purpose

Replace SQLite-specific SQL functions (`strftime`, `printf`) in the flow state service with portable SQLAlchemy expressions that work on both SQLite and PostgreSQL. This is required for production portability (the project uses SQLite for dev and PostgreSQL for prod per the tech stack).

## Deliverables

- Refactored `calculate_flow_state()` in `flow_state.py` using portable SQLAlchemy expressions for time-bucketing.
- Tests verifying the flow state calculation produces correct results.

## Primary files to change

- [code/backend/app/services/flow_state.py](code/backend/app/services/flow_state.py) — Replace SQLite-specific SQL
- [code/backend/tests/test_stats.py](code/backend/tests/test_stats.py) — Add/update flow state tests (may need to use the unit test pattern instead of server fixture)

## Detailed implementation steps

### 5.1 Identify the SQLite-specific code

In [code/backend/app/services/flow_state.py](code/backend/app/services/flow_state.py), lines 28–36:

```python
bucket_expr = func.strftime(
    '%Y-%m-%d %H:',
    ActionLog.timestamp,
) + func.printf(
    '%02d',
    (cast(func.strftime('%M', ActionLog.timestamp), Integer) / _BUCKET_MINUTES) * _BUCKET_MINUTES,
)
```

`func.strftime` and `func.printf` are SQLite-specific. PostgreSQL uses `to_char()` and `date_trunc()`.

### 5.2 Strategy: Move bucketing to Python

The simplest cross-DB approach is to fetch the raw timestamps within the window and do the bucketing in Python. Since the window is only 6 hours and this is a single-user app, the number of rows is small (likely < 200 even in heavy use).

Replace the SQL aggregation with:

```python
async def calculate_flow_state(db: AsyncSession, user_id: str) -> FlowStateSchema:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now - timedelta(hours=_WINDOW_HOURS)

    # Fetch raw timestamps — portable, no DB-specific functions
    stmt = (
        select(ActionLog.timestamp)
        .where(ActionLog.user_id == user_id)
        .where(ActionLog.user_id.is_not(None))
        .where(ActionLog.timestamp >= window_start)
        .where(ActionLog.action_type.notin_(AUTH_ACTION_TYPES))
    )
    result = await db.execute(stmt)
    timestamps = [row[0] for row in result.all()]

    if not timestamps:
        return FlowStateSchema(
            flow_percent=0,
            change_percent=0,
            window_label="Last 6 hours",
            series=[],
        )

    # Build the 12 bucket slots
    bucket_starts: list[datetime] = [
        window_start + timedelta(minutes=_BUCKET_MINUTES * i)
        for i in range(_NUM_BUCKETS)
    ]

    # Count actions per bucket in Python
    counts: list[int] = [0] * _NUM_BUCKETS
    for ts in timestamps:
        # Find which bucket this timestamp falls into
        offset_minutes = (ts - window_start).total_seconds() / 60
        bucket_index = int(offset_minutes // _BUCKET_MINUTES)
        if 0 <= bucket_index < _NUM_BUCKETS:
            counts[bucket_index] += 1

    # Rest of the calculation remains identical...
    max_count = max(counts) if max(counts) > 0 else 1
    scores: list[float] = [(c / max_count) * 100.0 for c in counts]

    flow_percent = int(max(0, min(100, _safe_mean(scores[-3:]))))
    preceding_mean = _safe_mean(scores[-6:-3])
    change_percent = int(_safe_mean(scores[-3:])) - int(preceding_mean)

    series = [
        FlowPointSchema(
            time=bucket_starts[i].strftime("%-I:%M %p"),
            activity_score=round(scores[i], 2),
        )
        for i in range(_NUM_BUCKETS)
    ]

    return FlowStateSchema(
        flow_percent=flow_percent,
        change_percent=change_percent,
        window_label="Last 6 hours",
        series=series,
    )
```

### 5.3 Handle platform-specific `strftime` format

Note: `%-I` (no-padding hour) is Linux-specific. On Windows it's `%#I`. Since the project targets Linux (per the env), this is fine, but add a comment:

```python
# NOTE: %-I is POSIX (Linux/macOS). On Windows use %#I.
```

### 5.4 Remove unused imports

After the refactor, `func.strftime`, `func.printf`, `cast`, `literal_column` are no longer needed. Remove them:

```python
# Before
from sqlalchemy import Integer, func, select, cast, literal_column

# After
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
```

Keep `func` only if used elsewhere (it's not in this file after the refactor).

### 5.5 Performance consideration

The Python-side bucketing trades a marginal SQL optimization for full portability. With a 6-hour window and a single user, the maximum rows fetched is bounded (even at 1 action per minute = 360 rows). This is negligible.

If performance becomes a concern later, a dialect-aware approach can be added:

```python
if db.bind.dialect.name == "postgresql":
    # Use date_trunc
elif db.bind.dialect.name == "sqlite":
    # Use strftime
```

But this is over-engineering for now. The Python approach is correct and simple.

### 5.6 Update tests

Add unit tests that directly call `calculate_flow_state()` with a test DB session containing known ActionLog entries, then verify the bucket counts and flow percentages.

## Integration & Edge Cases

- **Empty window:** Already handled — returns zeros.
- **Actions exactly at bucket boundaries:** `offset_minutes // _BUCKET_MINUTES` correctly assigns them to the starting bucket.
- **Actions outside the window:** The SQL WHERE clause filters them; Python bucketing won't encounter them.
- **Timezone handling:** All timestamps are UTC with `tzinfo=None` (SQLite-compatible). No change needed.
- **No persistence change.** No migration needed.

## Acceptance Criteria

1. **AC-1:** `GET /stats/flow-state` returns 200 with correct `flowPercent`, `changePercent`, `windowLabel`, and `series` array.
2. **AC-2:** No SQLite-specific function calls (`strftime`, `printf`) remain in [code/backend/app/services/flow_state.py](code/backend/app/services/flow_state.py).
3. **AC-3:** The SQL query emitted uses only portable operators (`SELECT`, `WHERE`, comparison operators).
4. **AC-4:** Given 3 actions in the last 30-minute bucket and 0 in all others, `flowPercent` is ~33 (100/3 buckets mean of last 3).
5. **AC-5:** Existing flow state behavior is preserved — same output for same input data.
6. **AC-6:** Manual verify: Hit `/stats/flow-state` and inspect the response for correct shapes.

## Testing / QA

### Tests to add

- **File:** [code/backend/tests/test_stats.py](code/backend/tests/test_stats.py) or a new `test_flow_state.py`
  - `test_flow_state_empty_window` — No actions, expect 0 flow percent and empty series.
  - `test_flow_state_single_bucket` — Actions in one bucket, verify correct score distribution.
  - `test_flow_state_even_distribution` — Equal actions across all buckets, verify 100% flow.

### Run commands
```bash
cd code/backend && python -m pytest tests/test_stats.py -v -k "flow"
```

### Manual QA checklist
1. Start backend, create a few tasks/updates to generate actions.
2. Hit `GET /stats/flow-state` — verify 200 with `series` containing 12 data points.
3. Verify `flowPercent` is a reasonable number (not 0 if recent actions exist).

## Files touched

- [code/backend/app/services/flow_state.py](code/backend/app/services/flow_state.py)
- [code/backend/tests/test_stats.py](code/backend/tests/test_stats.py)

## Estimated effort

0.5 dev days

## Concurrency & PR strategy

- **Suggested branch:** `phase-4.1/step-5-flow-state-portability`
- **Blocking steps:** None — independent of Steps 1–4.
- **Merge Readiness:** false (pending implementation)

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Python-side bucketing slower than SQL grouping | Max ~360 rows in 6h window; linear scan negligible |
| Different numerical results due to float rounding | Results are `int()` rounded — behavior preserved |
| `%-I` strftime not portable to Windows | Project targets Linux; added comment noting Windows alternative |

## References

- [MVP Final Audit §4 Backend](../../MVP_FINAL_AUDIT.md) — SQLite-specific SQL in flow state service
- [code/backend/app/services/flow_state.py](code/backend/app/services/flow_state.py)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
