from __future__ import annotations

from datetime import datetime
from typing import List

from ..schemas.base import CamelModel
from pydantic import Field
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase


def _to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class TaskSchema(CamelModel):
    id: str | None = None
    name: str
    priority: str | None = None
    tags: str | None = None
    is_completed: bool = Field(False)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deadline: datetime | None = None
    notes: str | None = None

    model_config = {
        "alias_generator": _to_camel,
        "populate_by_name": True,
        "json_schema_extra": {"example": {"name": "Write docs", "priority": "High"}},
    }


class TaskUpdate(CamelModel):
    """Schema for PUT/PATCH requests: excludes read-only fields (id, created_at, updated_at)."""
    name: str
    priority: str | None = None
    tags: str | None = None
    is_completed: bool = Field(False)
    deadline: datetime | None = None
    notes: str | None = None

    model_config = {
        "alias_generator": _to_camel,
        "populate_by_name": True,
    }


class Task(TimestampedBase):
    __tablename__ = "tasks"

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    priority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
