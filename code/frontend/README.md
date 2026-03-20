# Pulse Dashboard — Frontend

Next.js 14 (App Router) frontend for the Ambient AI Productivity Dashboard. Features a dark-themed bento-grid layout with real-time productivity telemetry, task management, manual reports, system state (vacation/leave) management, and AI-powered weekly synthesis.

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript (strict mode)
- **Styling:** Tailwind CSS 3.4 + `@tailwindcss/forms`
- **Charts:** Recharts
- **Icons:** Lucide React
- **Type Sync:** `@hey-api/openapi-ts` — auto-generates TypeScript clients from the backend OpenAPI spec

## Pages & Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | — | Redirects to `/tasks` |
| `/login` | Login | Username/password form → JWT stored in localStorage |
| `/tasks` | Dashboard | Bento-grid main view — focus header, pulse card, sessions, daily goals, task table, AI reasoning sidebar |
| `/reports` | Reports | CRUD for manual "brain dump" reports with task linking + system state management |
| `/synthesis` | Synthesis | AI-generated weekly narrative, commitment gauge, task suggestions with accept/dismiss |

## Directory Structure

```
app/                         # Next.js pages (App Router)
├── layout.tsx               # Root layout (dark theme, SilenceStateProvider)
├── page.tsx                 # Redirect → /tasks
├── login/page.tsx           # Login form
├── tasks/page.tsx           # Main dashboard (bento grid)
├── reports/page.tsx         # Reports + system state management
└── synthesis/page.tsx       # AI synthesis + suggestions
components/
├── BentoGrid.tsx            # Responsive grid layout (mobile-first)
├── SilenceStateProvider.tsx # React context for silence/engagement state
├── dashboard/
│   ├── FocusHeader.tsx      # Silence indicator + engagement badge
│   ├── ProductivityPulseCard.tsx  # Flow state metrics
│   ├── CurrentSessionCard.tsx     # Active focus session controls
│   ├── DailyGoalsCard.tsx         # Daily task completion progress
│   ├── QuickAccessCard.tsx        # Quick actions panel
│   ├── TaskQueueTable.tsx         # Full task list with inline editing
│   ├── ReasoningSidebar.tsx       # AI reasoning panel
│   ├── GhostListPanel.tsx         # Wheel-spinning task detection
│   ├── InferenceCard.tsx          # AI inference result display
│   └── ReEntryBanner.tsx          # Post-vacation re-entry mode banner
├── nav/
│   └── AppNavBar.tsx        # Top nav (tabs, silence badge, logout)
├── reports/
│   ├── ReportCard.tsx       # Single report display
│   ├── ReportForm.tsx       # Report create/edit modal
│   └── ReportList.tsx       # Paginated report list
├── synthesis/
│   ├── SynthesisTrigger.tsx # Button to trigger AI synthesis
│   ├── SynthesisCard.tsx    # Weekly synthesis display
│   ├── CommitmentGauge.tsx  # Commitment score visualization
│   └── TaskSuggestionList.tsx # AI-suggested tasks with accept/dismiss
├── system-state/
│   ├── SystemStateCard.tsx  # Single state display
│   ├── SystemStateForm.tsx  # State create/edit form
│   └── SystemStateManager.tsx # System state list + CRUD
└── tasks/
    └── TaskForm.tsx         # Task create/edit modal
lib/
├── api.ts                   # API client (fetch wrapper, auth headers, type exports)
├── generate-client.sh       # OpenAPI TypeScript client generator script
├── generated/               # Auto-generated types + client (do not edit)
│   ├── types.gen.ts         # Generated Pydantic → TypeScript types
│   ├── pulseClient.ts       # Generated pulse/stats client
│   └── index.ts             # Barrel export
└── hooks/
    └── useAuth.ts           # JWT auth hook (localStorage, /me validation, auto-redirect)
```

## Quick Start

### Prerequisites

- Node.js 20.x
- npm 8+
- Backend running on `http://localhost:8000` (see backend README)

### Install & Run

```bash
# Install dependencies
make deps     # or: npm ci

# Start dev server
make dev      # or: npm run dev
```

Frontend will be available at **http://localhost:3000**.

### From the Project Root

```bash
# Start both backend + frontend:
make dev

# Stop both:
make stop
```

## Makefile Reference

| Command | Description |
|---------|-------------|
| `make deps` | `npm ci` |
| `make dev` | `npm run dev` (foreground) |
| `make start-dev` | Start in background (PID saved to `.dev.pid`) |
| `make stop` | Stop background server, clear `.next` cache |
| `make build` | `npm run build` (production) |
| `make generate-api` | Regenerate TypeScript client from OpenAPI spec |
| `make clean-cache` | Clear `.next` build cache |

## Auth Flow

1. App boots → `useAuth` hook reads `pulse_token` from `localStorage`.
2. Validates token against `GET /me` on the backend.
3. Invalid/expired → clears token, redirects to `/login`.
4. User submits credentials → `POST /login` → receives JWT → stores in localStorage → redirects to `/tasks`.
5. All API calls include `Authorization: Bearer <token>`. On 401, `logout()` clears state and redirects.

> **Note:** Token is stored in `localStorage` (XSS risk). Migration to httpOnly cookies is planned for production deployment.

## Regenerating the API Client

Run whenever backend schemas or endpoints change:

```bash
# 1. Ensure the backend is running
cd code/backend && make start

# 2. Regenerate the client
cd code/frontend
npm run generate:api     # or: make generate-api

# 3. Commit the updated stubs
git add lib/generated
git commit -m "chore(frontend): regenerate API client"
```

The generator reads `http://localhost:8000/openapi.json` and writes to `lib/generated/`. These files are **canonical** — do not edit by hand. `lib/api.ts` re-exports them so components import from a single stable path.

> **CI note:** CI runs `npm run generate:api` before `npm run build`. If the backend contract changes and stubs aren't updated, the build fails as a safety gate.

## UI Patterns

### Bento Grid Layout

The dashboard uses a responsive "bento box" grid system (`BentoGrid.tsx`). Zones are arranged mobile-first with responsive breakpoints (`md:col-span-2`, etc.).

### Deferred Save (Tasks)

Task edits are stored in an in-memory `Map<id, Partial<Task>>` — no API call until the user clicks **Save changes**. Unsaved rows show an amber pill. Browser refresh discards pending edits by design. This keeps the ActionLog clean (one entry per intentional commit).

### Priority Colors

| Priority | Border | Background | Text |
|----------|--------|------------|------|
| **High** | Rose | `bg-rose-50` | `text-rose-600` |
| **Medium** | Amber | `bg-amber-50` | `text-amber-700` |
| **Low** | Sky Blue | `bg-sky-50` | `text-sky-700` |
| *(none)* | Gray | `bg-white` | `text-gray-600` |

### Silence Indicator

The `FocusHeader` displays real-time engagement state via `GET /stats/pulse` (polled every 30s):

| State | Badge | Meaning |
|-------|-------|---------|
| `engaged` | Emerald | Last action ≤ 48 hours ago, no active pause |
| `stagnant` | Amber | No action for > 48 hours, no active pause |
| `paused` | Sky Blue | Active vacation/leave system state (overrides stagnant) |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000` | Backend API base URL |

## Development Notes

- **Dark theme** is the default (`bg-slate-950 text-white`).
- **No frontend test runner** is configured yet. Add Vitest or Jest to enable `make test`.
- The TypeScript compiler runs with `"strict": true`.
- Generated types in `lib/generated/` are committed to the repo to avoid blocking frontend work when the backend isn't running.
