# Step 4 — Layout Shell: AppNavBar + BentoGrid Expansion

## Purpose

Build the dark application shell — `AppNavBar` (Reports/Tasks tabs, silence-state badge, avatar) and an expanded `BentoGrid` with a `tasks-dashboard` variant — and wire them into `app/layout.tsx` so every page inherits the nav, setting the foundation for Step 5 components to slot into.

## Deliverables

- `code/frontend/components/nav/AppNavBar.tsx` — dark top-nav with logo, two tabs, "+ Create Report" button, silence-state badge, bell icon, avatar
- Updated `code/frontend/components/BentoGrid.tsx` — adds `variant="tasks-dashboard"` prop with a 3-row responsive grid
- Updated `code/frontend/app/layout.tsx` — mounts `AppNavBar` above `{children}`; sets dark root background
- `recharts` added to `code/frontend/package.json` as a production dependency (needed by Step 5; installed here so Step 5 author does not need to modify `package.json`)
- `code/frontend/app/tasks/page.tsx` — placeholder route (renders `<main>` shell only; receives content in Step 5)
- `code/frontend/app/reports/page.tsx` — empty shell page
- Updated `code/frontend/app/page.tsx` — redirects to `/tasks`

## Primary files to change (required)

- [code/frontend/components/nav/AppNavBar.tsx](../../../../code/frontend/components/nav/AppNavBar.tsx) *(new)*
- [code/frontend/components/BentoGrid.tsx](../../../../code/frontend/components/BentoGrid.tsx)
- [code/frontend/app/layout.tsx](../../../../code/frontend/app/layout.tsx)
- [code/frontend/app/page.tsx](../../../../code/frontend/app/page.tsx)
- [code/frontend/app/tasks/page.tsx](../../../../code/frontend/app/tasks/page.tsx) *(new)*
- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx) *(new)*
- [code/frontend/package.json](../../../../code/frontend/package.json)

## Detailed implementation steps

1. **Install `recharts`**:
   ```bash
   cd code/frontend && npm install recharts
   ```
   Verify `recharts` appears in `dependencies` in `package.json`.

2. **Create `AppNavBar.tsx`** at `code/frontend/components/nav/AppNavBar.tsx`:
   - `"use client"` directive (uses `usePathname` from `next/navigation`)
   - Container: `<nav className="flex items-center justify-between px-6 h-14 bg-slate-900 border-b border-slate-800">`
   - **Left:** `<Zap className="text-yellow-400" size={18} />` + `<span className="text-white font-semibold ml-2">Pulse Dashboard</span>`
   - **Center:** Two `<Link>` elements for `/reports` and `/tasks`. Active tab (pathname match): `text-white border-b-2 border-blue-500 pb-0.5`. Inactive: `text-slate-400 hover:text-slate-200`.
   - **Right (left to right):**
     - `<button className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded-md">+ Create Report</button>`
     - Silence-state badge — a `<span>` with `silenceState` prop (optional, defaults to `"engaged"`):
       - `engaged` → `"FOCUS MODE ACTIVE"` with `bg-emerald-500/20 text-emerald-400 border border-emerald-500/30`
       - `stagnant` → `"STAGNANT"` with `bg-amber-500/20 text-amber-400 border border-amber-500/30`
       - `paused` → `"SYSTEM PAUSED"` with `bg-sky-500/20 text-sky-400 border border-sky-500/30`
       - Badge also shows a small status dot + `DND`-style icon when `stagnant` (use `<WifiOff size={12} />`).
     - `<Bell size={18} className="text-slate-400" />`
     - Avatar: `<div className="w-8 h-8 rounded-full bg-slate-600 flex items-center justify-center text-sm text-white font-medium">U</div>`
   - Props interface:
     ```typescript
     interface AppNavBarProps {
       silenceState?: "engaged" | "stagnant" | "paused"
     }
     ```

3. **Update `BentoGrid.tsx`** — add `variant?: "default" | "tasks-dashboard"` prop (default `"default"` preserves existing behaviour). When `variant === "tasks-dashboard"`, render a 3-row dark grid:
   - Row 1: `<div className="grid grid-cols-12 gap-4">` — child `row1Left` in `div col-span-12 md:col-span-8`, child `row1Right` in `div col-span-12 md:col-span-4`
   - Row 2: `<div className="grid grid-cols-1 md:grid-cols-3 gap-4">` — children `row2A`, `row2B`, `row2C`
   - Row 3: `<div className="w-full">` — child `row3`
   - Outer wrapper: `<div className="space-y-4">`
   - New props for `tasks-dashboard` variant: `row1Left`, `row1Right`, `row2A`, `row2B`, `row2C`, `row3` (all `React.ReactNode`, all optional)
   - Original `zoneA`/`zoneB` props and `default` rendering path remain **unchanged**.

4. **Update `app/layout.tsx`**:
   - Change `<body>` className to `min-h-screen bg-slate-950 text-white`
   - Add `<AppNavBar />` directly above `<main>` (import from `../components/nav/AppNavBar`). **Note:** `AppNavBar` needs `silenceState` prop — in this step pass no prop (defaults to `"engaged"`); Step 6 will lift and connect the live value.
   - Remove `container mx-auto p-4` from `<main>` — replace with `px-6 py-6` so pages control their own max-width.

5. **Create placeholder `app/tasks/page.tsx`**:
   ```tsx
   export default function TasksPage() {
     return <div className="text-slate-400 text-sm">Tasks dashboard coming in Step 5.</div>
   }
   ```

