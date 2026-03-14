# Step 3 — Sunday Synthesis Backend

## Purpose

Implement the Sunday Synthesis feature end-to-end on the backend: a new `SynthesisReport` model for storing AI-generated narratives, API endpoints to trigger and retrieve synthesis results, and integration with the OZ client and inference context builder from Steps 1–2.

## Deliverables

- `models/synthesis.py` — `SynthesisReport` SQLAlchemy model (stores narrative, theme, commitment score, suggested tasks, OZ run metadata)
- `schemas/synthesis.py` — Pydantic schemas for synthesis create/response
- `services/synthesis_service.py` — orchestrates context building → prompt construction → OZ submission → result parsing → storage
- `api/ai.py` — new router with `POST /ai/synthesis`, `GET /ai/synthesis/latest`, `GET /ai/synthesis/{id}`
- Backend tests covering the full synthesis pipeline (with mocked OZ responses)

## Primary files to change (required)

- [code/backend/app/models/synthesis.py](code/backend/app/models/synthesis.py) (new)
- [code/backend/app/schemas/synthesis.py](code/backend/app/schemas/synthesis.py) (new)
- [code/backend/app/services/synthesis_service.py](code/backend/app/services/synthesis_service.py) (new)
- [code/backend/app/api/ai.py](code/backend/app/api/ai.py) (new)
- [code/backend/app/main.py](code/backend/app/main.py) (register ai router)
- [code/backend/app/db/base.py](code/backend/app/db/base.py) (import new model for `create_all`)
- [code/backend/tests/test_ai.py](code/backend/tests/test_ai.py) (new)

## Detailed implementation steps

1. **Create `models/synthesis.py`:**
   ```python
   class SynthesisReport(TimestampedBase):
       __tablename__ = "synthesis_reports"
       
       id: Mapped[int] = mapped_column(primary_key=True)
       user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
       summary: Mapped[str] = mapped_column(Text, nullable=False)        # 1-paragraph narrative
       theme: Mapped[str] = mapped_column(String(200), nullable=False)   # e.g., "Heavy Backend Focus"
       commitment_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-10
       suggested_tasks: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array of task suggestions
       oz_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # OZ run ID for audit
       status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | completed | failed
       raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)  # Full OZ response for debugging
       period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
       period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
   ```

2. **Create `schemas/synthesis.py`:**
   ```python
   class SynthesisCreate(CamelModel):
       """Trigger a new synthesis. No body required — uses last 7 days."""
       period_days: int = 7  # optional override for lookback period
   
   class SuggestedTask(CamelModel):
       name: str
       priority: str  # Low | Medium | High
       rationale: str  # why the AI suggests this task
       is_low_friction: bool = False  # True for re-entry mode suggestions
   
   class SynthesisResponse(CamelModel):
       id: int
       summary: str
       theme: str
       commitment_score: int
       suggested_tasks: list[SuggestedTask]
       status: str
       period_start: datetime
       period_end: datetime
       created_at: datetime
   
   class SynthesisStatusResponse(CamelModel):
       id: int
       status: str  # pending | completed | failed
       oz_run_id: str | None
   ```

3. **Create `services/synthesis_service.py`:**
   ```python
   class SynthesisService:
       async def trigger_synthesis(self, user_id: int, db: AsyncSession, period_days: int = 7) -> SynthesisReport:
           """Full pipeline: check rate limit → gather context → build prompt → submit to OZ → parse → store."""
           # 0. Enforce weekly synthesis cap BEFORE any DB writes or OZ call.
           #    Raises HTTPException(429) if the weekly limit (default: 3) is reached.
           #    Import: from app.services.ai_rate_limiter import AIRateLimiter
           await AIRateLimiter().check_limit(user_id, endpoint="synthesis", db=db)
           # 1. Build inference context
           context = await InferenceContextBuilder().build(user_id, db)
           # 2. Build prompt
           prompt = PromptBuilder().build_synthesis_prompt(context.model_dump(by_alias=True))
           # 3. Create pending SynthesisReport row
           report = SynthesisReport(user_id=user_id, status="pending", ...)
           db.add(report)
           await db.commit()
           # 4. Submit to OZ
           try:
               result = await OZClient().run_prompt(prompt, title=f"Sunday Synthesis {date.today()}")
               # 5. Parse OZ response (expects JSON with summary, theme, commitmentScore)
               parsed = self._parse_oz_response(result)
               report.summary = parsed["summary"]
               report.theme = parsed["theme"]
               report.commitment_score = parsed["commitmentScore"]
               report.suggested_tasks = json.dumps(parsed.get("suggestedTasks", []))
               report.status = "completed"
               report.oz_run_id = result.get("run_id")
               report.raw_response = json.dumps(result)
               # 6. Record usage AFTER a successful real OZ call (not for failed or mocked runs).
               await AIRateLimiter().record_usage(
                   user_id, endpoint="synthesis", oz_run_id=result.get("run_id"),
                   prompt_chars=len(prompt), was_mocked=False, db=db
               )
           except Exception as e:
               report.status = "failed"
               report.summary = f"Synthesis failed: {str(e)}"
               report.theme = "Error"
               report.commitment_score = 0
               logger.error(f"Synthesis failed for user {user_id}: {e}")
           await db.commit()
           return report
       
       def _parse_oz_response(self, result: dict) -> dict:
           """Extract structured JSON from OZ agent response text."""
           # OZ returns session transcript. Parse the last JSON block from the agent output.
           # Defensive: use regex to find JSON in response, validate with Pydantic.
       
       async def get_latest(self, user_id: int, db: AsyncSession) -> SynthesisReport | None:
           """Get the most recent completed synthesis for a user."""
       
       async def get_by_id(self, synthesis_id: int, user_id: int, db: AsyncSession) -> SynthesisReport | None:
           """Get a specific synthesis report, scoped to user."""
   ```

