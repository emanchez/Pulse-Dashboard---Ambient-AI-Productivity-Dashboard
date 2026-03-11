# Step 4 — TypeScript Client Regeneration

## Purpose

Regenerate the TypeScript client from the updated backend OpenAPI spec so the frontend has access to the new `TaskCreate` type and updated schema shapes.

## Deliverables

- Regenerated [code/frontend/lib/generated/types.gen.ts](code/frontend/lib/generated/types.gen.ts) reflecting `TaskCreate`, updated `TaskSchema` (with `userId`), and validated `TaskUpdate`.
- Updated [code/frontend/lib/generated/index.ts](code/frontend/lib/generated/index.ts) barrel exports.
- Updated [code/frontend/lib/api.ts](code/frontend/lib/api.ts) to export `TaskCreate`, use it in `createTask()`, and use `TaskUpdate` in `updateTask()`.

## Primary files to change (required)

- [code/frontend/lib/generated/types.gen.ts](code/frontend/lib/generated/types.gen.ts) (regenerated)
- [code/frontend/lib/generated/index.ts](code/frontend/lib/generated/index.ts) (regenerated)
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts)

## Detailed implementation steps

1. Ensure the backend is running with Step 3 changes merged (the OpenAPI spec must reflect the new `TaskCreate` schema and updated `TaskSchema`).
2. Run the generation script:
   ```bash
   cd code/frontend && bash lib/generate-client.sh
   ```
3. Verify that [code/frontend/lib/generated/types.gen.ts](code/frontend/lib/generated/types.gen.ts) now contains:
   - `TaskCreate` type with fields: `name`, `priority?`, `tags?`, `isCompleted?`, `deadline?`, `notes?` (no `id`, `createdAt`, `updatedAt`).
   - `TaskSchema` type with `userId` field added.
   - `TaskUpdate` type with validators reflected (optional fields).
4. In [code/frontend/lib/api.ts](code/frontend/lib/api.ts):
   - Import `TaskCreate` from `./generated`:
     ```typescript
     import type {
       TaskSchema as Task,
       TaskCreate,
       // ... existing imports
     } from "./generated";
     ```
   - Re-export it: `export type { Task, TaskCreate, ... };`
   - Update `createTask` signature from `task: Task` to `task: TaskCreate`:
     ```typescript
     export async function createTask(token: string, task: TaskCreate) {
     ```
   - Update `updateTask` signature from `task: Task` to `task: TaskUpdate`:
     ```typescript
     export async function updateTask(token: string, id: string, task: TaskUpdate) {
     ```
   - Import `TaskUpdate` from `./generated` if not already imported.
5. Run `npm run build` to confirm zero TypeScript errors.

## Integration & Edge Cases

- No persistence changes.
- If the backend OpenAPI spec URL is different in the generation script, verify it matches the running backend.
- Any frontend component that directly imports `TaskSchema` from `types.gen.ts` may need updates if the shape changed significantly (e.g., `TaskQueueTable.tsx` imports `TaskSchema` directly). Verify imports compile cleanly.

## Acceptance Criteria (required)

1. `TaskCreate` type exists in [code/frontend/lib/generated/types.gen.ts](code/frontend/lib/generated/types.gen.ts).
2. `TaskSchema` type in generated output includes `userId` field.
3. `createTask()` in [code/frontend/lib/api.ts](code/frontend/lib/api.ts) accepts `TaskCreate` (not full `Task`).
4. `updateTask()` in [code/frontend/lib/api.ts](code/frontend/lib/api.ts) accepts `TaskUpdate` (not full `Task`).
5. `TaskCreate` is exported from [code/frontend/lib/api.ts](code/frontend/lib/api.ts).
6. `npm run build` passes with zero errors.

## Testing / QA (required)

**Automated:**
```bash
cd code/frontend && npm run build
```

**Manual QA checklist:**
1. Open [code/frontend/lib/generated/types.gen.ts](code/frontend/lib/generated/types.gen.ts) — confirm `TaskCreate` interface is present with correct fields.
2. Open [code/frontend/lib/api.ts](code/frontend/lib/api.ts) — confirm `createTask` uses `TaskCreate` type.
3. Run `npm run build` — confirm no TypeScript compilation errors.

## Files touched (repeat for reviewers)

- [code/frontend/lib/generated/types.gen.ts](code/frontend/lib/generated/types.gen.ts)
- [code/frontend/lib/generated/index.ts](code/frontend/lib/generated/index.ts)
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts)

## Estimated effort

< 0.5 dev days

## Concurrency & PR strategy

- Suggested branch: `phase-3/step-4-type-sync-regen`
- Blocking steps: Blocked until `.github/artifacts/phase3/postplan/step-3-backend-task-hardening.md` is merged (branch: `phase-3/step-3-backend-task-hardening`).
- Merge Readiness: false
- Step 5 (Task CRUD UI) is blocked on this step.

## Risks & Mitigations

- **Risk:** Generation script produces unexpected output if backend isn't running. **Mitigation:** Pre-requisite: start backend with Step 3 changes before running generation.
- **Risk:** Generated types break existing component imports. **Mitigation:** `npm run build` is the gate; fix any breakage before merging.

## References

- [code/frontend/lib/generate-client.sh](code/frontend/lib/generate-client.sh) — generation script.
- [Step 3 — Backend Task Hardening](./step-3-backend-task-hardening.md) — produces the updated OpenAPI spec.
- [Architecture — Type Sync](../../architecture.md)

## Author Checklist (must complete before PR)

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation) — N/A (frontend type sync only)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected — N/A
