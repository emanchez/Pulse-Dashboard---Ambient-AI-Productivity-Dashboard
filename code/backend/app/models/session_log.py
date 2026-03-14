from __future__ import annotations

from datetime import datetime, timezone

from pydantic import ConfigDict
from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase
from ..schemas.base import CamelModel


class SessionLog(TimestampedBase):
    __tablename__ = "session_logs"
    __table_args__ = (
        Index('ix_session_logs_user_ended', 'user_id', 'ended_at'),
    )

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    task_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    goal_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def elapsed_minutes(self) -> int:
        end = self.ended_at if self.ended_at is not None else datetime.now(timezone.utc).replace(tzinfo=None)
        return int((end - self.started_at).total_seconds() // 60)


class SessionStartRequest(CamelModel):
    task_id: str | None = None
    task_name: str
    goal_minutes: int | None = None


class SessionLogSchema(CamelModel):
    id: str | None = None
    user_id: str | None = None
    task_id: str | None = None
    task_name: str | None = None
    goal_minutes: int | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    elapsed_minutes: int | None = None

    model_config = ConfigDict(from_attributes=True)
