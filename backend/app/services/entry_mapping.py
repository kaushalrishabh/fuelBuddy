from decimal import Decimal

from app.models.fuel_entry import FuelEntry
from app.models.odometer_event import OdometerEvent
from app.services.mileage import FuelRemovedEntry, OdometerEventData, RefuelEntry


def to_refuel_entry(entry: FuelEntry) -> RefuelEntry:
    assert entry.odometer_km is not None
    assert entry.fill_type is not None
    return RefuelEntry(
        id=entry.id,
        date=entry.date,
        odometer_km=entry.odometer_km,
        litres=entry.litres,
        amount_rs=entry.amount_rs or Decimal(0),
        price_per_litre=entry.price_per_litre or Decimal(0),
        fill_type=entry.fill_type,
        odometer_status=entry.odometer_status,
        distance_override_km=entry.distance_override_km,
    )


def to_fuel_removed_entry(entry: FuelEntry) -> FuelRemovedEntry:
    return FuelRemovedEntry(id=entry.id, date=entry.date, litres=entry.litres)


def to_odometer_event_data(event: OdometerEvent) -> OdometerEventData:
    return OdometerEventData(
        event_type=event.event_type,
        start_date=event.start_date,
        end_date=event.end_date,
        old_reading_at_change=event.old_reading_at_change,
        new_reading_at_change=event.new_reading_at_change,
    )
