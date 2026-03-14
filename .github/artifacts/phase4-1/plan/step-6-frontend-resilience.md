# Step 6 — Frontend Resilience: Promise.allSettled, 401 Detection, isReEntryMode, Deduplicate Types

## Purpose

Address four frontend resilience and correctness issues from the audit:

1. **`TasksPage` uses `Promise.all`** — a single API failure (e.g. flow-state timeout) crashes the entire dashboard load.
2. **Fragile 401 detection** — `err.message.includes("401")` is brittle; should use structured error handling.
3. **`isReEntryMode` is never set from API response** — the feature is inert despite backend support.
4. **Duplicate type definitions** — `api.ts` re-exports types from `generated/` but also has inline type aliases that can drift.

## Deliverables

- `Promise.all` replaced with `Promise.allSettled` in `TasksPage` with graceful per-result fallbacks.
- Structured 401 detection via HTTP status code (not string matching).
- `isReEntryMode` wired through from the task suggestion API response.
- Duplicate type re-exports cleaned up in `api.ts`.

## Primary files to change

- [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx) — Promise.allSettled + 401 fix
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts) — Structured error class, deduplicate types
- [code/frontend/components/dashboard/ReasoningSidebar.tsx](code/frontend/components/dashboard/ReasoningSidebar.tsx) — Wire `isReEntryMode` (if suggestion response is displayed here)
- [code/frontend/app/reports/page.tsx](code/frontend/app/reports/page.tsx) — Apply same Promise.allSettled pattern if affected
- [code/frontend/app/synthesis/page.tsx](code/frontend/app/synthesis/page.tsx) — Apply same pattern if affected

## Detailed implementation steps

### 6.1 Create a structured API error class

In [code/frontend/lib/api.ts](code/frontend/lib/api.ts), replace the generic `Error` throw with a structured class:

```typescript
export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(`Request failed ${status}: ${body}`);
    this.status = status;
    this.body = body;
    this.name = "ApiError";
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }
}
```

Update the `request()` function:

```typescript
async function request(path: string, opts: RequestInit = {}) {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "omit",
    ...opts,
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text);
  }
  if (res.status === 204) return undefined;
  return res.json();
}
```

### 6.2 Replace all `err.message.includes("401")` with structured check

In [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx) and any other pages:

```typescript
// Before
if (err?.message?.includes("401")) logout()

// After
import { ApiError } from "../../lib/api"

if (err instanceof ApiError && err.isUnauthorized) logout()
```

Search for all occurrences of `.includes("401")` across the frontend and replace them.

### 6.3 Replace `Promise.all` with `Promise.allSettled`

In `TasksPage.fetchAll()`:

```typescript
const fetchAll = async () => {
  try {
    const results = await Promise.allSettled([
      getFlowState(token),
      getActiveSession(token),
      listTasks(token),
    ]);

    // Process each result independently
    if (results[0].status === "fulfilled") {
      setFlowState(results[0].value);
    } else {
      console.warn("Flow state fetch failed:", results[0].reason);
      if (results[0].reason instanceof ApiError && results[0].reason.isUnauthorized) {
        logout();
        return;
      }
    }

    if (results[1].status === "fulfilled") {
      setActiveSession(results[1].value);
    } else {
      console.warn("Active session fetch failed:", results[1].reason);
      if (results[1].reason instanceof ApiError && results[1].reason.isUnauthorized) {
        logout();
        return;
      }
    }

    if (results[2].status === "fulfilled") {
      setTasks(results[2].value);
    } else {
      console.warn("Tasks fetch failed:", results[2].reason);
      if (results[2].reason instanceof ApiError && results[2].reason.isUnauthorized) {
        logout();
        return;
      }
    }
  } finally {
    setLoading(false);
  }
};
```

Consider extracting a helper to reduce repetition:

```typescript
function handleSettled<T>(
  result: PromiseSettledResult<T>,
  setter: (val: T) => void,
  label: string,
  onUnauthorized: () => void,
): boolean {
  if (result.status === "fulfilled") {
    setter(result.value);
    return true;
  }
  console.warn(`${label} fetch failed:`, result.reason);
  if (result.reason instanceof ApiError && result.reason.isUnauthorized) {
    onUnauthorized();
    return false;
  }
  return true; // non-auth error — continue
}
```

### 6.4 Wire `isReEntryMode` from API response

Check the task suggestion response type in the generated types. The backend returns:

```json
{
  "suggestions": [...],
  "isReEntryMode": true,
  "rationale": "..."
}
```

Verify the generated `TaskSuggestionResponse` type includes `isReEntryMode`. Then in whatever component displays task suggestions (likely `ReasoningSidebar.tsx`), use the field to conditionally render a "Re-entry Mode" indicator:

