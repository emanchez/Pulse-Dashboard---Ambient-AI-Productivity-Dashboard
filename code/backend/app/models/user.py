from __future__ import annotations

from datetime import datetime

from ..schemas.base import CamelModel
from pydantic import Field
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import TimestampedBase


class UserSchema(CamelModel):
    id: str | None = None
    username: str
    is_active: bool = Field(True)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # inheritance from CamelModel provides alias_generator and populate_by_name


class User(TimestampedBase):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
