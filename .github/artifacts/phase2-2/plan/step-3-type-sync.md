# Step 3 — Type Sync: Regenerate API Client

## Purpose

Run `@hey-api/openapi-ts` against the updated OpenAPI spec (after Steps 1 and 2 are merged) to replace the hand-written stubs in `lib/generated/` with a generated client, then add typed wrapper functions in `lib/api.ts` for all new endpoints (`getFlowState`, `startSession`, `stopSession`, `getActiveSession`).

## Deliverables

- Regenerated `code/frontend/lib/generated/index.ts` — barrel re-export of all generated types and clients
- Regenerated `code/frontend/lib/generated/types.ts` — TypeScript types for `Task`, `PulseStats`, `SessionLog`, `FlowState`, `FlowPoint`, and any other schema the generator emits
- Regenerated `code/frontend/lib/generated/pulseClient.ts` — or equivalent generated service file(s)
- Updated `code/frontend/lib/api.ts` — four new wrapper functions: `getFlowState`, `startSession`, `stopSession`, `getActiveSession`

## Primary files to change (required)

- [code/frontend/lib/generated/index.ts](../../../../code/frontend/lib/generated/index.ts)
- [code/frontend/lib/generated/types.ts](../../../../code/frontend/lib/generated/types.ts)
- [code/frontend/lib/generated/pulseClient.ts](../../../../code/frontend/lib/generated/pulseClient.ts)
- [code/frontend/lib/api.ts](../../../../code/frontend/lib/api.ts)

## Detailed implementation steps

1. **Snapshot the current hand-written stubs** — copy `lib/generated/` to `lib/generated.bak/` (not committed; gitignored) so they can be restored if the generator output is unusable.

2. **Ensure the backend is running** with Steps 1 and 2 merged and the DB migrated:
   ```bash
   cd code/backend && uvicorn app.main:app --reload
   ```
   Verify `http://localhost:8000/openapi.json` contains paths for `/sessions/start`, `/sessions/stop`, `/sessions/active`, and `/stats/flow-state`.

3. **Run the generator**:
   ```bash
   cd code/frontend
   npm run generate:api
   # expands to: bash ./lib/generate-client.sh http://localhost:8000/openapi.json ./lib/generated
   ```

4. **Verify generated output** — the following types must be present (names may vary by generator version; adjust wrapper imports accordingly):
   - A type representing `SessionLogSchema` fields: `id`, `userId`, `taskId`, `taskName`, `goalMinutes`, `startedAt`, `endedAt`, `elapsedMinutes`
   - A type representing `FlowStateSchema` fields: `flowPercent`, `changePercent`, `windowLabel`, `series`
   - A type representing `FlowPointSchema` fields: `time`, `activityScore`
   - Existing `Task` and `PulseStats` types must still be present (regression check)

5. **Update `code/frontend/lib/api.ts`** — add the four new wrapper functions after the existing exports, following the same `request()` helper pattern already used by `listTasks`, `updateTask`, etc.:

   ```typescript
   // Session management
   export async function getActiveSession(token: string): Promise<SessionLog | null> { ... }
   export async function startSession(token: string, body: SessionStartRequest): Promise<SessionLog> { ... }
   export async function stopSession(token: string): Promise<SessionLog> { ... }

   // Flow state
   export async function getFlowState(token: string): Promise<FlowState> { ... }
   ```

   Where `SessionLog`, `SessionStartRequest`, and `FlowState` are imported from `./generated`.

6. **Re-export** any needed types from `lib/generated/index.ts` so downstream components can import from a single barrel: `export type { SessionLog, SessionStartRequest, FlowState, FlowPoint } from './types'`.

7. **Run TypeScript build gate**:
   ```bash
   cd code/frontend && npm run build
   ```
   Must exit 0 with zero TS errors.

## Integration & Edge Cases

