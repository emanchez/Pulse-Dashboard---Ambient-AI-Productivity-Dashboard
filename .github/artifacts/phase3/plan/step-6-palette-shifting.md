# Step 6 — State-Aware Accent Palette Shifting

## Purpose

Implement subtle state-aware palette shifting so that accent colours (borders, highlights, active indicators) across all pages dynamically tint based on the current `silenceState` (engaged → emerald, stagnant → amber, paused → sky blue), reinforcing the ambient awareness design principle from the PDD without disrupting the base dark slate theme.

## Deliverables

- CSS custom properties (or Tailwind `data-*` attribute strategy) for state-driven accent theming
- Updated `code/frontend/app/layout.tsx` — propagates `data-state` attribute to root element
- Updated `code/frontend/app/globals.css` — defines accent variable sets per state
- Updated page components to consume accent variables for card borders, section headers, and active indicators
- Consistent accent tinting across both `/tasks` and `/reports` pages
- `npm run build` passes with zero TypeScript errors

## Primary files to change (required)

- [code/frontend/app/layout.tsx](../../../../code/frontend/app/layout.tsx) *(modify — add state propagation)*
- [code/frontend/app/globals.css](../../../../code/frontend/app/globals.css) *(modify — add CSS custom properties)*
- [code/frontend/app/tasks/page.tsx](../../../../code/frontend/app/tasks/page.tsx) *(modify — pass state to layout/wrapper)*
- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx) *(modify — pass state to layout/wrapper)*
- [code/frontend/components/reports/ReportCard.tsx](../../../../code/frontend/components/reports/ReportCard.tsx) *(modify — use accent variables)*
- [code/frontend/components/dashboard/FocusHeader.tsx](../../../../code/frontend/components/dashboard/FocusHeader.tsx) *(modify — use accent variables)*
- [code/frontend/components/dashboard/ProductivityPulseCard.tsx](../../../../code/frontend/components/dashboard/ProductivityPulseCard.tsx) *(modify — use accent variables)*
- [code/frontend/tailwind.config.js](../../../../code/frontend/tailwind.config.js) *(modify — add custom colour references if using CSS vars)*

## Detailed implementation steps

1. **Define CSS custom properties** in `code/frontend/app/globals.css`:
   ```css
   :root {
     /* Default (engaged) accent palette */
     --accent-primary: theme('colors.emerald.500');
     --accent-primary-light: theme('colors.emerald.400');
     --accent-bg: theme('colors.emerald.500/0.2');
     --accent-border: theme('colors.emerald.500/0.3');
   }

   [data-state="stagnant"] {
     --accent-primary: theme('colors.amber.500');
     --accent-primary-light: theme('colors.amber.400');
     --accent-bg: theme('colors.amber.500/0.2');
     --accent-border: theme('colors.amber.500/0.3');
   }

   [data-state="paused"] {
     --accent-primary: theme('colors.sky.500');
     --accent-primary-light: theme('colors.sky.400');
     --accent-bg: theme('colors.sky.500/0.2');
     --accent-border: theme('colors.sky.500/0.3');
   }
   ```

2. **Extend Tailwind config** in `code/frontend/tailwind.config.js`:
   ```javascript
   theme: {
     extend: {
       colors: {
         accent: {
           primary: 'var(--accent-primary)',
           light: 'var(--accent-primary-light)',
           bg: 'var(--accent-bg)',
           border: 'var(--accent-border)',
         }
       }
     }
   }
   ```
   This enables classes like `border-accent-primary`, `text-accent-light`, `bg-accent-bg`.

3. **Propagate `data-state` on the root element**:
   - **Strategy A (recommended — client component wrapper):** Create a thin client wrapper component (e.g., `StateProvider.tsx`) that:
     - Accepts `children` and renders them
     - Fetches pulse data (or receives `silenceState` via context)
     - Sets `document.documentElement.dataset.state = silenceState` via `useEffect`
   - **Strategy B (simpler, per-page):** Each page sets `data-state` on its own wrapper div — less elegant but avoids layout-level state management.
   - Recommendation: Use Strategy A with a React Context (`SilenceStateContext`) that both pages subscribe to, and the context provider sets the `data-state` attribute on `<html>`.

4. **Create `SilenceStateContext`** (if using Strategy A):
   - New file: `code/frontend/lib/hooks/useSilenceState.ts` or `code/frontend/components/SilenceStateProvider.tsx`
   - Context provides: `silenceState: "engaged" | "stagnant" | "paused" | null`, `gapMinutes: number`
   - Provider fetches pulse data on mount and polls every 30s (same logic currently duplicated in Tasks and Reports pages)
   - Both pages consume the context instead of each independently fetching pulse
   - The provider sets `document.documentElement.dataset.state = silenceState` in a `useEffect`

5. **Update `layout.tsx`**:
   - Wrap `{children}` with the `SilenceStateProvider` (requires `"use client"` directive on the provider, not on layout)
   - The `<html>` element gets `data-state` set dynamically

6. **Apply accent classes to components**:
   - **`ReportCard.tsx` (expanded):** Replace `border-l-4 border-cyan-500` with `border-l-4 border-accent-primary`
   - **`ReportCard.tsx` (STRATEGIC NARRATIVE header):** Replace `text-cyan-400` with `text-accent-light`
   - **`FocusHeader.tsx`:** Apply `text-accent-light` or `border-accent-border` to the subtitle or accent elements
   - **`ProductivityPulseCard.tsx`:** Tint the Recharts area fill with accent colour (pass `var(--accent-primary)` as fill prop)
   - **Card borders:** Where components use hardcoded emerald/amber/sky for state indicators, replace with accent CSS variables so they auto-shift
   - **Do NOT change the AppNavBar badge** — it already correctly switches colours per state and should remain explicit (the badge is a direct state readout, not ambient tinting)