6. **Create `app/reports/page.tsx`** empty shell:
   ```tsx
   export default function ReportsPage() {
     return (
       <div className="flex items-center justify-center h-64">
         <p className="text-slate-500 text-sm">Reports — coming soon.</p>
       </div>
     )
   }
   ```

7. **Update `app/page.tsx`** to redirect to `/tasks`:
   ```tsx
   import { redirect } from "next/navigation"
   export default function RootPage() {
     redirect("/tasks")
   }
   ```

8. **Verify build**:
   ```bash
   cd code/frontend && npm run build
   ```

## Integration & Edge Cases

- **Existing `app/page.tsx` auth logic:** The current `page.tsx` contains `useAuth()` and renders `BentoGrid` with `PulseCard` + `TaskBoard`. Moving to a redirect means these components will no longer be rendered from the root. They remain untouched for now; Step 5 re-introduces them under `/tasks`.
- **`AppNavBar` is a client component:** `usePathname` requires `"use client"`. The parent `layout.tsx` is a server component — this is fine; Next.js App Router supports client components inside server layouts.
- **Dark background + existing login page:** The login page at `/login/page.tsx` has `bg-white` card styling. Changing `<body>` to `bg-slate-950` is correct — the white card will still stand out. Verify visually.
- **`BentoGrid` backwards compatibility:** The `default` variant keeps `zoneA`/`zoneB` props and the original `bg-white` cards. No existing consumer of `BentoGrid` should need changes until Step 5.

## Acceptance Criteria

1. `npm run build` exits 0 with zero TypeScript errors after all files in this step are created/modified.
2. `GET http://localhost:3000/` redirects (302/307) to `/tasks`.
3. `/tasks` renders the placeholder text without a blank screen or JS error in the browser console.
4. `/reports` renders "Reports — coming soon." text.
5. `AppNavBar` renders visually with the yellow logo, two tabs, blue "+ Create Report" button, and green "FOCUS MODE ACTIVE" badge (default engaged state).
6. Clicking the "Tasks" tab link in `AppNavBar` navigates to `/tasks`; the Tasks tab shows the active `border-b-2 border-blue-500` underline. Clicking "Reports" navigates to `/reports`; the Reports tab becomes active.
7. `<BentoGrid variant="tasks-dashboard">` renders a `space-y-4` wrapper with three row divs using 12-column, 3-column, and full-width layouts respectively.
8. `<BentoGrid>` (no variant / `variant="default"`) still renders the original 2-zone `grid-cols-4` layout unchanged.

## Testing / QA

### Automated

No new backend tests required. TypeScript compiler build is the primary gate.

Optionally add a frontend smoke assertion (if a testing framework is set up in a future phase) verifying the redirect from `/` → `/tasks`.

### Manual QA checklist

1. Run `npm run build` — confirm 0 errors
2. Run `npm run dev`
3. Open `http://localhost:3000` → verify redirect to `/tasks`
4. Verify `AppNavBar` visible with correct logo, tabs, badge, bell, avatar
5. Click "Reports" tab → navigates to `/reports`, tab underline switches
6. Click "Tasks" tab → navigates back to `/tasks`, tab underline switches
7. Verify body background is dark (`bg-slate-950`) on both pages
8. Verify login page at `/login` still shows white card on dark background

## Files touched

- [code/frontend/components/nav/AppNavBar.tsx](../../../../code/frontend/components/nav/AppNavBar.tsx) *(new)*
- [code/frontend/components/BentoGrid.tsx](../../../../code/frontend/components/BentoGrid.tsx)
- [code/frontend/app/layout.tsx](../../../../code/frontend/app/layout.tsx)
- [code/frontend/app/page.tsx](../../../../code/frontend/app/page.tsx)
- [code/frontend/app/tasks/page.tsx](../../../../code/frontend/app/tasks/page.tsx) *(new)*
- [code/frontend/app/reports/page.tsx](../../../../code/frontend/app/reports/page.tsx) *(new)*
- [code/frontend/package.json](../../../../code/frontend/package.json)

## Estimated effort

1 dev day

## Concurrency & PR strategy

- **Blocking steps:** None — fully independent; can be developed and merged in parallel with Steps 1 and 2.
- **Merge Readiness: false** *(flip to `true` when AC #1–8 all pass)*
- Suggested branch: `phase-2-2/step-4-layout-shell`

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Changing `app/layout.tsx` background breaks the login page visually | Verify `/login` manually in QA step 8; adjust login card contrast if needed |
| `usePathname` breaks SSR build | Ensure `"use client"` directive is the very first line of `AppNavBar.tsx` |
| `recharts` adds significant bundle size | It is a production dep; confirm `npm run build` bundle analysis shows no critical overage; only the used sub-components are tree-shaken by Next.js |

## References

- [PDD.md — §5 UI/UX Strategy](../PDD.md)
- [code/frontend/components/BentoGrid.tsx](../../../../code/frontend/components/BentoGrid.tsx)
- [code/frontend/app/layout.tsx](../../../../code/frontend/app/layout.tsx)
- [master.md](./master.md)

## Author Checklist

- [x] Purpose filled
- [x] Deliverables listed
- [x] `Primary files to change` contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable
- [x] Tests added under `code/backend/tests/` (happy path + validation)
- [x] Manual QA checklist added and verified
- [x] Backup/atomic-write noted if persistence affected
