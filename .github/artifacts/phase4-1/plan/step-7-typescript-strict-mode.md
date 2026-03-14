# Step 7 — Enable TypeScript Strict Mode & Resolve All Type Errors

## Purpose

Enable `"strict": true` in `tsconfig.json` and resolve all resulting type errors. TypeScript strict mode catches `any`, `null`/`undefined` issues, and implicit type coercions that can cause runtime crashes. The audit notes several code paths that pass `string | null` into functions expecting `string`.

## Deliverables

- `tsconfig.json` updated with `"strict": true`.
- All TypeScript type errors resolved across the frontend codebase.
- Zero `npm run build` errors with strict mode enabled.

## Primary files to change

- [code/frontend/tsconfig.json](code/frontend/tsconfig.json) — Enable strict mode
- All `.tsx`/`.ts` files that produce type errors under strict mode (enumerated after initial `tsc --noEmit` run)

### Likely affected files (based on audit patterns)

- [code/frontend/app/tasks/page.tsx](code/frontend/app/tasks/page.tsx) — `string | null` passed to functions expecting `string`
- [code/frontend/lib/api.ts](code/frontend/lib/api.ts) — Return types may need narrowing
- [code/frontend/lib/hooks/useAuth.ts](code/frontend/lib/hooks/useAuth.ts) — `token` is `string | null`
- [code/frontend/components/dashboard/ReasoningSidebar.tsx](code/frontend/components/dashboard/ReasoningSidebar.tsx) — Possible `any` usage
- [code/frontend/components/dashboard/TaskQueueTable.tsx](code/frontend/components/dashboard/TaskQueueTable.tsx) — Array/null handling
- [code/frontend/components/tasks/TaskForm.tsx](code/frontend/components/tasks/TaskForm.tsx) — Optional prop handling
- [code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx) — ReactNode props

## Detailed implementation steps

### 7.1 Enable strict mode

In [code/frontend/tsconfig.json](code/frontend/tsconfig.json), change:

```json
"strict": true
```

This enables all strict-family flags:
- `strictNullChecks`
- `strictFunctionTypes`
- `strictBindCallApply`
- `strictPropertyInitialization`
- `noImplicitAny`
- `noImplicitThis`
- `alwaysStrict`
- `useUnknownInCatchVariables`

### 7.2 Run initial type check to enumerate errors

```bash
cd code/frontend && npx tsc --noEmit 2>&1 | head -100
```

Categorize the errors before fixing:

1. **`Parameter 'x' implicitly has an 'any' type`** — Add explicit types to function parameters, especially event handlers and catch blocks.
2. **`Type 'X | null' is not assignable to type 'X'`** — Add null guards or non-null assertions where appropriate.
3. **`Object is possibly 'null' or 'undefined'`** — Add optional chaining or null checks.
4. **`Variable 'x' is used before being assigned`** — Initialize variables or restructure code.

### 7.3 Common fix patterns

#### Catch block variables

```typescript
// Before (noImplicitAny violation)
} catch (err) {
  console.error(err.message);
}

// After (useUnknownInCatchVariables)
} catch (err: unknown) {
  if (err instanceof Error) {
    console.error(err.message);
  }
}
```

With Step 6's `ApiError`, this becomes:
```typescript
} catch (err: unknown) {
  if (err instanceof ApiError && err.isUnauthorized) {
    logout();
  } else if (err instanceof Error) {
    console.error(err.message);
  }
}
```

#### Token null checks

```typescript
// Before
const { token } = useAuth();
await listTasks(token);  // token is string | null

// After
if (!token) return;
await listTasks(token);  // token narrowed to string
```

Most pages already have `if (!ready || !token || loading) return <LoadingSpinner />` which provides the null guard. Verify this covers all call sites.

#### Event handler types

```typescript
// Before
const handleChange = (e) => { ... }

// After
const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => { ... }
```

#### Optional props

```typescript
// Before
interface Props {
  task?: Task
}
// Used as: task.name  // error: task is possibly undefined

// After
if (!task) return null;
// task.name is now safe
```

