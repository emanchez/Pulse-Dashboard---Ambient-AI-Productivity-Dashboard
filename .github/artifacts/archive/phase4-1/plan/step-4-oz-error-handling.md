# Step 4 — OZ Error Handling: Map Exceptions to HTTP Codes & Sanitize AI Error Messages

## Purpose

Address three related OZ/AI service issues:

1. **Custom OZ exceptions are not translated to HTTP errors** — `ServiceDisabledError`, `CircuitBreakerOpen`, `TimeoutError`, and `ValueError` from the OZ client propagate as raw 500s with internal stack traces.
2. **AI error messages leak internal exception text** — `str(e)` is passed directly to `rationale` fields in API responses, exposing internal details.
3. **Greedy JSON extraction regex** — `re.search(r"\{[\s\S]*\}", raw)` matches from the first `{` to the last `}`, potentially including invalid JSON when the response contains multiple JSON-like blocks.

## Deliverables

- Exception-to-HTTP mapping in the AI API route layer (or service layer) that converts OZ exceptions to proper 429/503/422 responses.
- Sanitized error messages in all `rationale` and `conflict_description` fields — no raw `str(e)`.
- Non-greedy, bracket-balanced JSON extraction replacing the greedy regex.
- Tests for each exception mapping and the JSON extraction fix.

## Primary files to change

- [code/backend/app/services/ai_service.py](code/backend/app/services/ai_service.py) — Sanitize error messages, improve JSON parsing
- [code/backend/app/services/oz_client.py](code/backend/app/services/oz_client.py) — Annotate exceptions for mapping (no changes needed if mapping is done in ai_service/api layer)
- [code/backend/app/api/ai.py](code/backend/app/api/ai.py) — Add exception handlers that map OZ exceptions to HTTP status codes
- [code/backend/tests/test_ai.py](code/backend/tests/test_ai.py) — Test exception mapping and sanitized responses
- [code/backend/tests/test_oz_client.py](code/backend/tests/test_oz_client.py) — Test JSON extraction edge cases

## Detailed implementation steps

### 4.1 Define exception-to-HTTP mapping

Create a mapping in [code/backend/app/api/ai.py](code/backend/app/api/ai.py) or a shared utility:

```python
from app.services.oz_client import ServiceDisabledError, CircuitBreakerOpen

_OZ_EXCEPTION_MAP = {
    ServiceDisabledError: (503, "AI features are currently disabled."),
    CircuitBreakerOpen: (503, "AI service temporarily unavailable. Please try again later."),
    TimeoutError: (504, "AI request timed out. Please try again."),
    ValueError: (422, "Invalid AI response format."),
    RuntimeError: (502, "AI service returned an error."),
}
```

### 4.2 Add a helper to translate exceptions in route handlers

In [code/backend/app/api/ai.py](code/backend/app/api/ai.py), wrap each AI service call:

```python
def _handle_ai_exception(exc: Exception) -> HTTPException:
    """Convert OZ/AI exceptions to structured HTTP errors."""
    for exc_type, (status_code, message) in _OZ_EXCEPTION_MAP.items():
        if isinstance(exc, exc_type):
            logger.warning("AI exception mapped to %d: %s — %s", status_code, type(exc).__name__, str(exc))
            raise HTTPException(status_code=status_code, detail=message)
    # Unknown exception — log full details, return generic 500
    logger.error("Unexpected AI exception: %s", exc, exc_info=True)
    raise HTTPException(status_code=500, detail="An unexpected error occurred with the AI service.")
```

Update the route handlers to catch and translate:

```python
@router.post("/suggest")
async def suggest_tasks(...):
    try:
        return await ai_service.suggest_tasks(user_id, db, focus_area)
    except HTTPException:
        raise  # Already structured (e.g., 429 from rate limiter)
    except Exception as exc:
        _handle_ai_exception(exc)
```

### 4.3 Sanitize error messages in AIService

