# Step 8 — Mobile-Responsive UI: NavBar Hamburger, Responsive Tables & Grids

## Purpose

Address three UI responsiveness issues from the audit:

1. **Nav bar is not responsive on mobile** — No hamburger/drawer pattern; tabs overflow on small screens.
2. **Task table overflows on mobile** — Fixed-width columns don't fit narrow viewports.
3. **Report card grid and other grids are non-responsive** — Content overflows horizontally on small screens.

The project requires mobile-first design per the coding standards. All layout components must use responsive classes (`md:col-span-2`).

## Deliverables

- `AppNavBar` with hamburger toggle and slide-out drawer on viewports < 768px (Tailwind `md:` breakpoint).
- Responsive task table: horizontally scrollable wrapper on mobile, or converted to card layout.
- Responsive BentoGrid and report cards: single-column stacking on mobile.
- All changes use Tailwind CSS responsive utilities — no custom media queries.

## Primary files to change

- [code/frontend/components/nav/AppNavBar.tsx](code/frontend/components/nav/AppNavBar.tsx) — Hamburger + drawer
- [code/frontend/components/dashboard/TaskQueueTable.tsx](code/frontend/components/dashboard/TaskQueueTable.tsx) — Responsive table
- [code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx) — Responsive grid
- [code/frontend/components/reports/](code/frontend/components/reports/) — Report card grid responsiveness (if applicable)

## Detailed implementation steps

### 8.1 NavBar: Add hamburger toggle for mobile

In [code/frontend/components/nav/AppNavBar.tsx](code/frontend/components/nav/AppNavBar.tsx):

#### 8.1.1 Add state for mobile menu

```typescript
const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
```

Import `useState` from React and `Menu`, `X` icons from `lucide-react`.

#### 8.1.2 Add hamburger button (visible on mobile only)

In the left section of the nav, after the logo:

```tsx
{/* Hamburger — visible on mobile only */}
<button
  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
  className="md:hidden text-slate-400 hover:text-white ml-3"
  aria-label="Toggle menu"
>
  {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
</button>
```

#### 8.1.3 Hide center tabs on mobile

Wrap the center tabs div with:

```tsx
<div className="hidden md:flex items-center gap-6">
  {/* existing tabs */}
</div>
```

#### 8.1.4 Hide right-side actions on mobile (except logout)

Wrap most right-side items:

```tsx
<div className="flex items-center gap-3">
  {/* Create Report button — hidden on mobile */}
  {onCreateReport && (
    <button className="hidden md:flex items-center gap-1.5 ...">
      + Create New Report
    </button>
  )}
  {/* Badge — hidden on mobile */}
  <span className="hidden md:flex">{badge()}</span>
  {/* ... other items hidden on mobile */}
  
  {/* Logout — always visible */}
  <button onClick={onLogout} className="...">U</button>
</div>
```

#### 8.1.5 Add mobile drawer

Below the main nav bar, add a conditional mobile drawer:

```tsx
{mobileMenuOpen && (
  <div className="md:hidden bg-slate-900 border-b border-slate-800 px-6 py-4 space-y-3">
    {/* Mobile tabs */}
    <Link href="/tasks" className={tabClass("/tasks")} onClick={() => setMobileMenuOpen(false)}>
      Tasks
    </Link>
    <Link href="/synthesis" className={tabClass("/synthesis")} onClick={() => setMobileMenuOpen(false)}>
      <span className="flex items-center gap-1"><Brain size={14} /> Synthesis</span>
    </Link>
    <Link href="/reports" className={tabClass("/reports")} onClick={() => setMobileMenuOpen(false)}>
      Reports
    </Link>
    
    {/* Mobile badge */}
    <div className="pt-2 border-t border-slate-800">
      {badge()}
    </div>
    
    {/* Mobile Create Report button */}
    {onCreateReport && (
      <button onClick={() => { onCreateReport(); setMobileMenuOpen(false); }}
        className="w-full flex items-center justify-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-2 rounded-md">
        + Create New Report
      </button>
    )}
  </div>
)}
```

#### 8.1.6 Close drawer on route change

Use `usePathname()` (already imported) to close the drawer on navigation:

```typescript
const pathname = usePathname();
useEffect(() => {
  setMobileMenuOpen(false);
}, [pathname]);
```

### 8.2 Responsive task table

In [code/frontend/components/dashboard/TaskQueueTable.tsx](code/frontend/components/dashboard/TaskQueueTable.tsx):

#### 8.2.1 Option A: Horizontal scroll wrapper (simpler)

Wrap the `<table>` in a scrollable container:

```tsx
<div className="overflow-x-auto -mx-4 px-4">
  <table className="w-full min-w-[640px]">
    {/* existing table content */}
  </table>
</div>
```

This allows the table to scroll horizontally on mobile while keeping the card padding.

#### 8.2.2 Option B: Card layout on mobile (better UX)

Convert the table to cards on mobile using Tailwind's responsive utilities:

```tsx
{/* Desktop: table layout */}
<div className="hidden md:block">
  <table>...</table>
</div>

{/* Mobile: card layout */}
<div className="md:hidden space-y-3">
  {tasks.map((task) => (
    <div key={task.id} className="bg-slate-800 border border-slate-700 rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-medium text-white text-sm truncate">{task.name}</span>
        <PriorityBadge priority={task.priority} />
      </div>
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>{task.deadline ? formatDate(task.deadline) : "No deadline"}</span>
        <div className="flex gap-2">
          <button onClick={() => onEdit(task)}>Edit</button>
          <button onClick={() => onToggleComplete(task)}>
            {task.isCompleted ? "Undo" : "Complete"}
          </button>
          <button onClick={() => onDelete(task)}>Delete</button>
        </div>
      </div>
    </div>
  ))}
</div>
```

**Recommendation:** Start with Option A (scroll wrapper) for simplicity. Option B can be a follow-up.

### 8.3 Responsive BentoGrid

In [code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx):

Ensure the grid uses responsive column spans. The current grid likely uses fixed `grid-cols-3` or similar. Update to:

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* Grid items with responsive spans */}
</div>
```

For the "tasks-dashboard" variant, ensure:
- Row 1: Stack vertically on mobile (`grid-cols-1`), side-by-side on desktop.
- Row 2: Stack vertically on mobile, 3 columns on desktop.
- Row 3 (task table): Full width on all breakpoints.
- Zone C (reasoning sidebar): Full width on mobile, side column on desktop.

### 8.4 Responsive report card grid

Check if report cards use a fixed grid. If so, update:

```tsx
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
  {reports.map(...)}
</div>
```

### 8.5 Test on mobile viewport

Use browser DevTools responsive mode to test at:
- 375px (iPhone SE)
- 414px (iPhone 12)
- 768px (iPad)
- 1024px+ (desktop)

## Integration & Edge Cases

- **Drawer z-index:** Ensure the mobile drawer doesn't conflict with modals (TaskForm, etc.). Use `z-40` for drawer, `z-50` for modals.
- **Drawer backdrop:** Consider adding a backdrop overlay to close the drawer on outside click.
- **Table sort/filter controls:** If the task table has sort buttons, they should remain accessible on mobile (either in the scroll area or above the table).
- **BentoGrid variants:** The grid may have multiple variants (tasks-dashboard, etc.). Ensure all variants are responsive.

## Acceptance Criteria

1. **AC-1:** At viewport width < 768px, the NavBar shows a hamburger icon instead of inline tabs.
2. **AC-2:** Tapping the hamburger opens a drawer with navigation links, badge, and action buttons.
3. **AC-3:** Tapping a nav link in the drawer navigates and closes the drawer.
4. **AC-4:** At viewport width < 768px, the task table is horizontally scrollable (no content cut off or overflow).
5. **AC-5:** At viewport width < 768px, BentoGrid items stack vertically (single column).
6. **AC-6:** At viewport width 768px+, the layout matches the current desktop design (no regression).
7. **AC-7:** `npm run build` succeeds.
8. **AC-8:** Manual verify: All pages are usable at 375px viewport width.

## Testing / QA

### Automated
```bash
cd code/frontend && npm run build
```

### Manual QA checklist
1. Open `/tasks` in Chrome DevTools responsive mode at 375px.
2. Verify hamburger icon is visible; inline tabs are hidden.
3. Tap hamburger — verify drawer slides open with tabs and badge.
4. Tap "Reports" in drawer — verify navigation and drawer closes.
5. Scroll the task table horizontally — verify all columns are accessible.
6. Resize to 1024px — verify desktop layout is unchanged.
7. Open `/reports` at 375px — verify report cards stack vertically.
8. Open `/synthesis` at 375px — verify content doesn't overflow.

## Files touched

- [code/frontend/components/nav/AppNavBar.tsx](code/frontend/components/nav/AppNavBar.tsx)
- [code/frontend/components/dashboard/TaskQueueTable.tsx](code/frontend/components/dashboard/TaskQueueTable.tsx)
- [code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx)
- [code/frontend/components/reports/](code/frontend/components/reports/) (if applicable)

## Estimated effort

1–2 dev days

## Concurrency & PR strategy

- **Suggested branch:** `phase-4.1/step-8-mobile-responsive-ui`
- **Blocking steps:** None — independent of Steps 1–7 (pure CSS/layout changes).
- **Merge Readiness:** false (pending implementation)

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Desktop layout regression | Manual QA at 1024px+; use responsive-only Tailwind classes |
| Drawer animation jank | Use CSS transitions (Tailwind `transition-all duration-200`); keep DOM minimal |
| Table card layout loses information density | Start with scroll wrapper (Option A); iterate to card layout later |

## References

- [MVP Final Audit §4 Frontend](../../MVP_FINAL_AUDIT.md) — NavBar, tables, grids non-responsive
- [PDD §5](../../PDD.md) — UI/UX Strategy: "Bento Box" Grid
- [Copilot Instructions](../../copilot-instructions.md) — Mobile-First UI requirement
- [code/frontend/components/nav/AppNavBar.tsx](code/frontend/components/nav/AppNavBar.tsx)
- [code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx)

## Author Checklist (must complete before PR)

- [ ] Purpose filled
- [ ] Deliverables listed
- [ ] `Primary files to change` contains workspace-relative links
- [ ] Acceptance Criteria are measurable/testable
- [ ] Tests added under `code/backend/tests/` (happy path + validation)
- [ ] Manual QA checklist added and verified
- [ ] Backup/atomic-write noted if persistence affected