4. **Create `api/ai.py` router:**
   ```python
   router = APIRouter(prefix="/ai", tags=["ai"])
   
   @router.post("/synthesis", status_code=202)
   async def trigger_synthesis(
       body: SynthesisCreate = SynthesisCreate(),
       current_user = Depends(get_current_user),
       db = Depends(get_db)
   ):
       """Trigger a new Sunday Synthesis. Returns 202 with synthesis ID.
       The synthesis runs synchronously (blocking) but returns quickly 
       if OZ is responsive (~30-60s). For long runs, frontend can poll status.
       
       Raises 429 if the user has exceeded their weekly synthesis limit
       (default: 3/week, set via OZ_MAX_SYNTHESIS_PER_WEEK in .env)."""
       # Check AI_ENABLED
       if not settings.ai_enabled:
           raise HTTPException(503, "AI features are disabled")
       # Rate limit is checked inside SynthesisService.trigger_synthesis()
       report = await SynthesisService().trigger_synthesis(current_user.id, db, body.period_days)
       return {"id": report.id, "status": report.status}
   
   @router.get("/synthesis/latest")
   async def get_latest_synthesis(
       current_user = Depends(get_current_user),
       db = Depends(get_db)
   ):
       """Get the most recent completed synthesis."""
       report = await SynthesisService().get_latest(current_user.id, db)
       if not report:
           raise HTTPException(404, "No synthesis reports found")
       return SynthesisResponse.model_validate(report, from_attributes=True)
   
   @router.get("/synthesis/{synthesis_id}")
   async def get_synthesis(
       synthesis_id: int,
       current_user = Depends(get_current_user),
       db = Depends(get_db)
   ):
       """Get a specific synthesis report."""
       report = await SynthesisService().get_by_id(synthesis_id, current_user.id, db)
       if not report:
           raise HTTPException(404, "Synthesis report not found")
       return SynthesisResponse.model_validate(report, from_attributes=True)
   ```

5. **Register router in `main.py`:**
   - `from app.api.ai import router as ai_router`
   - `app.include_router(ai_router)`

6. **Update `db/base.py`:**
   - Add `from app.models.synthesis import SynthesisReport` to ensure `create_all` picks up the new table.

## Integration & Edge Cases

- **Synchronous vs Async execution:** For MVP, the synthesis endpoint blocks while waiting for OZ (up to `oz_max_wait_seconds`). This is acceptable for a single-user app. Future enhancement: return 202 immediately and let frontend poll `GET /ai/synthesis/{id}` for status updates.
- **OZ response parsing:** The OZ agent produces a session transcript, not raw JSON. The `_parse_oz_response` method must extract the JSON payload from the agent's text output. Strategy: instruct the prompt to output **only** a JSON block, then regex-extract the first `{...}` from the response.
- **Graceful degradation:** If OZ fails, the `SynthesisReport` is stored with `status="failed"` and an error summary. The endpoint still returns 202 — it doesn't 500.
- **Persistence:** New table `synthesis_reports` via `create_all`. Pre-merge: backup `dev.db`.
- **ActionLog middleware:** `POST /ai/synthesis` will be captured by the ActionLog middleware. This is desirable — it records when the user triggered a synthesis.
- **Rate limit order of operations (cost):** The `AIRateLimiter.check_limit()` call is the very first thing in `SynthesisService.trigger_synthesis()` — before any DB writes, before context building, before the OZ call. This ensures no credits are consumed when the weekly cap is already reached. The `record_usage()` call only happens after a real (non-mocked) OZ run succeeds. Failed runs and mock-mode runs are NOT recorded against the cap.

## Acceptance Criteria (required)