In [code/backend/app/services/ai_service.py](code/backend/app/services/ai_service.py), the `suggest_tasks` and `co_plan` methods currently return `str(e)` in user-facing fields:

**suggest_tasks:**
```python
except Exception as e:
    ...
    return TaskSuggestionResponse(
        suggestions=[],
        rationale=f"Unable to generate suggestions: {str(e)}",  # ← LEAKS
    )
```

Replace with generic messages:

```python
except HTTPException:
    raise
except Exception as e:
    logger.error("Task suggestion failed for user %s: %s", user_id, e, exc_info=True)
    raise  # Let the route handler catch and map to HTTP
```

**Alternative (if graceful degradation is preferred over error):** Return a generic message without `str(e)`:

```python
return TaskSuggestionResponse(
    suggestions=[],
    rationale="Unable to generate suggestions. Please try again later.",
)
```

The same pattern applies to `co_plan`:
```python
return CoPlanResponse(
    has_conflict=False,
    conflict_description="Analysis temporarily unavailable. Please try again later.",
    resolution_question=None,
    suggested_priority=None,
)
```

**Decision:** Use graceful degradation (return empty/generic response) for non-critical failures, and raise exceptions for critical ones (disabled, circuit breaker). The route handler catches anything that escapes.

### 4.4 Fix greedy JSON extraction regex

In [code/backend/app/services/ai_service.py](code/backend/app/services/ai_service.py), the `_parse_coplan_response` method uses:

```python
match = re.search(r"\{[\s\S]*\}", raw)
```

This is greedy and will match from the **first** `{` to the **last** `}` in the entire string, potentially gobbling invalid JSON. Replace with a bracket-balanced extractor:

```python
def _extract_json_object(self, raw: str) -> dict | None:
    """Extract the first valid JSON object from a string.
    
    Uses bracket-depth tracking instead of greedy regex to avoid
    matching across multiple JSON blocks.
    """
    start = raw.find("{")
    if start == -1:
        return None
    
    depth = 0
    in_string = False
    escape_next = False
    
    for i in range(start, len(raw)):
        c = raw[i]
        if escape_next:
            escape_next = False
            continue
        if c == "\\":
            escape_next = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(raw[start:i + 1])
                except (json.JSONDecodeError, ValueError):
                    # This block wasn't valid JSON; try finding next {
                    next_start = raw.find("{", i + 1)
                    if next_start == -1:
                        return None
                    return self._extract_json_object(raw[next_start:])
    return None
```

Similarly fix the array extraction in `_parse_suggestion_response`:

```python
def _extract_json_array(self, raw: str) -> list | None:
    """Extract the first valid JSON array from a string."""
    start = raw.find("[")
    if start == -1:
        return None
    
    depth = 0
    in_string = False
    escape_next = False
    
    for i in range(start, len(raw)):
        c = raw[i]
        if escape_next:
            escape_next = False
            continue
        if c == "\\":
            escape_next = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(raw[start:i + 1])
                except (json.JSONDecodeError, ValueError):
                    next_start = raw.find("[", i + 1)
                    if next_start == -1:
                        return None
                    return self._extract_json_array(raw[next_start:])
    return None
```

Replace the regex fallback in `_parse_suggestion_response`:
```python
# Old:
match = re.search(r"\[[\s\S]*\]", raw)

# New:
arr = self._extract_json_array(raw)
if arr is not None:
    return arr
```

And in `_parse_coplan_response`:
```python
# Old:
match = re.search(r"\{[\s\S]*\}", raw)

# New:
obj = self._extract_json_object(raw)
if obj is not None:
    return obj
```

### 4.5 Add tests

Add edge-case tests for the JSON extraction and exception mapping.

## Integration & Edge Cases

- **Rate limiter 429s:** The rate limiter already raises `HTTPException(429)`. The `except HTTPException: raise` pattern preserves this. Verify no double-wrapping.
- **Mock mode errors:** In mock mode, OZ client loads fixtures and shouldn't raise. But if the fixture file is missing and the inline fallback is used, it could have parsing issues. Test this path.
- **Nested JSON in LLM responses:** LLM output may contain markdown code blocks with JSON inside. The bracket-balanced parser correctly finds the first complete JSON object/array, even if markdown wraps it.

