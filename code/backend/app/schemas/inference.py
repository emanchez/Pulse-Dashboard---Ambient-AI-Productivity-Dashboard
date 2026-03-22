"""Pydantic models for the inference context structure.

These schemas define the shape of data assembled by InferenceContextBuilder
and injected into LLM prompts by PromptBuilder.
"""

from __future__ import annotations

from datetime import datetime

from .base import CamelModel


class TaskSummary(CamelModel):
    id: str
    name: str
    priority: str | None
    is_completed: bool
    days_open: int
    action_count: int  # number of ActionLog entries for this task
    last_action_at: datetime | None


class SilenceGap(CamelModel):
    start: datetime
    end: datetime
    duration_hours: float
    explained: bool  # True if a ManualReport exists within the gap
    explanation: str | None  # Report title if explained


class ReportSummary(CamelModel):
    id: str
    title: str
    body_preview: str  # first 200 chars
    word_count: int
    associated_task_ids: list[str]
    created_at: datetime


class SystemStateSummary(CamelModel):
    mode_type: str
    start_date: datetime
    end_date: datetime | None
    requires_recovery: bool
    is_active: bool


class WeeklySummary(CamelModel):
    total_actions: int
    tasks_completed: int
    tasks_created: int
    reports_written: int
    longest_silence_hours: float
    active_days: int  # days with at least 1 action


class InferenceContext(CamelModel):
    """Complete context payload for LLM prompt injection."""

    period_start: datetime
    period_end: datetime
    tasks: list[TaskSummary]
    completed_tasks: list[TaskSummary]
    open_tasks: list[TaskSummary]
    silence_gaps: list[SilenceGap]
    reports: list[ReportSummary]
    system_state: SystemStateSummary | None
    weekly_summary: WeeklySummary
    is_returning_from_leave: bool  # True if a SystemState with requiresRecovery ended in the last 48h
