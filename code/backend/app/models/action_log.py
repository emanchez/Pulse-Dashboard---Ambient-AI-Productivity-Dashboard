from __future__ import annotations

from datetime import datetime, timezone

from ..schemas.base import CamelModel
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase


# Auth action types — excluded from pulse/flow activity calculations so that
# login events do not reset the silence gap or inflate flow-state buckets.
AUTH_ACTION_TYPES = ("LOGIN_SUCCESS", "LOGIN_FAILED")


class ActionLogSchema(CamelModel):
    id: str | None = None
    timestamp: datetime | None = None
    task_id: str | None = None
    action_type: str | None = None
    change_summary: str | None = None
    user_id: str | None = None
    client_host: str | None = None

    # inheritance from CamelModel provides alias_generator and populate_by_name


class ActionLog(TimestampedBase):
    __tablename__ = "action_logs"
    __table_args__ = (
        Index('ix_action_logs_user_ts', 'user_id', 'timestamp'),
    )

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=True)
    action_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    client_host: Mapped[str | None] = mapped_column(String(45), nullable=True)
