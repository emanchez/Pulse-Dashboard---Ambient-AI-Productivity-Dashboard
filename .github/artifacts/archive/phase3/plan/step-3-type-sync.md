# Step 3 — Regenerate TypeScript Client + Typed API Wrappers

## Purpose

Regenerate the TypeScript client types from the updated FastAPI OpenAPI spec (which now includes ManualReport and SystemState endpoints), and add typed wrapper functions in `lib/api.ts` so the frontend can consume all new Phase 3 endpoints with full type safety.

## Deliverables

- Regenerated `code/frontend/lib/generated/types.gen.ts` with new types: `ManualReportSchema`, `ManualReportCreate`, `ManualReportUpdate`, `PaginatedReportsResponse`, `SystemStateSchema`, `SystemStateCreate`, `SystemStateUpdate`
- Regenerated `code/frontend/lib/generated/index.ts` barrel exports
- New typed wrapper functions in `code/frontend/lib/api.ts` for all report and system-state endpoints
- `code/frontend/lib/generated/pulseClient.ts` preserved intact
- `npm run build` passes with zero TypeScript errors

## Primary files to change (required)

- [code/frontend/lib/generated/types.gen.ts](../../../../code/frontend/lib/generated/types.gen.ts) *(regenerated)*
- [code/frontend/lib/generated/index.ts](../../../../code/frontend/lib/generated/index.ts) *(regenerated)*
- [code/frontend/lib/api.ts](../../../../code/frontend/lib/api.ts) *(modify — add new wrapper functions)*
- [code/frontend/lib/generate-client.sh](../../../../code/frontend/lib/generate-client.sh) *(verify — no changes expected)*

## Detailed implementation steps

1. **Ensure backend is running** with all Phase 3 endpoints registered:
   ```bash
   cd code/backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   Verify `http://localhost:8000/openapi.json` includes `/reports` and `/system-states` paths.

2. **Regenerate TypeScript client**:
   ```bash
   cd code/frontend
   npm run generate:api
   ```
   This runs `@hey-api/openapi-ts` against the backend's OpenAPI spec. The output lands in `lib/generated/`.

3. **Verify generated types** in `lib/generated/types.gen.ts`:
   - Confirm presence of `ManualReportSchema` (with `id`, `title`, `body`, `wordCount`, `associatedTaskIds`, `tags`, `status`, `userId`, `createdAt`, `updatedAt`)
   - Confirm presence of `ManualReportCreate` (with `title`, `body`, `associatedTaskIds?`, `tags?`, `status?`)
   - Confirm presence of `ManualReportUpdate` (all optional)
   - Confirm presence of `PaginatedReportsResponse` (with `items`, `total`, `offset`, `limit`)
   - Confirm presence of `SystemStateSchema` (with `id`, `modeType`, `startDate`, `endDate`, `requiresRecovery`, `description`, `userId`)
   - Confirm presence of `SystemStateCreate` and `SystemStateUpdate`

4. **Verify `pulseClient.ts` is preserved**:
   - The hand-written `code/frontend/lib/generated/pulseClient.ts` must NOT be overwritten. If the generator removes it, restore from git.

5. **Add type re-exports** to `code/frontend/lib/api.ts`:
   ```typescript
   import type {
     ManualReportSchema,
     ManualReportCreate,
     ManualReportUpdate,
     PaginatedReportsResponse,
     SystemStateSchema,
     SystemStateCreate,
     SystemStateUpdate,
   } from "./generated";
   export type {
     ManualReportSchema,
     ManualReportCreate,
     ManualReportUpdate,
     PaginatedReportsResponse,
     SystemStateSchema,
     SystemStateCreate,
     SystemStateUpdate,
   };
   ```

