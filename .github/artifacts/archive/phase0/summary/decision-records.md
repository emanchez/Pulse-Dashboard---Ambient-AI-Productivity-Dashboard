# Phase‑0 Decision Records (ADRs)

## ADR: Ollama Inference Posture
- status: proposed
- owner: TBD
- date: 2026-02-17

Decision: Use Ollama for local-first LLM inference. No external cloud LLM APIs will be used for inference.

Context: Privacy, cost control, and offline-first operation for a single-user product.

Alternatives: Use hosted APIs (OpenAI, Anthropic) — rejected due to cost/privacy constraints.

Consequences: Requires local inference runtime (CPU-first; optional GPU for performance). Must include local install/run docs and fallback behavior when Ollama is unavailable.

Acceptance:
- Include local run commands in docs and a fallback behavior documented in `architecture.md`.
- CI/checks must not reference external LLM APIs.

---

## ADR: Auth Approach — Phase‑0 JWT (Single-User)
- status: proposed
- owner: TBD
- date: 2026-02-17

Decision: For Phase‑0, use a single-user JWT authentication model. `/login` and `/health` remain unauthenticated; all other endpoints require a JWT that contains `user_id`.

Context: Single-user MVP; future migration to OAuth providers planned.

Alternatives: Full OAuth/OIDC — deferred to future phases.

Consequences: All API endpoints (except `/login` and `/health`) must validate JWT and extract `user_id`. Use `user_id` for scoping data access.

Acceptance:
- Code and API docs include JWT requirement for endpoints.
- Step-1 ADR and Step-2 policy reference `Auth First` requirement explicitly.

---

## ADR: Data Retention & Backups
- status: proposed
- owner: TBD
- date: 2026-02-17

Decision: Persist primary data in SQLite for Phase‑0. ActionLog entries retained for 90 days by default. Provide export/import and pre-merge backup steps for any migration.

Context: Local-first, small dataset expected for a personal dashboard.

Alternatives: Use Postgres immediately — deferred to production.

Consequences: Provide backup/restore documentation and scheduled compaction/archival processes.

Acceptance:
- Include backup commands and rollback procedure in any step that modifies persistence.
- Add database export instructions (SQLite `.dump`) in `retention.md`.

---

## ADR: CI/CD & Hosting Defaults
- status: proposed
- owner: TBD
- date: 2026-02-17

Decision: Use GitHub Actions for Phase‑0 CI. Deploy to a manual VPS/host via SSH for ad-hoc testing; no automated production deploys in Phase‑0.

Acceptance:
- Add `project/.github/workflows/phase0-smoke.yml` that validates lint/test-discovery and uploads a `phase0-smoke.json` artifact.

---

## ADR: Budget Bounds
- status: proposed
- owner: TBD
- date: 2026-02-17

Decision: Phase‑0 runs on $0–$50 monthly budget. Escalation triggers documented in `budget.md`.

Acceptance:
- `budget.md` exists and lists triggers and contact/owner.
