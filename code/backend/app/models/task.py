from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..schemas.base import CamelModel
from pydantic import Field, field_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase

_ALLOWED_PRIORITIES = {"High", "Medium", "Low"}


def _strip_deadline_tz(v: datetime | None) -> datetime | None:
    """Convert offset-aware deadline to UTC, then drop tzinfo.

    The ``deadline`` column is ``TIMESTAMP WITHOUT TIME ZONE``; asyncpg raises
    a TypeError when it receives an offset-aware datetime.  Normalise here so
    the ORM layer always receives a naive UTC datetime.
    """
    if v is None or v.tzinfo is None:
        return v
    return v.astimezone(timezone.utc).replace(tzinfo=None)


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
    user_id: str | None = None

    model_config = {
        "json_schema_extra": {"example": {"name": "Write docs", "priority": "High"}},
    }


class TaskCreate(CamelModel):
    """Schema for POST /tasks/ — no read-only fields accepted."""
    name: str
    priority: str | None = None
    tags: str | None = None
    is_completed: bool = False
    deadline: datetime | None = None
    notes: str | None = None

    @field_validator("deadline", mode="after")
    @classmethod
    def normalize_deadline(cls, v: datetime | None) -> datetime | None:
        return _strip_deadline_tz(v)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        if len(v) > 256:
            raise ValueError("name must be <= 256 characters")
        return v

    @field_validator("priority")
    @classmethod
    def priority_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in _ALLOWED_PRIORITIES:
            raise ValueError(f"priority must be one of {_ALLOWED_PRIORITIES}")
        return v


class TaskUpdate(CamelModel):
    """Schema for PUT/PATCH requests: excludes read-only fields (id, created_at, updated_at)."""
    name: str | None = None
    priority: str | None = None
    tags: str | None = None
    is_completed: bool | None = None
    deadline: datetime | None = None
    notes: str | None = None

    @field_validator("deadline", mode="after")
    @classmethod
    def normalize_deadline(cls, v: datetime | None) -> datetime | None:
        return _strip_deadline_tz(v)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        if len(v) > 256:
            raise ValueError("name must be <= 256 characters")
        return v

    @field_validator("priority")
    @classmethod
    def priority_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in _ALLOWED_PRIORITIES:
            raise ValueError(f"priority must be one of {_ALLOWED_PRIORITIES}")
        return v


class Task(TimestampedBase):
    __tablename__ = "tasks"

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    priority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
