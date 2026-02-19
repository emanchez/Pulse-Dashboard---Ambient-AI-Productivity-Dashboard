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