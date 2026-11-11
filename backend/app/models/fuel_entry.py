import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import EntrySource, EntryType, FillType, OdometerStatus, enum_values

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle


class FuelEntry(Base):
    __tablename__ = "fuel_entries"
    __table_args__ = (
        UniqueConstraint(
            "vehicle_id", "entry_type", "date", "odometer_km", name="uq_fuel_entry_dedupe"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    entry_type: Mapped[EntryType] = mapped_column(
        SAEnum(EntryType, native_enum=False, length=20, values_callable=enum_values), nullable=False
    )
    date: Mapped[dt.date] = mapped_column(Date, nullable=False, index=True)

    odometer_km: Mapped[Decimal | None] = mapped_column(Numeric(7, 1))
    litres: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    amount_rs: Mapped[Decimal | None] = mapped_column(Numeric(9, 2))
    price_per_litre: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    fill_type: Mapped[FillType | None] = mapped_column(
        SAEnum(FillType, native_enum=False, length=10, values_callable=enum_values)
    )
    location: Mapped[str | None] = mapped_column(String(100), index=True)
    station_name: Mapped[str | None] = mapped_column(String(150))

    notes: Mapped[str | None] = mapped_column(Text)
    odometer_status: Mapped[OdometerStatus] = mapped_column(
        SAEnum(OdometerStatus, native_enum=False, length=10, values_callable=enum_values),
        nullable=False,
        default=OdometerStatus.OK,
    )
    distance_override_km: Mapped[Decimal | None] = mapped_column(Numeric(7, 1))
    source: Mapped[EntrySource] = mapped_column(
        SAEnum(EntrySource, native_enum=False, length=20, values_callable=enum_values),
        nullable=False,
        default=EntrySource.MANUAL,
    )
    raw_text: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    vehicle: Mapped["Vehicle"] = relationship(back_populates="fuel_entries")