```tsx
{response.isReEntryMode && (
  <div className="bg-sky-500/20 text-sky-400 text-xs px-3 py-1 rounded-lg">
    Re-entry Mode — Low-friction tasks suggested
  </div>
)}
```

### 6.5 Deduplicate type re-exports in `api.ts`

Currently [code/frontend/lib/api.ts](code/frontend/lib/api.ts) re-exports types from `./generated` with aliases:

```typescript
import type { TaskSchema as Task, ... } from "./generated";
export type { Task, TaskCreate, ... };
```

This is fine as long as it's the single source of truth. The risk is when `api.ts` also defines its own types. Audit the file for any inline type definitions that duplicate generated types and remove them. Keep only the re-exports.

Also ensure the `PulseStats` re-export from `./generated/pulseClient` is consistent (line 3 of api.ts).

### 6.6 Apply same patterns to other pages

Check [code/frontend/app/reports/page.tsx](code/frontend/app/reports/page.tsx) and [code/frontend/app/synthesis/page.tsx](code/frontend/app/synthesis/page.tsx) for the same `Promise.all` and `includes("401")` patterns. Apply the same fixes.

## Integration & Edge Cases

- **`ApiError` and non-API errors:** Network failures (e.g. `TypeError: Failed to fetch`) won't be `ApiError` instances. The `instanceof` check handles this — non-API errors won't trigger logout.
- **`Promise.allSettled` typing:** Each result is `PromiseSettledResult<T>` with discriminated union. TypeScript strict mode will require narrowing.
- **`isReEntryMode` default:** If the field is missing from the response (older backend), default to `false`.
- **Generated types re-export chain:** After deduplication, components should import from `@/lib/api` (the canonical re-export point), not directly from `@/lib/generated`.

## Acceptance Criteria

1. **AC-1:** If the `/stats/flow-state` endpoint is down, the tasks page still loads (tasks and session display correctly; flow state shows fallback).
2. **AC-2:** A 401 response from any API call triggers logout (no string matching).
3. **AC-3:** A network error (backend fully down) does not trigger logout — shows error state instead.
4. **AC-4:** The `ApiError` class exposes `status` and `isUnauthorized` properties.
5. **AC-5:** No occurrences of `.includes("401")` remain in the frontend codebase.
6. **AC-6:** When the task suggestion response includes `isReEntryMode: true`, a visual indicator is rendered.
7. **AC-7:** No duplicate type definitions exist in `api.ts` vs `generated/`.
8. **AC-8:** `npm run build` succeeds with no type errors (pre-strict; strict mode is Step 7).

## Testing / QA

### Manual QA checklist
1. Stop the backend, navigate to `/tasks` in the frontend — verify partial load (should show loading states, not a blank page or crash).
2. Start backend, log in, navigate to `/tasks` — verify all data loads normally.
3. Expire the JWT (wait 8 hours or modify expiry), navigate to `/tasks` — verify redirect to `/login`.
4. Open browser devtools network tab, create a task suggestion request — verify the response includes `isReEntryMode` field.
5. Search codebase for `.includes("401")` — verify zero results.
6. Search codebase for `Promise.all` (not `Promise.allSettled`) in page components — verify zero results.

### Automated
```bash
cd code/frontend && npx tsc --noEmit
cd code/frontend && npm run build
```

## Files touched

- [code/frontend/lib/api.ts](code/frontend/lib/api.ts)
- [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx)
- [code/frontend/app/reports/page.tsx](code/frontend/app/reports/page.tsx)
- [code/frontend/app/synthesis/page.tsx](code/frontend/app/synthesis/page.tsx)
- [code/frontend/components/dashboard/ReasoningSidebar.tsx](code/frontend/components/dashboard/ReasoningSidebar.tsx)

## Estimated effort

1 dev day

## Concurrency & PR strategy

- **Suggested branch:** `phase-4.1/step-6-frontend-resilience`
- **Blocking steps:** None — independent of backend steps.
- **Merge Readiness:** false (pending implementation)
- Step 7 (TypeScript strict mode) depends on this step — fixes here reduce strict-mode errors.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `Promise.allSettled` changes observable timing | Each result is processed independently; order preserved |
| `ApiError` breaks existing error handling in other components | `ApiError extends Error`, so `catch (err)` still works everywhere |
| `isReEntryMode` field missing from generated types | Verify generated types include it; regenerate if needed |

## References

- [MVP Final Audit §4 Frontend](../../MVP_FINAL_AUDIT.md) — Promise.all, 401 detection, isReEntryMode, duplicate types
- [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx)
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
