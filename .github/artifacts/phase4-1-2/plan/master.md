# Phase 4.1.2 — General LLM Access Layer (OZ Replacement)

> **Note:** This phase replaces the OZ (Warp cloud agent) integration. The project originally planned to use OZ as its inference backend but did not receive beta access. All inference is now routed through a direct LLM provider (Anthropic Claude or Groq) via a generic `LLMClient` abstraction. All "OZ" terminology in source code and active documentation is replaced with provider-agnostic "LLM" / "agent" language.

---

## Scope

Replace the `OZClient` and all OZ-specific configuration with a provider-agnostic `LLMClient` that supports:
- **Anthropic Claude** (primary — pay-per-use, best quality)
- **Groq** (secondary — free tier, open-source models)

Switchable via a single `LLM_PROVIDER` environment variable. Mock mode (empty API key) is preserved for dev/test. All OZ-specific ENV vars (`OZ_API_KEY`, `OZ_MODEL_ID`, etc.) are migrated to generic equivalents (`LLM_API_KEY`, `LLM_MODEL_ID`). All references to "OZ" are updated to "LLM" or "agent" in source code and active docs.

---

## Phase-level Deliverables

- `code/backend/app/services/llm_client.py` — new provider-agnostic LLM client (replaces `oz_client.py`)
- `code/backend/app/core/config.py` — OZ settings migrated to generic LLM settings (including rate-limit cap fields)
- `code/backend/app/services/ai_rate_limiter.py` — updated to use renamed config fields and `llm_run_id` param
- `code/backend/app/services/synthesis_service.py` — wired to `LLMClient`
- `code/backend/app/services/ai_service.py` — wired to `LLMClient`
- `code/backend/app/models/synthesis.py` — `oz_run_id` attr renamed to `llm_run_id`
- `code/backend/app/models/ai_usage.py` — `oz_run_id` attr renamed to `llm_run_id`
- `code/backend/scripts/setup_llm.py` — replaces `setup_oz.py`
- `code/backend/scripts/migrate_oz_run_id.py` — renames DB columns on two tables
- `code/backend/.env.prod.example` — updated with new env var names
- All active documentation/context files updated (OZ → LLM/agent terminology)
- All tests updated and passing

---

## Steps (ordered)

1. Step 1 — [step-1-llm-client.md](./step-1-llm-client.md)  
   Build the `LLMClient` abstraction and migrate `config.py` settings.

2. Step 2 — [step-2-wire-and-cleanup.md](./step-2-wire-and-cleanup.md)  
   Wire services and replace all OZ references in code and docs.

## Merge Order

Sequential — step 2 is blocked on step 1 (imports `LLMClient`).

1. `.github/artifacts/phase4-1-2/plan/step-1-llm-client.md` — branch: `phase-4/step-1-llm-client`
2. `.github/artifacts/phase4-1-2/plan/step-2-wire-and-cleanup.md` — branch: `phase-4/step-2-wire-and-cleanup`

---

## Phase Acceptance Criteria

1. `POST /ai/synthesis` returns 202 with a synthesis report in dev (mock mode, no API key).
2. `POST /ai/synthesis` returns a real AI-generated report when `LLM_API_KEY` is set and `LLM_PROVIDER=anthropic`.
3. Switching `LLM_PROVIDER=groq` produces a valid synthesis without code changes.
4. No string `"oz"` (case-insensitive) appears in `code/` source files except inside comments explicitly noting the historical migration. DB column names (`oz_run_id`) are renamed to `llm_run_id` via migration script.
5. All 57+ backend tests pass.
6. `python scripts/setup_llm.py` writes `LLM_API_KEY` and `LLM_PROVIDER` to `.env` correctly.
7. `PRAGMA table_info(synthesis_reports)` and `PRAGMA table_info(ai_usage_logs)` show `llm_run_id` column (no `oz_run_id`).

---

## Concurrency groups & PR strategy

- Steps must merge in order (step 2 imports from step 1).
- Each step is a focused PR with no unrelated changes.
- Branch naming: `phase-4/step-1-llm-client`, `phase-4/step-2-wire-and-cleanup`.

---

## Verification Plan

```bash
# 1. Unit tests
cd code/backend
pytest tests/test_llm_client.py -v       # New LLMClient tests
pytest tests/test_ai.py -v               # AI endpoint integration

# 2. Smoke test — mock mode (no API key)
curl -s -X POST http://localhost:8000/ai/synthesis \
  -H "Authorization: Bearer <token>" | jq .status
# Expected: "pending" → poll → "completed"

# 3. Grep check — no raw OZ references in source
grep -rin "oz_api_key\|OZClient\|oz_client\|oz_model_id\|oz_environment_id\|oz_skill_spec\|oz_run_id\|oz_max_synthesis\|oz_max_suggestions\|oz_max_coplan" code/ \
  | grep -v "__pycache__" | grep -v ".bak"
# Expected: 0 results

# 4. DB migration verification
cd code/backend
python scripts/migrate_oz_run_id.py
sqlite3 data/dev.db "PRAGMA table_info(synthesis_reports);" | grep -E "oz_run_id|llm_run_id"
sqlite3 data/dev.db "PRAGMA table_info(ai_usage_logs);" | grep -E "oz_run_id|llm_run_id"
# Expected: llm_run_id present, oz_run_id absent
```

---

## Risks, Rollbacks & Migration Notes

- **`.env` key rename is a breaking change:** `OZ_API_KEY` → `LLM_API_KEY`, and all `OZ_MAX_*` → `LLM_MAX_*`. Existing `.env` files must be updated manually or via `setup_llm.py`. Document clearly.
- **Rate-limit cap env vars renamed:** `OZ_MAX_SYNTHESIS_PER_WEEK` → `LLM_MAX_SYNTHESIS_PER_WEEK`, etc. If the old vars exist in `.env`, they will be ignored and defaults will apply. Check `.env` after running `setup_llm.py`.
- **DB schema change — `oz_run_id` column rename:** Run `python scripts/migrate_oz_run_id.py` before starting the server post-merge. Take a `.bak` of `dev.db` first (`cp data/dev.db data/dev.db.pre-phase4-1-2.bak`). Script is idempotent. No new columns are added; no data is lost.
- **No additional DB schema changes** — no Alembic required.
- **Provider quality difference:** Groq (Llama) produces lower-quality synthesis than Claude. Acceptable for dev/cost-sensitive use; Claude recommended for regular use.
- **Rollback:** `oz_client.py` should be preserved in git history until step 2 is fully verified. The DB rename is reversible by running the same script with columns swapped.

---

## References

- [step-1-llm-client.md](./step-1-llm-client.md)
- [step-2-wire-and-cleanup.md](./step-2-wire-and-cleanup.md)
- [code/backend/app/services/oz_client.py](../../../../code/backend/app/services/oz_client.py) — file being replaced
- [code/backend/app/core/config.py](../../../../code/backend/app/core/config.py)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Groq Python SDK](https://github.com/groq/groq-python)
- [PLANNING.md](../../PLANNING.md)

---

## Author Checklist (master)

- [x] All step files created and linked
- [x] Phase-level acceptance criteria are measurable
- [x] PR/merge order documented
