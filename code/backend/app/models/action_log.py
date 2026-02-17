from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase


def _to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class ActionLogSchema(BaseModel):
    id: str | None = None
    timestamp: datetime | None = None
    task_id: str | None = None
    action_type: str | None = None
    change_summary: str | None = None

    model_config = {"alias_generator": _to_camel, "populate_by_name": True}


class ActionLog(TimestampedBase):
    __tablename__ = "action_logs"

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