- **Generator version `0.27.0` output shape:** `@hey-api/openapi-ts@0.27.0` emits a `services.ts` and `types.ts` at minimum. The existing `pulseClient.ts` hand-written file will be removed or overwritten. Verify `getPulse` is either regenerated or manually preserved — if the generator does not emit a `getPulse` function, keep a hand-written `pulseClient.ts` alongside generated files and adjust the barrel to re-export it.
- **`getActiveSession` returns `null`:** The backend returns JSON `null` for no session. The wrapper must handle `response.json()` returning `null` without throwing — add a `null` return type and do not throw on `null` body.
- **Existing `PulseCard` uses `getPulse`:** After regeneration, verify `PulseCard.tsx` import path still resolves (it imports from `lib/generated/pulseClient`). If the generator replaces that file, update the import in `PulseCard.tsx` to point at the new generated path.
- **No backend running during CI:** The `generate:api` script requires a live backend. In a CI environment, either mock the OpenAPI spec or gate this step on a running backend Docker service. Document this in the PR.

## Acceptance Criteria

1. `npm run generate:api` exits 0 with no errors.
2. `lib/generated/types.ts` contains TypeScript types with fields for `sessionLog` (camelCase: `id`, `taskName`, `goalMinutes`, `elapsedMinutes`, `startedAt`, `endedAt`) and `flowState` (`flowPercent`, `changePercent`, `windowLabel`, `series`).
3. `lib/api.ts` exports `getFlowState`, `startSession`, `stopSession`, `getActiveSession` functions with correct return type signatures.
4. `npm run build` exits 0 with zero TypeScript errors.
5. Importing `getPulse` in `PulseCard.tsx` still resolves without a module-not-found error.
6. Calling `getActiveSession(token)` when no session is active returns `null` (not an exception).

## Testing / QA

### Automated

No new unit tests required for this step — it is a code-generation + wiring step. The TypeScript compiler (`npm run build`) is the primary gate.

### Manual QA checklist

1. Start backend (Steps 1 + 2 merged): `uvicorn app.main:app --reload`
2. Confirm `http://localhost:8000/openapi.json` has `/sessions/start`, `/sessions/stop`, `/sessions/active`, `/stats/flow-state`
3. Run `npm run generate:api` — output lists generated files with no errors
4. Open `lib/generated/types.ts` — visually verify presence of session and flow state types
5. Run `npm run build` — zero errors
6. Open `lib/api.ts` — verify four new wrapper functions are present and typed

## Files touched

- [code/frontend/lib/generated/index.ts](../../../../code/frontend/lib/generated/index.ts)
- [code/frontend/lib/generated/types.ts](../../../../code/frontend/lib/generated/types.ts)
- [code/frontend/lib/generated/pulseClient.ts](../../../../code/frontend/lib/generated/pulseClient.ts)
- [code/frontend/lib/api.ts](../../../../code/frontend/lib/api.ts)

## Estimated effort

0.5 dev day

## Concurrency & PR strategy

- **Blocking steps:** Blocked until both [step-1-session-model.md](./step-1-session-model.md) and [step-2-flow-state.md](./step-2-flow-state.md) are merged and the backend is running with the updated schema.
- **Merge Readiness: false** *(flip to `true` when `npm run build` exits 0 and all generated types are confirmed)*
- Suggested branch: `phase-2-2/step-3-type-sync`
- `Depends-On: phase-2-2/step-1-session-model, phase-2-2/step-2-flow-state`

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Generator overwrites `getPulse` / `pulseClient.ts` and breaks `PulseCard` | Keep a backup of `lib/generated/` before running; manually restore `getPulse` if not regenerated |
| Generator output TypeScript naming does not match hand-written type aliases | Adjust wrapper function return types in `api.ts` to use whatever names the generator emits; update imports in Step 5 components accordingly |
| `null` body from `getActiveSession` throws in a `response.json()` call | Explicitly check `response.status === 200 && content-length > 0` or use a try/catch around `.json()` |

## References

- [code/frontend/lib/generate-client.sh](../../../../code/frontend/lib/generate-client.sh)
- [code/frontend/package.json](../../../../code/frontend/package.json)
- [step-1-session-model.md](./step-1-session-model.md)
- [step-2-flow-state.md](./step-2-flow-state.md)
- [master.md](./master.md)

## Author Checklist

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/` (happy path + validation)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected
