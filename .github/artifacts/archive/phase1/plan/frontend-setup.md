# Step 4 — Frontend Setup

## Purpose
Set up Next.js frontend with Bento Box grid layout and basic components.

## Deliverables
- code/frontend/package.json: Dependencies for Next.js, TypeScript, Tailwind, Lucide.
- code/frontend/app/layout.tsx: Root layout with Bento grid.
- code/frontend/components/BentoGrid.tsx: Grid component.
- code/frontend/app/page.tsx: Main dashboard page.

## Primary files to change
- [code/frontend/package.json](code/frontend/package.json)
- [code/frontend/app/layout.tsx](code/frontend/app/layout.tsx)
- [code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx)
- [code/frontend/app/page.tsx](code/frontend/app/page.tsx)

## Detailed implementation steps
1. Create package.json with Next.js 14, TypeScript, Tailwind CSS, Lucide React.
2. In layout.tsx, set up HTML structure with Tailwind.
3. In BentoGrid.tsx, create responsive grid with md:col-span-2 classes.
4. In page.tsx, render BentoGrid with placeholder zones.

## Integration & Edge Cases
- Mobile-first responsive design.

## Acceptance Criteria
1. npm install succeeds.
2. npm run dev starts server on port 3000.
3. Page renders Bento grid layout.

## Testing / QA
- Manual QA: Check responsive layout.

## Files touched
- [code/frontend/package.json](code/frontend/package.json)
- [code/frontend/app/layout.tsx](code/frontend/app/layout.tsx)
- [code/frontend/components/BentoGrid.tsx](code/frontend/components/BentoGrid.tsx)
- [code/frontend/app/page.tsx](code/frontend/app/page.tsx)

## Estimated effort
1 dev day

## Concurrency & PR strategy
- Branch: phase-1/step-4-frontend-setup
- Can be parallel with backend steps.

- Blocking steps: .github/artifacts/phase1/plan/type-sync.md
- Merge Readiness: false

## Risks & Mitigations
- Build errors; follow Next.js docs.

## References
- [PDD.md](../PDD.md) — UI/UX Strategy

## Author Checklist
- [x] Purpose filled
- [x] Deliverables listed
- [x] Primary files to change contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable</content>
<parameter name="filePath">/home/manny/Documents/projects/personalDash2026/project/.github/artifacts/phase1/plan/frontend-setup.md