6. **Add Report API wrappers** in `code/frontend/lib/api.ts`:
   ```typescript
   // ── Reports ─────────────────────────────────────────────────────────────────
   
   export async function createReport(token: string, data: ManualReportCreate): Promise<ManualReportSchema> {
     return request(`/reports`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) });
   }
   
   export async function listReports(token: string, offset = 0, limit = 20, status?: string): Promise<PaginatedReportsResponse> {
     const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
     if (status) params.set("status", status);
     return request(`/reports?${params}`, { headers: { Authorization: `Bearer ${token}` } });
   }
   
   export async function getReport(token: string, id: string): Promise<ManualReportSchema> {
     return request(`/reports/${id}`, { headers: { Authorization: `Bearer ${token}` } });
   }
   
   export async function updateReport(token: string, id: string, data: ManualReportUpdate): Promise<ManualReportSchema> {
     return request(`/reports/${id}`, { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) });
   }
   
   export async function deleteReport(token: string, id: string): Promise<void> {
     return request(`/reports/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
   }
   
   export async function archiveReport(token: string, id: string): Promise<ManualReportSchema> {
     return request(`/reports/${id}/archive`, { method: "PATCH", headers: { Authorization: `Bearer ${token}` } });
   }
   ```

7. **Add SystemState API wrappers**:
   ```typescript
   // ── System States ──────────────────────────────────────────────────────────
   
   export async function createSystemState(token: string, data: SystemStateCreate): Promise<SystemStateSchema> {
     return request(`/system-states`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) });
   }
   
   export async function listSystemStates(token: string): Promise<SystemStateSchema[]> {
     return request(`/system-states`, { headers: { Authorization: `Bearer ${token}` } });
   }
   
   export async function getActiveSystemState(token: string): Promise<SystemStateSchema | null> {
     const res = await fetch(`${BASE}/system-states/active`, {
       credentials: "omit",
       headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
     });
     if (!res.ok) {
       const text = await res.text();
       throw new Error(`Request failed ${res.status}: ${text}`);
     }
     const text = await res.text();
     if (!text || text.trim() === "null") return null;
     return JSON.parse(text) as SystemStateSchema;
   }
   
   export async function updateSystemState(token: string, id: string, data: SystemStateUpdate): Promise<SystemStateSchema> {
     return request(`/system-states/${id}`, { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) });
   }
   
   export async function deleteSystemState(token: string, id: string): Promise<void> {
     return request(`/system-states/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
   }
   ```

8. **Update default export** at bottom of `api.ts`:
   ```typescript
   export default {
     login, me,
     listTasks, createTask, updateTask, deleteTask,
     getActiveSession, startSession, stopSession,
     getFlowState,
     createReport, listReports, getReport, updateReport, deleteReport, archiveReport,
     createSystemState, listSystemStates, getActiveSystemState, updateSystemState, deleteSystemState,
   };
   ```

9. **Build gate**:
   ```bash
   npm run build
   ```
   Must exit 0 with zero TypeScript errors.

## Integration & Edge Cases

- **Generator overwrites:** `@hey-api/openapi-ts` regenerates all files in `lib/generated/`. The hand-written `pulseClient.ts` lives in the same directory. Verify the generator config's output doesn't delete files it didn't create. If it does, restore `pulseClient.ts` from git after generation.
- **`getActiveSystemState` null handling:** Uses the same pattern as `getActiveSession` — raw fetch + manual null check — since the `request()` helper doesn't handle null bodies well.
- **CamelCase consistency:** Backend serializes with camelCase aliases. Generated types should reflect camelCase field names. Verify the OpenAPI spec uses `alias` names (camelCase) not Python snake_case.
- **No runtime testing in this step:** This step is purely type/contract work. Runtime testing of the API calls happens in Steps 4 and 5 when the frontend pages consume them.

## Acceptance Criteria

1. `npm run generate:api` exits 0.
2. `lib/generated/types.gen.ts` contains `ManualReportSchema` with fields: `id`, `title`, `body`, `wordCount`, `associatedTaskIds`, `tags`, `status`, `userId`, `createdAt`, `updatedAt`.
3. `lib/generated/types.gen.ts` contains `SystemStateSchema` with fields: `id`, `modeType`, `startDate`, `endDate`, `requiresRecovery`, `description`, `userId`.
4. `lib/generated/types.gen.ts` contains `ManualReportCreate`, `ManualReportUpdate`, `PaginatedReportsResponse`, `SystemStateCreate`, `SystemStateUpdate`.
5. `lib/generated/pulseClient.ts` exists and is unchanged.
6. `lib/api.ts` exports: `createReport`, `listReports`, `getReport`, `updateReport`, `deleteReport`, `archiveReport`, `createSystemState`, `listSystemStates`, `getActiveSystemState`, `updateSystemState`, `deleteSystemState`.
7. `npm run build` exits 0 with zero TypeScript errors.
8. All pre-existing type exports (`Task`, `SessionLogSchema`, `FlowStateSchema`, `PulseStats`) remain available.

## Testing / QA

### Automated checks

```bash
# Type generation
cd code/frontend
npm run generate:api
echo "Exit code: $?"

# Build gate
npm run build
echo "Exit code: $?"

# Verify key types exist in generated output
grep -c "ManualReportSchema" lib/generated/types.gen.ts
grep -c "SystemStateSchema" lib/generated/types.gen.ts
grep -c "PaginatedReportsResponse" lib/generated/types.gen.ts

# Verify pulseClient preserved
test -f lib/generated/pulseClient.ts && echo "pulseClient OK" || echo "MISSING"
```

### Manual QA checklist

1. Run `npm run generate:api` → verify exit 0, no errors
2. Open `lib/generated/types.gen.ts` → verify new types present with camelCase field names
3. Open `lib/api.ts` → verify new wrapper functions compile (no red squiggles in IDE)
4. Run `npm run build` → verify 0 exit code, 0 errors
5. Verify `pulseClient.ts` still exists with `getPulse` and `PulseStats` exports

## Files touched (repeat for reviewers)

- [code/frontend/lib/generated/types.gen.ts](../../../../code/frontend/lib/generated/types.gen.ts)
- [code/frontend/lib/generated/index.ts](../../../../code/frontend/lib/generated/index.ts)
- [code/frontend/lib/api.ts](../../../../code/frontend/lib/api.ts)

## Estimated effort

0.5 dev day

## Concurrency & PR strategy

- **Suggested branch:** `phase-3/step-3-type-sync`
- **Blocking steps:** `phase-3/step-1-manual-report-backend` and `phase-3/step-2-system-state-backend` must both be merged first (OpenAPI spec must include all new endpoints).
- **Merge Readiness:** false
- Steps 4 and 5 depend on this step.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Generator overwrites `pulseClient.ts` | Restore from git; verify generator config excludes manual files |
| OpenAPI spec field names are snake_case instead of camelCase | FastAPI + Pydantic alias_generator should emit camelCase in the spec; verify before generating |
| Generated types drift from backend schemas | Run type generation as part of CI; compare checksums |

## References

- [architecture.md — §3 Synchronization (Type Sync)](../../architecture.md)
- [Phase 3 Master](./master.md)
- [Step 1 — ManualReport Backend](./step-1-manual-report-backend.md)
- [Step 2 — SystemState Backend](./step-2-system-state-backend.md)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added (build gate + grep checks)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
- [ ] Author signoff
