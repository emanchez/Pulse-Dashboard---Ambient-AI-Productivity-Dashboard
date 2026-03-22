"""SynthesisReport — stores AI-generated weekly synthesis narratives.

Each row is one LLM inference run that analyzed the user's ambient data and
produced a narrative, theme, commitment score, and suggested tasks.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase


class SynthesisReport(TimestampedBase):
    __tablename__ = "synthesis_reports"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    theme: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    commitment_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suggested_tasks: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array
    llm_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending | completed | failed
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
