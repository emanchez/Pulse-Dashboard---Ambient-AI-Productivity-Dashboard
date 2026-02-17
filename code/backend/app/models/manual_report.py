from datetime import datetime
from typing import List

from pydantic import BaseModel, Field
from sqlalchemy import Integer, Text, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase


def _to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class ManualReportSchema(BaseModel):
    id: str | None = None
    title: str
    body: str
    word_count: int | None = None
    associated_task_ids: List[str] | None = None
    created_at: datetime | None = None

    model_config = {"alias_generator": _to_camel, "populate_by_name": True}


class ManualReport(TimestampedBase):
    __tablename__ = "manual_reports"

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    associated_task_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
