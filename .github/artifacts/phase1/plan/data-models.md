# Step 2 — Data Models

## Purpose
Define Pydantic models for core data entities with camelCase JSON serialization and SQLAlchemy ORM models.

## Deliverables
- code/backend/app/models/task.py: Task model with Pydantic and SQLAlchemy definitions.
- code/backend/app/models/action_log.py: ActionLog model.
- code/backend/app/models/manual_report.py: ManualReport model.
- code/backend/app/models/system_state.py: SystemState model.
- code/backend/app/schemas/__init__.py: Import all schemas.

## Primary files to change
- [code/backend/app/models/task.py](code/backend/app/models/task.py)
- [code/backend/app/models/action_log.py](code/backend/app/models/action_log.py)
- [code/backend/app/models/manual_report.py](code/backend/app/models/manual_report.py)
- [code/backend/app/models/system_state.py](code/backend/app/models/system_state.py)
- [code/backend/app/schemas/__init__.py](code/backend/app/schemas/__init__.py)

## Detailed implementation steps
1. For each model, create Pydantic BaseModel with fields as per PDD.md, using camelCase aliases.
2. Create corresponding SQLAlchemy Table model with snake_case columns.
3. Ensure UUID for ids, DateTime for timestamps.
4. In schemas/__init__.py, import all models for easy access.

## Integration & Edge Cases
- Models must serialize to camelCase for frontend, keep snake_case for DB.
- Use Pydantic v2 features.

## Acceptance Criteria
1. Models validate correctly with sample data.
2. Serialization produces camelCase JSON.
3. SQLAlchemy models can be used to create tables.

## Testing / QA
- Add validation tests in code/backend/tests/test_models.py.
- Manual QA: Instantiate models and check JSON output.

## Files touched
- [code/backend/app/models/task.py](code/backend/app/models/task.py)
- [code/backend/app/models/action_log.py](code/backend/app/models/action_log.py)
- [code/backend/app/models/manual_report.py](code/backend/app/models/manual_report.py)
- [code/backend/app/models/system_state.py](code/backend/app/models/system_state.py)
- [code/backend/app/schemas/__init__.py](code/backend/app/schemas/__init__.py)

## Estimated effort
1 dev day

## Concurrency & PR strategy
- Branch: phase-1/step-2-data-models
- Depends on step 1.

## Risks & Mitigations
- Schema mismatches; validate against PDD.md.

## References
- [PDD.md](../PDD.md) — Data Models section

## Author Checklist
- [x] Purpose filled
- [x] Deliverables listed
- [x] Primary files to change contains workspace-relative links
- [x] Acceptance Criteria are measurable/testable</content>
<parameter name="filePath">/home/manny/Documents/projects/personalDash2026/project/.github/artifacts/phase1/plan/data-models.md