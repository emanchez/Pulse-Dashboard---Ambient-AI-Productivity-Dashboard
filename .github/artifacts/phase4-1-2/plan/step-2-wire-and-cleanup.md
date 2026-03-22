# Step 2 — Wire Services & Remove OZ References

**Phase:** 4.1.2  
**Branch:** `phase-4/step-2-wire-and-cleanup`

---

## Purpose

Wire the two AI service consumers (`synthesis_service.py`, `ai_service.py`) to use the new `LLMClient` from step 1. Then perform a full sweep of all active source code and documentation to replace "OZ" terminology with provider-agnostic "LLM" / "agent" language. Delete `oz_client.py` and its test file. Leave one clearly marked note explaining the Oz migration history.

---

## Deliverables

- `synthesis_service.py` and `ai_service.py` import `LLMClient`, not `OZClient`
- `oz_client.py` deleted
- `tests/test_oz_client.py` deleted; all coverage preserved in `tests/test_llm_client.py`
- `tests/fixtures/mock_oz_synthesis.json` deleted (replaced by `mock_llm_synthesis.json` from step 1)
- `scripts/setup_oz.py` deleted
- All active documentation and context files updated (no raw "OZ" branding in `code/` or active `.github/artifacts/`)
- `copilot-instructions.md` updated to reflect generic LLM usage

---

## Primary files to change

| File | Change |
|------|--------|
| `code/backend/app/services/synthesis_service.py` | Import `LLMClient`; swap instantiation; update `record_usage(llm_run_id=...)` call; store `result.get("provider")` instead of `result.get("id")` |
| `code/backend/app/services/ai_service.py` | Import `LLMClient`; swap instantiation; update `record_usage(llm_run_id=...)` calls; store `result.get("provider")` instead of `result.get("run_id")` |
| `code/backend/app/api/ai.py` | Update OZ error type imports to `llm_client` |
| `code/backend/app/models/synthesis.py` | Rename `oz_run_id` attr → `llm_run_id` |
| `code/backend/app/models/ai_usage.py` | Rename `oz_run_id` attr → `llm_run_id` |
| `code/backend/app/services/oz_client.py` | **Delete** |
| `code/backend/scripts/setup_oz.py` | **Delete** |
| `code/backend/scripts/migrate_oz_run_id.py` | **Create** — Alembic-free migration script |
| `code/backend/tests/test_oz_client.py` | **Delete** |
| `code/backend/tests/fixtures/mock_oz_synthesis.json` | **Delete** |
| `code/backend/tests/fixtures/mock_oz_suggestions.json` | **Delete** |
| `code/backend/tests/fixtures/mock_oz_coplan.json` | **Delete** |
| `.github/artifacts/phase4-1-2/plan/*.md` | Already generic — confirm |
| `.github/artifacts/copilot-instructions.md` | Remove OZ SDK references; update LLM section |
| `.github/artifacts/architecture.md` | Replace "OZ" with "LLM client" where relevant |
| `.github/artifacts/agents.md` | Replace "OZ" with "LLM" platform references |
| `.github/artifacts/PDD.md` | Replace "OZ" with "LLM" platform references |
| `.github/artifacts/product.md` | Replace "OZ" with "LLM" platform references |

---

## Detailed Implementation Steps

### 1. Wire `synthesis_service.py`

```python
# Before
from app.services.oz_client import OZClient
...
client = OZClient(settings)

# After
from app.services.llm_client import LLMClient
...
client = LLMClient(settings)
```

Also update the `run_prompt` result handling — `LLMClient` does not return `id`/`run_id`:

```python
# Before
report.oz_run_id = result.get("id") or result.get("run_id")

# After
report.llm_run_id = result.get("provider")   # stores "anthropic" | "groq" | "mock"
```

Update the `record_usage` call (parameter renamed in step 1):

```python
# Before
await self._rate_limiter.record_usage(
    oz_run_id=result.get("id") or result.get("run_id"), ...
)
# After
await self._rate_limiter.record_usage(
    llm_run_id=result.get("provider"), ...
)
```

### 2. Wire `ai_service.py`

Same import swap as above. Also update the two `record_usage` calls in `suggest_tasks()` and `co_plan()`:

```python
# Before (in both methods)
oz_run_id=result.get("id") or result.get("run_id"),

# After
llm_run_id=result.get("provider"),
```

No other `OZClient`-specific attributes are used.

### 3. Rename `oz_run_id` in ORM models

In `app/models/synthesis.py` and `app/models/ai_usage.py`, rename the mapped attribute:

```python
# Before
oz_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

# After
llm_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

The column name in the DB also needs updating — see step 4b (migration script).

### 4. Update `api/ai.py` error handling

Replace the import:

```python
# Before
from ..services.oz_client import CircuitBreakerOpen, ServiceDisabledError