## Acceptance Criteria

1. **AC-1:** When `AI_ENABLED=false`, `POST /ai/suggest` returns 503 with `{"detail": "AI features are currently disabled."}`.
2. **AC-2:** When the circuit breaker is open, `POST /ai/suggest` returns 503 with `{"detail": "AI service temporarily unavailable..."}`.
3. **AC-3:** When OZ times out, `POST /ai/suggest` returns 504 with `{"detail": "AI request timed out..."}`.
4. **AC-4:** No API response contains raw Python exception text (no `str(e)` in any user-visible field).
5. **AC-5:** Given raw text `'Some text {"a":1} more {"b":2}'`, `_extract_json_object` returns `{"a": 1}` (first valid object, not greedy match).
6. **AC-6:** Given raw text `'prefix [1,2,3] suffix [4,5]'`, `_extract_json_array` returns `[1, 2, 3]`.
7. **AC-7:** Existing AI tests continue to pass.

## Testing / QA

### Tests to add

- **File:** [code/backend/tests/test_ai.py](code/backend/tests/test_ai.py)
  - `test_suggest_returns_503_when_disabled` — Set `AI_ENABLED=false`, call suggest, expect 503.
  - `test_suggest_error_message_sanitized` — Mock OZ to raise, verify response doesn't contain exception text.
  
- **File:** [code/backend/tests/test_oz_client.py](code/backend/tests/test_oz_client.py)
  - `test_extract_json_object_non_greedy` — Multiple JSON blocks, verify first is returned.
  - `test_extract_json_array_non_greedy` — Multiple JSON arrays, verify first is returned.
  - `test_extract_json_handles_nested_braces` — Nested `{}`s, verify correct extraction.
  - `test_extract_json_handles_strings_with_braces` — JSON values containing `{` in strings.

### Run commands
```bash
cd code/backend && python -m pytest tests/test_ai.py tests/test_oz_client.py -v
```

### Manual QA checklist
1. Set `AI_ENABLED=false` in `.env`, restart backend.
2. Call `POST /ai/suggest` — verify 503 response with clean message.
3. Set `AI_ENABLED=true`, `OZ_API_KEY=""` (mock mode).
4. Call `POST /ai/suggest` — verify mock response works normally.

## Files touched

- [code/backend/app/services/ai_service.py](code/backend/app/services/ai_service.py)
- [code/backend/app/api/ai.py](code/backend/app/api/ai.py)
- [code/backend/tests/test_ai.py](code/backend/tests/test_ai.py)
- [code/backend/tests/test_oz_client.py](code/backend/tests/test_oz_client.py)

## Estimated effort

1 dev day

## Concurrency & PR strategy

- **Suggested branch:** `phase-4.1/step-4-oz-error-handling`
- **Blocking steps:** `Blocked until: .github/artifacts/phase4-1/plan/step-3-backend-hardening.md` (needs cached `get_settings()`)
- **Merge Readiness:** false (pending implementation)

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Bracket-balanced parser slower than regex | Max ~8000 chars (oz_max_context_chars); linear scan is fast enough |
| Graceful degradation hides real errors | All exceptions logged at ERROR level with full stack trace; only user-facing message is sanitized |
| New exception mapping breaks existing error handling | `except HTTPException: raise` preserves existing 429s from rate limiter |

## References

- [MVP Final Audit §4 Backend](../../MVP_FINAL_AUDIT.md) — OZ exceptions, greedy regex, error leaking
- [MVP Final Audit §3.2](../../MVP_FINAL_AUDIT.md) — Avoid leaking internal exception text
- [code/backend/app/services/ai_service.py](code/backend/app/services/ai_service.py)
- [code/backend/app/services/oz_client.py](code/backend/app/services/oz_client.py)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
