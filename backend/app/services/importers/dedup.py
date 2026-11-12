"""Duplicate detection for import previews.

The DB's unique constraint (vehicle_id, entry_type, date, odometer_km) only
catches fuel_removed rows that recorded an odometer reading -- MySQL treats
NULL as distinct in unique indexes. For removals without an odometer, we
fall back to a soft match on (date, litres) here instead of a hard
constraint, surfaced as a warning the user can override.

This also catches duplicates *within* the batch being imported, not just
against what's already in the DB, by seeding the "seen" sets from existing
entries and then adding each row's key as it's processed.
"""

import datetime as dt
from collections.abc import Sequence
from decimal import Decimal

from app.models.enums import EntryType
from app.models.fuel_entry import FuelEntry
from app.services.importers.parsed_row import ParsedRow

ExactKey = tuple[EntryType, dt.date, Decimal]
RemovalKey = tuple[dt.date, Decimal]


def mark_duplicates(rows: Sequence[ParsedRow], existing_entries: Sequence[FuelEntry]) -> None:
    seen_exact: set[ExactKey] = {
        (e.entry_type, e.date, e.odometer_km) for e in existing_entries if e.odometer_km is not None
    }
    seen_removal: set[RemovalKey] = {
        (e.date, e.litres)
        for e in existing_entries
        if e.entry_type == EntryType.FUEL_REMOVED and e.odometer_km is None
    }

    for row in rows:
        if row.date is None or row.entry_type is None:
            continue

        if row.odometer_km is not None:
            exact_key: ExactKey = (row.entry_type, row.date, row.odometer_km)
            if exact_key in seen_exact:
                row.is_duplicate = True
                row.warnings.append(
                    "Possible duplicate: an entry already exists for this date/odometer"
                )
            seen_exact.add(exact_key)
        elif row.entry_type == EntryType.FUEL_REMOVED and row.litres is not None:
            removal_key: RemovalKey = (row.date, row.litres)
            if removal_key in seen_removal:
                row.is_duplicate = True
                row.warnings.append(
                    "Possible duplicate: a removal already exists for this date/litres"
                )
            seen_removal.add(removal_key)
