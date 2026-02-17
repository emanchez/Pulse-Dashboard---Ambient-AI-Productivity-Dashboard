from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import String, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase


def _to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class SystemStateSchema(BaseModel):
    id: str | None = None
    mode_type: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    requires_recovery: bool | None = None
    description: str | None = None

    model_config = {"alias_generator": _to_camel, "populate_by_name": True}


class SystemState(TimestampedBase):
    __tablename__ = "system_states"

    mode_type: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    requires_recovery: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