1. `POST /ai/synthesis` with valid JWT returns 202 with `{ "id": <int>, "status": "pending" | "completed" }`.
2. `POST /ai/synthesis` without JWT returns 401.
3. `POST /ai/synthesis` with `AI_ENABLED=false` returns 503.
4. `POST /ai/synthesis` when the weekly synthesis limit is exhausted returns 429 with a message containing the reset date.
5. `GET /ai/synthesis/latest` returns 200 with the most recent completed synthesis including `summary`, `theme`, `commitmentScore`, `suggestedTasks`.
6. `GET /ai/synthesis/latest` with no prior synthesis returns 404.
7. `GET /ai/synthesis/{id}` returns the specific report scoped to the authenticated user.
8. `GET /ai/synthesis/{id}` for another user's report returns 404 (not 403 — information hiding).
9. `SynthesisReport` rows are persisted in the database with `user_id`, `oz_run_id`, and timestamps.
10. When OZ returns an error, `status="failed"` is stored and the endpoint does not raise 500.
11. A failed synthesis run does NOT count against the weekly rate limit.
12. `suggested_tasks` field contains a JSON array of task objects with `name`, `priority`, `rationale`.
13. All existing tests pass with zero regressions.
14. `test_ai.py` adds ≥9 new tests.

## Testing / QA (required)

**New test file:** `code/backend/tests/test_ai.py`

Tests to add (synthesis-specific; this file will be extended in Step 4):
- `test_trigger_synthesis_success` — mock OZ response with valid JSON → assert 202 and `status=completed`.
- `test_trigger_synthesis_unauthorized` — no JWT → assert 401.
- `test_trigger_synthesis_ai_disabled` — `AI_ENABLED=false` → assert 503.
- `test_trigger_synthesis_rate_limited` — insert 3 `ai_usage_logs` rows for `endpoint="synthesis"` in the current week → assert 429 with reset date in response. Assert `OZClient.run_prompt` was **never called** (patch it and assert zero invocations).
- `test_trigger_synthesis_failed_run_not_counted` — mock OZ timeout → assert `status=failed` stored, endpoint returns 202, AND `ai_usage_logs` table has NO new entry (failed runs don't count).
- `test_get_latest_synthesis` — create a synthesis → `GET /ai/synthesis/latest` → assert 200 with correct fields.
- `test_get_latest_synthesis_none` — no prior synthesis → assert 404.
- `test_get_synthesis_by_id` — create synthesis → get by ID → assert 200.
- `test_get_synthesis_user_scoping` — create synthesis for user A → request as user B → assert 404.

Mock strategy: Patch `OZClient.run_prompt` to return a predefined JSON response. **Always assert that `OZClient.run_prompt` was not called** in tests that exercise the 429 or short-circuit paths — this verifies no credits were consumed.

```bash
cd code/backend && python -m pytest tests/test_ai.py -v
```

**Manual QA checklist:**
1. Start backend with valid `OZ_API_KEY` → `POST /ai/synthesis` → verify OZ run is created.
2. Wait for completion → `GET /ai/synthesis/latest` → inspect narrative, theme, score.
3. Check `synthesis_reports` table in SQLite → verify row exists with all fields.
4. Start backend with `AI_ENABLED=false` → `POST /ai/synthesis` → verify 503.

## Files touched (repeat for reviewers)

- [code/backend/app/models/synthesis.py](code/backend/app/models/synthesis.py) (new)
- [code/backend/app/schemas/synthesis.py](code/backend/app/schemas/synthesis.py) (new)
- [code/backend/app/services/synthesis_service.py](code/backend/app/services/synthesis_service.py) (new)
- [code/backend/app/api/ai.py](code/backend/app/api/ai.py) (new)
- [code/backend/app/main.py](code/backend/app/main.py) (router registration)
- [code/backend/app/db/base.py](code/backend/app/db/base.py) (model import)
- [code/backend/tests/test_ai.py](code/backend/tests/test_ai.py) (new)

## Estimated effort

2–3 dev days

## Concurrency & PR strategy

- **Blocking steps:**
  - `Blocked until: .github/artifacts/phase4/plan/step-1-oz-integration-layer.md` (OZClient, PromptBuilder)
  - `Blocked until: .github/artifacts/phase4/plan/step-2-inference-context-builder.md` (InferenceContextBuilder)
- **Merge Readiness:** false (draft)
- **Branch:** `phase-4/step-3-sunday-synthesis`
- Step 6 (Synthesis UI) depends on this step's endpoints.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| OZ response format is unpredictable (free-text, not always JSON) | Prompt explicitly requests JSON-only output. Parser uses regex to extract first JSON block. Fallback: store raw response with `status=failed` and error message. |
| Blocking endpoint ties up the worker for 30–60s | Single-user app — only one synthesis at a time. Add `oz_max_wait_seconds` timeout to prevent indefinite blocking. |
| New table requires migration on existing DBs | `create_all` handles new table creation. No column additions to existing tables. Pre-merge backup required. |

**BEFORE MERGE:** `cp data/dev.db data/dev.db.pre-phase4.bak`

## References

- [agents.md](../../agents.md) — Prompt A (Sunday Synthesis / The Narrator)
- [PDD.md](../../PDD.md) — §4.3 Sunday Synthesis, §3.4 Sunday Synthesis feature
- [step-1-oz-integration-layer.md](./step-1-oz-integration-layer.md) — OZClient, PromptBuilder
- [step-2-inference-context-builder.md](./step-2-inference-context-builder.md) — InferenceContextBuilder, InferenceContext

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
