from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import EntryType, FillType
from app.models.fuel_entry import FuelEntry
from app.models.odometer_event import OdometerEvent
from app.models.vehicle import Vehicle
from app.services.entry_mapping import (
    to_fuel_removed_entry,
    to_odometer_event_data,
    to_refuel_entry,
)
from app.services.mileage import ValidationWarning, compute_fill_preview, validate_new_refuel


def build_refuel_feedback(
    db: Session, vehicle: Vehicle, entry: FuelEntry
) -> tuple[list[ValidationWarning], dict[str, Decimal | None]]:
    """Non-blocking warnings and a fill preview for a just-saved refuel entry."""
    all_refuels = (
        db.query(FuelEntry)
        .filter(FuelEntry.vehicle_id == vehicle.id, FuelEntry.entry_type == EntryType.REFUEL)
        .order_by(FuelEntry.date, FuelEntry.odometer_km)
        .all()
    )
    all_removed = (
        db.query(FuelEntry)
        .filter(FuelEntry.vehicle_id == vehicle.id, FuelEntry.entry_type == EntryType.FUEL_REMOVED)
        .all()
    )
    odometer_event_data = [
        to_odometer_event_data(e)
        for e in db.query(OdometerEvent).filter(OdometerEvent.vehicle_id == vehicle.id).all()
    ]

    prior_refuels = [
        e
        for e in all_refuels
        if e.id != entry.id and (e.date, e.odometer_km) < (entry.date, entry.odometer_km)
    ]
    previous_entry = prior_refuels[-1] if prior_refuels else None

    prior_full_fills = [e for e in prior_refuels if e.fill_type == FillType.FULL]
    previous_full_entry = prior_full_fills[-1] if prior_full_fills else None

    interior_partials: list[FuelEntry] = []
    removed_in_window: list[FuelEntry] = []
    if previous_full_entry is not None:
        interior_partials = [
            e
            for e in all_refuels
            if e.fill_type == FillType.PARTIAL
            and e.id not in (previous_full_entry.id, entry.id)
            and previous_full_entry.date <= e.date <= entry.date
        ]
        removed_in_window = [
            r for r in all_removed if previous_full_entry.date < r.date <= entry.date
        ]

    warnings = validate_new_refuel(
        to_refuel_entry(entry),
        to_refuel_entry(previous_entry) if previous_entry else None,
        vehicle.tank_capacity_l,
        odometer_event_data,
    )
    preview = compute_fill_preview(
        to_refuel_entry(entry),
        to_refuel_entry(previous_full_entry) if previous_full_entry else None,
        [to_refuel_entry(p) for p in interior_partials],
        [to_fuel_removed_entry(r) for r in removed_in_window],
        odometer_event_data,
    )
    return warnings, preview
