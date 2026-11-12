from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.fuel_entry import FuelEntry
from app.services.importers.parsed_row import ParsedRow


@dataclass(frozen=True)
class ImportResult:
    imported: int
    skipped_duplicates: int
    skipped_errors: int


def commit_rows(
    db: Session, vehicle_id: int, rows: Sequence[ParsedRow], skip_duplicates: bool = True
) -> ImportResult:
    """Inserts every importable row in one transaction. Rows with errors are
    always skipped; duplicates are skipped unless the caller opts in."""
    imported = skipped_duplicates = skipped_errors = 0

    for row in rows:
        if row.errors:
            skipped_errors += 1
            continue
        if row.is_duplicate and skip_duplicates:
            skipped_duplicates += 1
            continue

        db.add(
            FuelEntry(
                vehicle_id=vehicle_id,
                entry_type=row.entry_type,
                date=row.date,
                odometer_km=row.odometer_km,
                litres=row.litres,
                amount_rs=row.amount_rs,
                price_per_litre=row.price_per_litre,
                fill_type=row.fill_type,
                location=row.location,
                station_name=row.station_name,
                notes=row.notes or None,
                odometer_status=row.odometer_status,
                distance_override_km=row.distance_override_km,
                source=row.source,
                raw_text=row.raw_text,
            )
        )
        imported += 1

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    return ImportResult(
        imported=imported, skipped_duplicates=skipped_duplicates, skipped_errors=skipped_errors
    )
