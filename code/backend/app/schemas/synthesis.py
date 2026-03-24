"""Pydantic schemas for Sunday Synthesis, Task Suggester, and Co-Planning.

Covers Steps 3 and 4 of Phase 4.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import field_validator

from ..schemas.base import CamelModel


# ---------------------------------------------------------------------------
#  Step 3 — Sunday Synthesis
# ---------------------------------------------------------------------------

class SynthesisCreate(CamelModel):
    """Trigger a new synthesis. No body required — uses last 7 days."""
    period_days: int = 7


class SuggestedTask(CamelModel):
    name: str
    priority: str  # Low | Medium | High
    rationale: str  # why the AI suggests this task
    is_low_friction: bool = False  # True for re-entry mode suggestions

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v: object) -> object:
        """Normalize LLM-returned priority to Title Case (e.g. 'high' → 'High')."""
        if isinstance(v, str):
            return v.strip().title()
        return v


class SynthesisResponse(CamelModel):
    id: str
    summary: str
    theme: str
    commitment_score: int
    suggested_tasks: list[SuggestedTask]
    status: str
    period_start: datetime
    period_end: datetime
    created_at: datetime


class SynthesisStatusResponse(CamelModel):
    id: str
    status: str  # pending | completed | failed
    llm_run_id: str | None = None


# ---------------------------------------------------------------------------
#  Step 4 — Task Suggester
# ---------------------------------------------------------------------------

class TaskSuggestionRequest(CamelModel):
    """Optional context override for task suggestions."""
    focus_area: str | None = None  # e.g., "backend", "frontend", "documentation"


class TaskSuggestionResponse(CamelModel):
    suggestions: list[SuggestedTask]
    is_re_entry_mode: bool  # True if suggestions are biased toward low-friction tasks
    rationale: str  # why these tasks were suggested


# ---------------------------------------------------------------------------
#  Step 4 — Co-Planning (Ambiguity Guard)
# ---------------------------------------------------------------------------

class CoPlanRequest(CamelModel):
    report_id: str  # ID of the ManualReport to analyze


class CoPlanResponse(CamelModel):
    has_conflict: bool
    conflict_description: str | None = None
    resolution_question: str | None = None
    suggested_priority: str | None = None


# ---------------------------------------------------------------------------
#  Step 4 — Accept AI-suggested tasks
# ---------------------------------------------------------------------------

class AcceptedTask(CamelModel):
    name: str
    priority: str = "Medium"
    notes: str | None = None

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v: object) -> object:
        """Normalize priority to Title Case so stored tasks always use canonical casing."""
        if isinstance(v, str):
            return v.strip().title()
        return v


class AcceptTasksRequest(CamelModel):
    tasks: list[AcceptedTask]
