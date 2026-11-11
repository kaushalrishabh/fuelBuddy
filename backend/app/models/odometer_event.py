import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import OdometerEventType, enum_values

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle


class OdometerEvent(Base):
    __tablename__ = "odometer_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    event_type: Mapped[OdometerEventType] = mapped_column(
        SAEnum(OdometerEventType, native_enum=False, length=20, values_callable=enum_values),
        nullable=False,
    )
    start_date: Mapped[dt.date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[dt.date | None] = mapped_column(Date)
    old_reading_at_change: Mapped[Decimal | None] = mapped_column(Numeric(7, 1))
    new_reading_at_change: Mapped[Decimal | None] = mapped_column(Numeric(7, 1))
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    vehicle: Mapped["Vehicle"] = relationship(back_populates="odometer_events")
