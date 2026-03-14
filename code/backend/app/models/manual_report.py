from datetime import datetime
from typing import List

import bleach

from ..schemas.base import CamelModel, _to_camel
from pydantic import ConfigDict, field_validator
from sqlalchemy import Integer, Text, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase

# Canonical set of allowed report statuses. Used by Create/Update validators.
REPORT_STATUSES = {"draft", "published", "archived"}


class ManualReportSchema(CamelModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    id: str | None = None
    title: str
    body: str
    word_count: int | None = None
    associated_task_ids: List[str] | None = None
    status: str | None = None
    tags: List[str] | None = None
    user_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ManualReportCreate(CamelModel):
    title: str
    body: str
    associated_task_ids: List[str] | None = None
    tags: List[str] | None = None
    status: str = "published"

    @field_validator("title", "body", mode="before")
    @classmethod
    def strip_html(cls, v: object) -> object:
        """Strip all HTML tags from title and body to prevent stored XSS."""
        if isinstance(v, str):
            return bleach.clean(v, tags=[], strip=True)
        return v

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        if len(v) > 256:
            raise ValueError("title must be <= 256 characters")
        return v

    @field_validator("body")
    @classmethod
    def body_max_length(cls, v: str) -> str:
        if len(v) > 50_000:
            raise ValueError("body must be <= 50,000 characters")
        return v

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        if v not in REPORT_STATUSES:
            raise ValueError(f"status must be one of {REPORT_STATUSES}")
        return v


class ManualReportUpdate(CamelModel):
    title: str | None = None
    body: str | None = None
    associated_task_ids: List[str] | None = None
    tags: List[str] | None = None
    status: str | None = None

    @field_validator("title", "body", mode="before")
    @classmethod
    def strip_html(cls, v: object) -> object:
        """Strip all HTML tags from title and body to prevent stored XSS."""
        if isinstance(v, str):
            return bleach.clean(v, tags=[], strip=True)
        return v

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        if len(v) > 256:
            raise ValueError("title must be <= 256 characters")
        return v

    @field_validator("body")
    @classmethod
    def body_max_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 50_000:
            raise ValueError("body must be <= 50,000 characters")
        return v

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in REPORT_STATUSES:
            raise ValueError(f"status must be one of {REPORT_STATUSES}")
        return v


class PaginatedReportsResponse(CamelModel):
    items: List[ManualReportSchema]
    total: int
    offset: int
    limit: int


class ManualReport(TimestampedBase):
    __tablename__ = "manual_reports"

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    associated_task_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published")
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
