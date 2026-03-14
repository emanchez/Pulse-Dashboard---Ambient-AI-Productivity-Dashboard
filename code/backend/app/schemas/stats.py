from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import CamelModel


class PulseStatsSchema(CamelModel):
    silence_state: Literal["paused", "stagnant", "engaged"] = Field(alias="silenceState")
    last_action_at: datetime | None = Field(alias="lastActionAt")
    gap_minutes: int = Field(alias="gapMinutes")
    paused_until: datetime | None = Field(alias="pausedUntil")

    model_config = {
        "json_schema_extra": {
            "description": "Pulse telemetry reporting silence state. Paused overrides stagnant gaps >48h. Engaged if gap <=48h and no active pause."
        }
    }


# ---------------------------------------------------------------------------
#  Step 5 — Ghost List & Weekly Summary
# ---------------------------------------------------------------------------

class GhostTask(CamelModel):
    id: str
    name: str
    priority: str
    days_open: int
    action_count: int
    last_action_at: datetime | None
    ghost_reason: str  # "stale" | "wheel-spinning"


class GhostListResponse(CamelModel):
    ghosts: list[GhostTask]
    total: int


class WeeklySummaryResponse(CamelModel):
    total_actions: int
    tasks_completed: int
    tasks_created: int
    reports_written: int
    sessions_completed: int
    longest_silence_hours: float
    active_days: int
    period_start: datetime
    period_end: datetime