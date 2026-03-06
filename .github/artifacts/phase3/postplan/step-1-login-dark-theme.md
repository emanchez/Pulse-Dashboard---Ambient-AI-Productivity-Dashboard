# Step 1 — Login Page Dark Theme Fix

## Purpose

Restyle the login page from its current light-mode design (white background, invisible text) to match the app's dark `slate-950` theme, making form inputs readable.

## Deliverables

- Fully dark-themed login page consistent with the rest of the app.
- Readable input fields with explicit text and background colors.
- Error banner restyled for dark background.

## Primary files to change (required)

- [code/frontend/app/login/page.tsx](code/frontend/app/login/page.tsx)

## Detailed implementation steps

1. In [code/frontend/app/login/page.tsx](code/frontend/app/login/page.tsx), replace the form container class `bg-white rounded-lg shadow p-6 space-y-4` with dark equivalents: `bg-slate-800 border border-slate-700 rounded-xl shadow-xl p-6 space-y-4`.
2. Change the `<h1>` from default (inherits dark text on white bg) to `text-white` or `text-slate-100`.
3. Change both `<label>` elements from `text-gray-700` to `text-slate-300`.
4. Add explicit classes to both `<input>` elements: replace `w-full rounded border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm` with `w-full rounded-lg bg-slate-900 border border-slate-600 text-white px-4 py-2 focus:outline-none focus:border-blue-500 transition-colors sm:text-sm`. This matches the input style used in `ReportForm.tsx`.
5. Restyle the error banner from `bg-red-50 text-red-700` to `bg-red-500/20 text-red-400 border border-red-500/30`.
6. Restyle the submit button from `bg-indigo-600 hover:bg-indigo-700` to `bg-blue-600 hover:bg-blue-700` for consistency with the navbar and report form buttons.

## Integration & Edge Cases

- No persistence changes.
- No JavaScript logic changes — this is CSS/class-only.
- Verify the loading spinner also looks correct on the dark background (it uses `border-gray-300 border-t-indigo-600` — consider updating to `border-slate-600 border-t-blue-500`).

## Acceptance Criteria (required)

1. Both `<input>` fields on `/login` render with visible text (light text on dark background).
2. The login form container uses a dark background (no white rectangles on the dark page).
3. Label text is visible and legible against the dark form background.
4. Error messages (invalid credentials) are visible with dark-appropriate styling.
5. `npm run build` passes with zero errors after changes.

## Testing / QA (required)

**Automated:**
- No backend tests affected.
- `cd code/frontend && npm run build` must pass.

**Manual QA checklist:**
1. Navigate to `/login` — confirm form background is dark (slate-800 or similar), not white.
2. Click into the username field and type — confirm text is visible (white or light color).
3. Click into the password field and type — confirm text is visible.
4. Submit with wrong credentials — confirm the error banner is visible and readable.
5. Submit with correct credentials — confirm redirect to `/tasks`.
6. Resize to mobile width — confirm the form remains centered and readable.

## Files touched (repeat for reviewers)

- [code/frontend/app/login/page.tsx](code/frontend/app/login/page.tsx)

## Estimated effort

< 0.5 dev days

## Concurrency & PR strategy

- Suggested branch: `phase-3/step-1-login-dark-theme`
- Blocking steps: None
- Merge Readiness: false
- This step is in Concurrency Group A and can be worked/merged independently.

## Risks & Mitigations

- **Risk:** Tailwind class changes produce unexpected layout shifts. **Mitigation:** Test at multiple viewport widths; the form is a simple centered column.

## References

- [User observations](./observations.txt) — "login and password text input is white on white text box"
- [code/frontend/components/reports/ReportForm.tsx](code/frontend/components/reports/ReportForm.tsx) — reference dark input styling pattern (`bg-slate-900 border-slate-600 text-white`)

## Author Checklist (must complete before PR)

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation) — N/A (frontend CSS only)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected — N/A
