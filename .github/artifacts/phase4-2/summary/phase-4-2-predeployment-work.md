# Phase 4.2 — Pre-Deployment Work Summary

**Date:** 2026-03-22
**Branch:** `phase-4-2/predeployment-oz-cleanup`

---

## Scope

Prepare the codebase for OZ (Warp cloud agent platform) deployment by:
1. Purging all remaining Ollama references from active context/documentation files.
2. Updating the `dashboard-assistant` SKILL.md to align with OZ's Skill-as-Agent model.
3. Verifying backend and frontend readiness for OZ agent integration.

---

## What Was Done

### 1. Ollama Reference Removal (8 files, 20+ edits)

All active (non-archive) documentation and context files were updated to replace Ollama references with OZ:

| File | Changes |
|------|---------|
| `.github/artifacts/copilot-instructions.md` | Updated AI/LLM stack line, "No External AI APIs" → "OZ-Only Inference" rule, removed "Ollama/OZ" dual reference |
| `.github/artifacts/PDD.md` | Updated tech stack table, rewrote ADR-001, updated 3 inference references, updated Phase 4 roadmap line |
| `.github/artifacts/agents.md` | Rewrote §1 "Inference Engine" section (model, platform, context window), updated code comment, updated 2 production security recommendations |
| `.github/artifacts/architecture.md` | Updated `/ai/synthesize` endpoint description |
| `.github/artifacts/product.md` | Updated Phase 4 roadmap line |
| `.github/artifacts/project-summary.md` | Updated elevator pitch, tech stack, implementation status, key decisions, open issues, next steps, closing summary (7 edits total) |
| `.github/artifacts/MVP_FINAL_AUDIT.md` | Clarified Ollama-clean status line |
| `.agents/skills/dashboard-assistant/SKILL.md` | Updated Constraints section: "local Ollama instance" → "OZ (Warp) cloud agent platform" |

**Archive files were not touched** per project policy.

### 2. SKILL.md — OZ Agent Definition

The `dashboard-assistant` skill at `.agents/skills/dashboard-assistant/SKILL.md` was created and refined to serve as the canonical instruction set for the OZ agent. It includes:

- **YAML frontmatter** with `name` and `description` (required by Oz Skill format)
- **5-step analysis pipeline:** Silence Gap Analysis → Report Density Check → Commitment Score → Weekly Narrative → Task Recommendations
- **Structured JSON output format** matching the existing `SynthesisResponse` schema
- **Privacy constraints:** user_id scoping, no cross-user data, rate limits
- **Context budget:** 8,000 character hard cap with truncation rules

### 3. OZ API Alignment — Code Changes (5 files)

