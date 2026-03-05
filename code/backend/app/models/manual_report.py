from datetime import datetime
from typing import List

from ..schemas.base import CamelModel
from pydantic import Field
from sqlalchemy import Integer, Text, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase


class ManualReportSchema(CamelModel):
    id: str | None = None
    title: str
    body: str
    word_count: int | None = None
    associated_task_ids: List[str] | None = None
    created_at: datetime | None = None

    # inheritance from CamelModel provides alias_generator and populate_by_name


class ManualReport(TimestampedBase):
    __tablename__ = "manual_reports"

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    associated_task_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