7. **Verify visual shift works**:
   - Set up three test scenarios:
     - No action logs (or gap < 48h) → engaged → emerald accents
     - Gap > 48h → stagnant → amber accents
     - Active vacation SystemState → paused → sky blue accents
   - Verify on both `/tasks` and `/reports` pages

8. **Build gate**:
   ```bash
   npm run build   # zero errors
   ```

## Integration & Edge Cases

- **Server-side rendering:** CSS custom properties work in SSR — `:root` defaults apply on first paint. The `data-state` attribute is set client-side after hydration, so there may be a brief flash of emerald (default) before the actual state is applied. This is acceptable — the shift is subtle.
- **Pulse fetch deduplication:** With `SilenceStateProvider`, pulse fetching is centralized. Remove duplicate fetch logic from Tasks and Reports pages to avoid double-fetching.
- **Auth dependency:** The pulse endpoint requires a JWT. The `SilenceStateProvider` needs access to the token. Use the existing `useAuth()` hook or pass token via context.
- **Transition animation:** Consider adding `transition: color 0.3s, border-color 0.3s, background-color 0.3s` to elements using accent variables for a smooth shift. This is optional polish.
- **No breaking changes:** All existing component styling should remain functional. The accent variables are additive; hardcoded colours in components that don't use them are unaffected.

## Acceptance Criteria

1. CSS custom properties `--accent-primary`, `--accent-primary-light`, `--accent-bg`, `--accent-border` are defined in `globals.css` with per-state overrides via `[data-state]`.
2. The `<html>` element's `data-state` attribute dynamically reflects the current `silenceState`.
3. On the Reports page: the latest report card's left border and "STRATEGIC NARRATIVE" header tint match the current state (emerald/amber/sky).
4. On the Tasks page: at least one visual element (e.g., FocusHeader accent, PulseCard chart fill) tints per state.
5. Changing the state (e.g., creating/deleting a vacation) causes the accent colour to shift on the next pulse poll (within 30s).
6. The base dark slate theme (backgrounds, text) is NOT affected — only accent elements shift.
7. The `AppNavBar` badge remains explicitly colour-coded (NOT using accent variables) and continues to work correctly.
8. Pulse data is fetched centrally (not duplicated per page).
9. `npm run build` exits 0 with zero TypeScript errors.

## Testing / QA

### Automated checks

```bash
cd code/frontend
npm run build   # zero errors

# Verify CSS variables exist
grep -c "accent-primary" app/globals.css
grep -c "data-state" app/globals.css
```

### Manual QA checklist

1. Start backend + frontend
2. Login → navigate to `/tasks`
3. With no action gap (engaged state): verify emerald accent on FocusHeader/PulseCard elements
4. Insert a stale action log (>48h ago) in DB → refresh → verify amber accent shift
5. Create a vacation state covering now → refresh → verify sky blue accent shift
6. Navigate to `/reports` → verify same accent colour applies to report card border and headers
7. Delete the vacation → verify accent reverts to engaged/stagnant
8. Verify the AppNavBar badge is NOT affected by accent variables (still uses explicit colours)
9. Check that transitions are smooth (no jarring flicker)
10. Verify mobile layout is unaffected

## Files touched (repeat for reviewers)

- [code/frontend/app/layout.tsx](../../../../code/frontend/app/layout.tsx)
- [code/frontend/app/globals.css](../../../../code/frontend/app/globals.css)
- [code/frontend/app/tasks/page.tsx](../../../../code/frontend/app/tasks/page.tsx)
- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx)
- [code/frontend/tailwind.config.js](../../../../code/frontend/tailwind.config.js)
- [code/frontend/components/reports/ReportCard.tsx](../../../../code/frontend/components/reports/ReportCard.tsx)
- [code/frontend/components/dashboard/FocusHeader.tsx](../../../../code/frontend/components/dashboard/FocusHeader.tsx)
- [code/frontend/components/dashboard/ProductivityPulseCard.tsx](../../../../code/frontend/components/dashboard/ProductivityPulseCard.tsx)
- [code/frontend/components/SilenceStateProvider.tsx](../../../../code/frontend/components/SilenceStateProvider.tsx) *(new — optional, if using Strategy A)*
- [code/frontend/lib/hooks/useSilenceState.ts](../../../../code/frontend/lib/hooks/useSilenceState.ts) *(new — optional)*

## Estimated effort

1–1.5 dev days

## Concurrency & PR strategy

- **Suggested branch:** `phase-3/step-6-palette-shifting`
- **Blocking steps:** `phase-3/step-4-reports-page` and `phase-3/step-5-system-state-ui` must both be merged first (components that receive accent styling must exist).
- **Merge Readiness:** false
- This is the final step in Phase 3.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| CSS custom properties not supported on target browsers | All modern browsers support CSS vars; not a concern for dev tool |
| Flash of default accent on initial load (SSR → client hydration) | Default is emerald (engaged) which is the most common state; acceptable |
| Tailwind purge removes CSS var references | Verify Tailwind content config includes the `globals.css` and `data-*` attribute patterns |
| `SilenceStateProvider` context breaks SSR | Wrap in `"use client"` directive; provider renders children without SSR state |

## References

- [PDD.md — §5 UI/UX Strategy: State-Aware Styling](../../PDD.md)
- [product.md — §4 UI/UX Specification: State-Aware Styling](../../product.md)
- [Phase 3 Master](./master.md)
- [Step 4 — Reports Page](./step-4-reports-page.md)
- [Step 5 — SystemState UI](./step-5-system-state-ui.md)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added (build gate + grep checks)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
- [ ] Author signoff
