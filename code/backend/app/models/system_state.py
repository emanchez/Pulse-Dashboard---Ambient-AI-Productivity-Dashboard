from datetime import datetime

from ..schemas.base import CamelModel
from sqlalchemy import String, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase


class SystemStateSchema(CamelModel):
    id: str | None = None
    mode_type: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    requires_recovery: bool | None = None
    description: str | None = None
    user_id: str | None = None

    # inheritance from CamelModel provides alias_generator and populate_by_name


class SystemState(TimestampedBase):
    __tablename__ = "system_states"

    mode_type: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    requires_recovery: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
