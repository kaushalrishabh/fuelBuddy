import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.fuel_entry import FuelEntry
    from app.models.odometer_event import OdometerEvent
    from app.models.user import User


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    make: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    purchase_date: Mapped[dt.date | None] = mapped_column(Date)
    tank_capacity_l: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("13.00")
    )
    initial_odometer_km: Mapped[Decimal] = mapped_column(
        Numeric(7, 1), nullable=False, default=Decimal("0.0")
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="vehicles")
    fuel_entries: Mapped[list["FuelEntry"]] = relationship(back_populates="vehicle")
    odometer_events: Mapped[list["OdometerEvent"]] = relationship(back_populates="vehicle")