# After
from ..services.llm_client import CircuitBreakerOpen, ServiceDisabledError
```

Also rename `_OZ_EXCEPTION_MAP` → `_LLM_EXCEPTION_MAP` for consistency.

### 4b. Create DB migration script `scripts/migrate_oz_run_id.py`

This renames `oz_run_id` → `llm_run_id` on both affected tables. SQLite supports `RENAME COLUMN` since 3.26. Use the existing migration script pattern from `scripts/migrate_add_indexes.py`:

```python
"""Migrate oz_run_id → llm_run_id on synthesis_reports and ai_usage_logs.

Safe to re-run (checks column existence before altering).
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "dev.db")

def migrate(db_path: str) -> None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    for table in ("synthesis_reports", "ai_usage_logs"):
        cols = {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}
        if "oz_run_id" in cols and "llm_run_id" not in cols:
            cur.execute(f"ALTER TABLE {table} RENAME COLUMN oz_run_id TO llm_run_id")
            print(f"  Renamed oz_run_id → llm_run_id on {table}")
        else:
            print(f"  {table}: no migration needed")

    con.commit()
    con.close()

if __name__ == "__main__":
    migrate(DB_PATH)
    print("Migration complete.")
```

Run before starting the server post-merge:
```bash
cd code/backend
python scripts/migrate_oz_run_id.py
```

### 5. Delete obsolete files

```bash
rm code/backend/app/services/oz_client.py
rm code/backend/scripts/setup_oz.py
rm code/backend/tests/test_oz_client.py
rm code/backend/tests/fixtures/mock_oz_synthesis.json
rm code/backend/tests/fixtures/mock_oz_suggestions.json
rm code/backend/tests/fixtures/mock_oz_coplan.json
```

### 6. Grep sweep — source code

Run and resolve each hit:
```bash
grep -rin "oz_api_key\|oz_model_id\|oz_environment_id\|oz_skill_spec\|OZClient\|oz_client\|oz_max_wait\|oz_max_synthesis\|oz_max_suggestions\|oz_max_coplan\|oz_run_id" code/ \
  | grep -v "__pycache__" | grep -v ".bak"
```

Expected: 0 results after this step.

### 7. Documentation sweep — active artifacts

Files to update (search-and-replace "OZ" branding):

**`.github/artifacts/copilot-instructions.md`**
- Section: `AI/LLM:` — change `OZ (Warp cloud agent platform) via dashboard-assistant Skill` → `LLM provider (Anthropic Claude or Groq) via LLMClient`
- Section: `OZ-Only Inference` critical rule — update to describe `LLMClient` abstraction
- Remove `oz_environment_id`, `oz_skill_spec` from any example code
- Add migration note (see step 7)

**`.github/artifacts/architecture.md`**
- Replace "Warp OZ" / "OZ agent" references in inference/AI sections with "LLMClient"
- Update ENV var table: remove OZ_* rows, add LLM_* rows

**`.github/artifacts/agents.md`**
- Replace platform-name "OZ" with "LLM backend" or "inference provider"
- Prompt structures and reasoning logic remain unchanged

**`.github/artifacts/PDD.md`**
- Replace "OZ" in technology stack and ADR sections
- Update rationale: "LLM provider selected via LLM_PROVIDER env var (Anthropic or Groq)"

**`.github/artifacts/product.md`**
- Update tech stack line for AI/LLM

### 8. Add migration note (one location only)

Add to the top of `.github/artifacts/copilot-instructions.md` in the `AI/LLM:` stack section or as a note block:

> **Note (Phase 4.1.2):** This project previously planned to use OZ (Warp cloud agent platform) as its inference backend but did not receive beta access. All AI inference now runs directly through `LLMClient` (`anthropic` or `groq` SDK), configurable via `LLM_PROVIDER`.

Do not add this note to source code files — it belongs only in the architecture/context docs.

### 9. Final verification grep

```bash
# Should return 0 matches in non-archived, non-pycache files
grep -rin "\boz\b" code/ .github/artifacts/ \
  | grep -iv "archive\|__pycache__\|\.bak\|\.git\|phase4-1-2.*migration.note"
```

---

## Integration & Edge Cases

- `synthesis_service.py` calls `json.loads(result["result"])` on the return value. Verify `LLMClient.run_prompt()` wraps response text under `"result"` key (defined in step 1). ✓
- **`oz_run_id` → `llm_run_id` in models**: Both `SynthesisReport` and `AIUsageLog` have an `oz_run_id` column. The ORM attributes are renamed to `llm_run_id` and the DB column renamed via `scripts/migrate_oz_run_id.py`. Run the migration script before starting the server.
- **`result.get("provider")` as the new run identifier**: `LLMClient` returns `{"result": text, "provider": "anthropic"|"groq"|"mock"}`. Services should store `result.get("provider")` in the `llm_run_id` field for audit purposes (acceptable; 100 char limit is satisfied).
- If any test in `test_ai.py` or `test_synthesis.py` patches `oz_client.OZClient`, update the patch target to `llm_client.LLMClient`.
- `make dev` and `make start` commands should not reference `setup_oz.py`; update Makefile if needed.
- After the DB migration runs, `PRAGMA table_info(synthesis_reports)` and `PRAGMA table_info(ai_usage_logs)` should show `llm_run_id` and no `oz_run_id`.

---

## Acceptance Criteria

1. `grep -r "OZClient\|oz_client\|oz_api_key\|oz_max_synthesis\|oz_max_suggestions\|oz_max_coplan\|oz_run_id" code/` returns 0 results (excluding `__pycache__` and `.bak`).
2. `pytest tests/ -v` — all tests pass (no `test_oz_client.py` file present).
3. `POST /ai/synthesis` with mock mode returns a completed synthesis (no 500 errors).
4. `code/backend/app/services/oz_client.py` does not exist in the repository.
5. `code/backend/scripts/setup_oz.py` does not exist in the repository.
6. All three `mock_oz_*.json` fixture files do not exist.
7. `PRAGMA table_info(synthesis_reports)` shows `llm_run_id` column (no `oz_run_id`).
8. `PRAGMA table_info(ai_usage_logs)` shows `llm_run_id` column (no `oz_run_id`).
9. All active `.github/artifacts/` docs replaced "OZ" branding with LLM/agent language.
10. The migration note (step 8) appears in `copilot-instructions.md`.

---

## Testing / QA

**Automated:**
```bash
cd code/backend
pytest tests/ -v
# Expected: all tests pass; test_oz_client.py absent
```

**Regression check:**
```bash
pytest tests/test_ai.py tests/test_synthesis.py -v
```

**Manual verification:**
1. Start backend: `make dev`
2. `curl -s http://localhost:8000/health` → `{"status": "ok"}`
3. Obtain JWT: `POST /login`
4. `POST /ai/synthesis` → wait for response → confirm `status: "completed"` and `synthesis_text` is non-empty
5. Confirm no OZ-related errors in `logs/`

---

## Files touched

**Modified:**
- `code/backend/app/services/synthesis_service.py`
- `code/backend/app/services/ai_service.py`
- `code/backend/app/api/ai.py`
- `code/backend/app/models/synthesis.py` (`oz_run_id` → `llm_run_id`)
- `code/backend/app/models/ai_usage.py` (`oz_run_id` → `llm_run_id`)
- `.github/artifacts/copilot-instructions.md`
- `.github/artifacts/architecture.md`
- `.github/artifacts/agents.md`
- `.github/artifacts/PDD.md`
- `.github/artifacts/product.md`

**Created:**
- `code/backend/scripts/migrate_oz_run_id.py` — renames `oz_run_id` column on both tables

**Deleted:**
- `code/backend/app/services/oz_client.py`
- `code/backend/scripts/setup_oz.py`
- `code/backend/tests/test_oz_client.py`
- `code/backend/tests/fixtures/mock_oz_synthesis.json`
- `code/backend/tests/fixtures/mock_oz_suggestions.json`
- `code/backend/tests/fixtures/mock_oz_coplan.json`

---

## Estimated effort

~1.5–2 hours (wiring is trivial; doc sweep is the bulk of the work)

---

## Concurrency & PR strategy

**Blocking steps:** Blocked until `phase-4/step-1-llm-client` is merged.  
**Merge Readiness:** false (pending step 1 merge)  
**Branch:** `phase-4/step-2-wire-and-cleanup`  
**Depends-On:** `phase-4/step-1-llm-client`

Include `Depends-On: phase-4/step-1-llm-client` in the PR description and add a `depends` label.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Missed OZ reference in a test patch target | Run grep (step 6) before PR review |
| `ai.py` catches `OZSpecificError` not defined in new client | Import `CircuitBreakerOpen`/`ServiceDisabledError` from `llm_client` directly |
| Doc sweep misses a nested section | Use case-insensitive grep across all non-archive artifacts |
| Makefile references `setup_oz.py` | Check `Makefile` targets before deleting script |
| DB migration breaks existing rows | `migrate_oz_run_id.py` uses `PRAGMA table_info` guard — safe to re-run; take `.bak` first |
| SQLite version < 3.26 doesn't support `RENAME COLUMN` | Check `SELECT sqlite_version()` — Ubuntu 20.04+ ships ≥ 3.31. Fall back to table-rebuild pattern if < 3.26. |
| `report.oz_run_id` / `entry.oz_run_id` attribute access after ORM rename | Both service files update references as part of this step; `get_errors()` should show 0 Pylance errors after changes |

---

## References

- [master.md](./master.md)
- [step-1-llm-client.md](./step-1-llm-client.md)
- [code/backend/app/services/synthesis_service.py](../../../../code/backend/app/services/synthesis_service.py)
- [code/backend/app/services/ai_service.py](../../../../code/backend/app/services/ai_service.py)
- [.github/artifacts/copilot-instructions.md](../../copilot-instructions.md)
- [PLANNING.md](../../PLANNING.md)

---

## Author Checklist

- [x] Purpose clearly stated
- [x] All deliverables listed
- [x] Primary files (changed and deleted) identified
- [x] Acceptance criteria are numbered and testable
- [x] Testing/QA includes automated + manual steps
- [x] Blocking steps and Merge Readiness declared
- [x] Risks documented
- [x] Migration note placement defined (one location, copilot-instructions.md)