### 7.4 Fix files systematically

Process files in dependency order:
1. `lib/api.ts` — Foundation (already addressed in Step 6)
2. `lib/hooks/useAuth.ts` — Token type
3. `components/` — UI components
4. `app/` — Page components

For each file:
1. Run `npx tsc --noEmit` and note errors.
2. Fix errors in that file.
3. Re-run to verify.

### 7.5 Handle generated types

Files in `lib/generated/` are auto-generated and may have implicit `any` or loose types. Options:
1. **Preferred:** Regenerate with strict-compatible settings (`@hey-api/openapi-ts` supports this).
2. **Fallback:** Add `// @ts-ignore` comments or put a `tsconfig` `exclude` for generated files (not ideal).
3. **Last resort:** Create a `tsconfig.generated.json` that overrides strict for generated files.

Check if the generated types already pass strict mode:
```bash
cd code/frontend && npx tsc --noEmit --strict lib/generated/*.ts 2>&1
```

### 7.6 Verify build

```bash
cd code/frontend && npm run build
```

Must succeed with zero errors.

## Integration & Edge Cases

- **Step 6 dependency:** Step 6 fixes `Promise.all` → `allSettled` and introduces `ApiError`. These changes reduce the number of strict-mode errors (catch blocks, null handling). Run Step 7 after Step 6.
- **Generated types compatibility:** If `@hey-api/openapi-ts` generates non-strict code, the generated files may need a `skipLibCheck`-style exclusion. `skipLibCheck` is already `true` in the config.
- **Third-party types:** `lucide-react`, `next` should have proper types. Verify no issues.

## Acceptance Criteria

1. **AC-1:** `tsconfig.json` has `"strict": true`.
2. **AC-2:** `npx tsc --noEmit` produces zero errors.
3. **AC-3:** `npm run build` succeeds.
4. **AC-4:** No `// @ts-ignore` or `// @ts-expect-error` comments added (prefer proper fixes).
5. **AC-5:** No `as any` type assertions introduced (prefer proper typing).
6. **AC-6:** All catch blocks use `unknown` type and narrow before access.
7. **AC-7:** Manual verify: App functions correctly in the browser after build.

## Testing / QA

### Automated
```bash
cd code/frontend && npx tsc --noEmit && echo "PASS" || echo "FAIL"
cd code/frontend && npm run build
```

### Manual QA checklist
1. Enable strict mode and run build — verify it completes.
2. Navigate to `/tasks` — verify page loads and functions.
3. Navigate to `/reports` — verify page loads.
4. Navigate to `/synthesis` — verify page loads.
5. Create a task, edit it, delete it — verify full CRUD works.
6. Log out and log in — verify auth flow works.

## Files touched

- [code/frontend/tsconfig.json](code/frontend/tsconfig.json)
- All `.tsx`/`.ts` files with type errors (exact list determined during implementation)

## Estimated effort

1–2 dev days (depends on number of errors surfaced)

## Concurrency & PR strategy

- **Suggested branch:** `phase-4.1/step-7-typescript-strict-mode`
- **Blocking steps:** `Blocked until: .github/artifacts/phase4-1/plan/step-6-frontend-resilience.md` (Step 6 fixes reduce error count)
- **Merge Readiness:** false (pending implementation)

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Large number of errors (50+) | Systematic file-by-file approach; Step 6 reduces count first |
| Generated types not strict-compatible | Regenerate or exclude from strict; `skipLibCheck` already enabled |
| Fixes introduce runtime regressions | Manual QA checklist covers all user-facing flows |
| Some errors need `as` assertions | Prefer type guards and narrowing; `as` only as last resort with justification comment |

## References

- [MVP Final Audit §2.3](../../MVP_FINAL_AUDIT.md) — TypeScript Strict Mode Disabled
- [code/frontend/tsconfig.json](code/frontend/tsconfig.json)
- [TypeScript strict mode docs](https://www.typescriptlang.org/tsconfig#strict)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
