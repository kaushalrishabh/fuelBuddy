import datetime as dt
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EntryAudit(Base):
    __tablename__ = "entry_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    fuel_entry_id: Mapped[int] = mapped_column(
        ForeignKey("fuel_entries.id"), nullable=False, index=True
    )
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    old_values: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    new_values: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    changed_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
