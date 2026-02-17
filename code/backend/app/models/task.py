from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase


def _to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])


class TaskSchema(BaseModel):
    id: str | None = None
    name: str
    priority: str | None = None
    tags: str | None = None
    is_completed: bool = Field(False, alias="isCompleted")
    date_created: datetime | None = Field(None, alias="dateCreated")
    date_updated: datetime | None = Field(None, alias="dateUpdated")
    deadline: datetime | None = None
    notes: str | None = None

    model_config = {
        "alias_generator": _to_camel,
        "populate_by_name": True,
        "json_schema_extra": {"example": {"name": "Write docs", "priority": "High"}},
    }


class Task(TimestampedBase):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    priority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
