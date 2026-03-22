"""AIUsageLog — persists every AI API call for rate limiting and spend tracking.

Records are inserted ONLY after a real, successful LLM parse completes.
Mock-mode calls and failed calls MUST NOT produce entries — this ensures
rate-limit caps are never consumed by non-billable events.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase


class AIUsageLog(TimestampedBase):
    __tablename__ = "ai_usage_logs"
    __table_args__ = (
        Index("ix_ai_usage_user_endpoint_ts", "user_id", "endpoint", "timestamp"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(50), nullable=False)  # "synthesis" | "suggest" | "coplan"
    llm_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_chars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    was_mocked: Mapped[bool] = mapped_column(Boolean, default=False)
    # ISO-week bucket for weekly grouping, e.g. "2026-W11"
    week_number: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    # Day bucket for daily grouping, e.g. "2026-03-14"
    day: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
