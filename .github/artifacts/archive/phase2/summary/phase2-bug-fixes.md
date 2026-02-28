# Phase 2 — Bug fixes & recommended solutions

Date: 2026-02-19

This document summarizes the high-priority bugs discovered while implementing Step 2 (Dashboard Experience) and recommended fixes or mitigation approaches.

## High priority

- **422 on PUT /tasks/{id} (Partial body validation)**
  - Symptom: Frontend receives HTTP 422 when saving edits; DevTools show small payload or missing required fields.
  - Cause: `TaskBoard` sends a partial `diff` object in a `PUT` request; the backend `PUT /tasks/{id}` expects a full `TaskSchema` (required `name`).
  - Fix: Merge the original task with the diff before calling `updateTask` so the request body contains a complete task. Example:

```ts
const orig = tasks.find((t) => t.id === id) ?? {}
const body = { ...orig, ...diff }
await updateTask(token, id, body as Task)
```

- **Saving UI can get stuck on auth error**
  - Symptom: When a 401 occurs during the save loop the button remains in `Saving…` state.
  - Cause: `handleSave()` returns early on auth error without calling `setSaving(false)`.
  - Fix: Ensure `setSaving(false)` runs before returning on auth error, or handle auth outside the loop. Example:

```ts
if (err?.message?.includes("401")) {
  setSaving(false)
  onAuthError?.()
  return
}
```

## Medium priority

- **Duplicate / inconsistent pulse helper implementations**
  - Symptom: Two `getPulse` helpers exist (`lib/api.ts` and `lib/generated/pulseClient.ts`).
  - Risk: Divergence in headers/behaviour and maintenance overhead.
  - Fix: Re-export the generated client from `lib/api.ts` or remove the duplicate and use the generated `getPulse` exclusively.

- **Global (non-user-scoped) pulse data**
  - Symptom: `GET /stats/pulse` depends on auth but does not filter `ActionLog` or `SystemState` by user.
  - Risk: Multi-user environments will see global pulse data.
  - Fix: If pulse should be per-user, filter queries by `user_id` (the `get_current_user` value). Otherwise document intentional global behaviour.

## Low priority / UX

- **Deadline format / normalization**
  - Symptom: `TaskBoard` uses date-only input (`YYYY-MM-DD`) while backend stores datetimes.
  - Fix: Normalize `deadline` to an ISO datetime (e.g., append `T00:00:00Z` or convert to server timezone) when merging/sending updates.

- **Layout note**
  - `BentoGrid` currently makes `zoneB` span two cols; verify this matches PDD expectations (Zone B could be 1 col depending on final layout).

## Suggested short-term plan

1. Apply the frontend fixes (merge diff before PUT, setSaving false on auth error, deadline normalization).
2. Re-test saving flow and confirm 422 is resolved.
3. If partial updates are preferred long-term, add a server-side `PATCH /tasks/{id}` that accepts partial bodies and refactor frontend to call it.
4. Consolidate `getPulse` helpers and add user-scoping if required.

---

File created by automation: summary of investigation during Phase 2 Step 2 work.
