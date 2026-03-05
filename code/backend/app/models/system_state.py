from datetime import datetime

from ..schemas.base import CamelModel, _to_camel
from pydantic import ConfigDict, field_validator, model_validator
from sqlalchemy import String, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase


class SystemStateSchema(CamelModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    id: str | None = None
    mode_type: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    requires_recovery: bool | None = None
    description: str | None = None
    user_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SystemStateCreate(CamelModel):
    mode_type: str
    start_date: datetime
    end_date: datetime | None = None
    requires_recovery: bool = True
    description: str | None = None

    @field_validator("mode_type")
    @classmethod
    def mode_type_valid(cls, v: str) -> str:
        normalized = v.strip().lower()
        if normalized not in {"vacation", "leave"}:
            raise ValueError("mode_type must be 'vacation' or 'leave'")
        return normalized

    @model_validator(mode="after")
    def end_after_start(self) -> "SystemStateCreate":
        if self.end_date is not None and self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class SystemStateUpdate(CamelModel):
    mode_type: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    requires_recovery: bool | None = None
    description: str | None = None

    @field_validator("mode_type")
    @classmethod
    def mode_type_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        normalized = v.strip().lower()
        if normalized not in {"vacation", "leave"}:
            raise ValueError("mode_type must be 'vacation' or 'leave'")
        return normalized

    @model_validator(mode="after")
    def end_after_start(self) -> "SystemStateUpdate":
        if self.start_date is not None and self.end_date is not None:
            if self.end_date <= self.start_date:
                raise ValueError("end_date must be after start_date")
        return self


class SystemState(TimestampedBase):
    __tablename__ = "system_states"

    mode_type: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    requires_recovery: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