After cross-referencing the codebase against the [Oz REST API reference](https://docs.warp.dev/reference/api-and-sdk/agent) and the [official Python SDK](https://github.com/warpdotdev/oz-sdk-python), several gaps were identified and fixed:

#### 3a. `app/core/config.py` — New OZ settings

Added two new settings required for cloud agent runs:

| Setting | Default | Purpose |
|---------|---------|---------|
| `OZ_ENVIRONMENT_ID` | `""` | UID of the Oz cloud environment (Docker image + GitHub repos) |
| `OZ_SKILL_SPEC` | `""` | Skill spec in `owner/repo:skill_name` format → references SKILL.md |

`validate_oz_config()` now warns at startup when `OZ_ENVIRONMENT_ID` or `OZ_SKILL_SPEC` are missing and a real API key is configured.

#### 3b. `app/services/oz_client.py` — Full API alignment

| Change | Before | After |
|--------|--------|-------|
| Endpoint | `POST /agent/run` | `POST /agent/runs` (preferred per docs) |
| Request body | `{prompt, config: {model_id}}` | `{prompt, skill, config: {model_id, environment_id, name}, title}` |
| Response field | `id` / `status` | `run_id` / `state` (with `status` backcompat shim) |
| State handling | Only `SUCCEEDED`, `FAILED`, `CANCELLED`, `ERROR` | Full Oz state enum including `BLOCKED` with actionable error messages |
| Error detail | Generic `"ended with status"` | Extracts `status_message.message` from API response |
| Config builder | Inline dict | `_build_run_body()` method — composable and testable |
| `skill` param | Not sent | Top-level `skill` field (takes precedence over `config.skill_spec` per docs) |
| Mock response | `{status, id, result}` | `{state, status, run_id, result}` (matches real API shape) |

#### 3c. `scripts/setup_oz.py` — Extended setup

Now prompts for three values (previously only API key):
1. `OZ_API_KEY` — personal API key
2. `OZ_ENVIRONMENT_ID` — cloud environment UID
3. `OZ_SKILL_SPEC` — skill spec string

Uses idempotent `_upsert_env()` helper, includes doc links for API reference, Skills guide, and Python SDK.

#### 3d. `.env.prod.example` — New settings documented

Added `OZ_ENVIRONMENT_ID` and `OZ_SKILL_SPEC` entries with setup instructions.

#### 3e. Tests updated

- `tests/test_oz_client.py` — Updated mock response shapes (`state` vs `status`, `run_id` vs `id`), added `oz_environment_id` and `oz_skill_spec` to mocked settings, added 2 new config default tests. All 34 tests pass.
- `tests/fixtures/mock_oz_synthesis.json` — Updated to use `state`/`run_id` field names matching real Oz API.
- `tests/test_ai.py` — All 23 tests pass with no modifications (mock mode untouched).

### 4. Frontend Readiness Assessment

The frontend is **fully isolated from the OZ layer** — it only talks to the backend's `/ai/*` endpoints. Zero OZ-specific code exists in the frontend. As long as the backend continues serving the same `SynthesisResponse` / `TaskSuggestionResponse` / `CoPlanResponse` shapes, the frontend will work with any LLM backend.

**No frontend code changes were needed.**

---

## OZ Deployment Checklist (Remaining Steps)

Based on the [Oz Skills-as-Agents documentation](https://docs.warp.dev/agent-platform/cloud-agents/skills-as-agents):

- [ ] **Register the skill** in the Oz web app at `oz.warp.dev`:
  - Repository: `emanchez/Pulse-Dashboard---Ambient-AI-Producti...`
  - Skill name: `dashboard-assistant`
  - Instructions: paste from `.agents/skills/dashboard-assistant/SKILL.md`
- [ ] **Configure an Environment** in Oz that points to this GitHub repo
- [ ] **Set `OZ_API_KEY`** in `code/backend/.env` (run `python scripts/setup_oz.py`)
- [ ] **Test locally** with mock mode: `AI_ENABLED=true`, `OZ_API_KEY=""` (returns fixture data)
- [ ] **Test with real OZ**: set a real API key and trigger `/ai/synthesis`
- [ ] **Optional: Set up a schedule** for weekly synthesis (`oz schedule create --cron "0 10 * * 0"`)

---

## Files Changed

### Documentation (8 files)
- `.github/artifacts/copilot-instructions.md`
- `.github/artifacts/PDD.md`
- `.github/artifacts/agents.md`
- `.github/artifacts/architecture.md`
- `.github/artifacts/product.md`
- `.github/artifacts/project-summary.md`
- `.github/artifacts/MVP_FINAL_AUDIT.md`
- `.agents/skills/dashboard-assistant/SKILL.md`

### Backend Source (3 files)
- `code/backend/app/core/config.py` — Added `oz_environment_id`, `oz_skill_spec` settings + config warnings
- `code/backend/app/services/oz_client.py` — Full Oz API alignment (endpoint, request body, response handling)
- `code/backend/scripts/setup_oz.py` — Extended to configure environment ID and skill spec

### Config Templates (1 file)
- `code/backend/.env.prod.example` — Added `OZ_ENVIRONMENT_ID`, `OZ_SKILL_SPEC`

### Tests (2 files)
- `code/backend/tests/test_oz_client.py` — Updated mock shapes, added new config tests
- `code/backend/tests/fixtures/mock_oz_synthesis.json` — Updated to match Oz API field names

---

## Verification

```bash
# Confirm zero Ollama references in source code
grep -r "ollama\|Ollama\|OLLAMA" code/
# Expected: 0 results

# Confirm remaining Ollama refs are only in archive/ or prohibition rules
grep -rn "ollama\|Ollama\|OLLAMA" .github/artifacts/ --include="*.md" | grep -v "archive/"
# Expected: only contextual mentions (ADR supersession, SDK prohibition, audit status)

# Run OZ client tests (34 tests)
cd code/backend && python -m pytest tests/test_oz_client.py -v
# Expected: 34 passed

# Run AI endpoint tests (23 tests)
python -m pytest tests/test_ai.py -v
# Expected: 23 passed
```

---

## Design Decisions

### Keep httpx instead of adopting `oz-sdk-python`
The official Warp SDK (`pip install oz-agent-sdk`) was evaluated but not adopted because:
- The current `OZClient` already has circuit breaker, mock mode, prompt guard — patterns that would need to be reimplemented around the SDK
- The SDK adds a dependency to track; the raw `httpx` usage is simple and fully aligned with the API now
- **Recommendation:** Adopt the SDK in a future phase if we need SDK features (retries, typed response models, streaming)

### Top-level `skill` vs `config.skill_spec`
Per Oz docs, the top-level `skill` field takes precedence over `config.skill_spec`. We use the top-level field for clarity and to avoid any ambiguity.

### Backward-compatible `status` shim in `get_run_status()`
The Oz API returns `state` but existing callers (and tests like the polling mock sequences) checked for `status`. The `get_run_status()` method now copies `state` → `status` for backward compatibility, allowing a gradual migration.

---

## Commit Message

```
feat: align OZ client with Warp Agent API, add environment/skill config

Documentation cleanup:
- Replace all active Ollama references with OZ across 8 docs (archive/ untouched)
- Update SKILL.md constraints to reference OZ platform

OZ API alignment:
- Switch OZClient to POST /agent/runs (preferred endpoint per Oz docs)
- Send skill spec, environment_id, and config name in run requests
- Handle full Oz state enum (QUEUED→SUCCEEDED + BLOCKED, ERROR)
- Extract status_message details on failures for actionable errors
- Add _build_run_body() for composable request construction

Configuration:
- Add OZ_ENVIRONMENT_ID setting (cloud environment UID)
- Add OZ_SKILL_SPEC setting (owner/repo:skill_name format)
- Startup warnings when environment/skill not configured with real API key
- Update setup_oz.py to prompt for all three Oz settings
- Update .env.prod.example with new settings

Tests:
- Update mock response shapes to match Oz API (state/run_id vs status/id)
- Add config default tests for new settings
- All 57 tests pass (34 oz_client + 23 ai)

Resolves: Phase 4.2 pre-deployment OZ readiness
```
