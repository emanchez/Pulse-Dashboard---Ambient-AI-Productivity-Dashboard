# Phase 4 Summary — Steps 5 & 6 (Ghost List + Synthesis UI)

## Scope
This summary covers the implementation of **Step 5 (Ghost List & Analytics Optimization)** and **Step 6 (Sunday Synthesis UI)**.

## Key Deliverables Implemented

### Step 5 — Ghost List & Analytics
- Implemented **ghost list** backend logic to detect stale/wheel-spinning tasks based on task age and action activity.
- Added **weekly summary** endpoint (Mon–Sun) aggregating actions, tasks, reports, sessions, and silence gaps.
- Added **composite indexes** for `action_logs(user_id, timestamp)` and `session_logs(user_id, ended_at)`.
- Optimized **flow-state** calculation to use SQL aggregation instead of pulling all timestamps into Python.
- Added migration script to create indices idempotently.
- Added comprehensive tests (`test_ghost_list.py`) covering ghost list conditions, weekly summary, and flow-state response shape.

### Step 6 — Sunday Synthesis UI
- Added `/synthesis` page and components:
  - `SynthesisCard` (summary, theme, commitment score)
  - `CommitmentGauge` (accessible meter UI)
  - `TaskSuggestionList` (accept/dismiss, re-entry mode)
  - `SynthesisTrigger` (trigger button, loading + rate-limit state)
- Added API wrappers for AI endpoints, including usage and ghost-list endpoints.
- Added `Synthesis` nav tab to the main `AppNavBar`.
- Verified frontend build success (`npm run build`).

## Verification
- Backend tests: `pytest tests/test_ghost_list.py tests/test_stats.py` pass.
- Full backend suite: passes (with pre-existing login fixture warnings/errors unrelated to these steps).
- Frontend build passes and includes `/synthesis` route.

---

## Notes
- The ghost list service uses a 14-day stale threshold and considers low activity (<2 actions) or high edit churn (>5 actions).
- Weekly summary uses simple SQL counts and a minimal Python gap calculation.
- The frontend uses the existing design tokens and `data-state` theming patterns (engaged/stagnant/paused).
