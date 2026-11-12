import datetime as dt
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import EntrySource, EntryType, FillType
from app.models.fuel_entry import FuelEntry
from app.models.vehicle import Vehicle
from app.services.importers.commit import commit_rows
from app.services.importers.dedup import mark_duplicates
from app.services.importers.parsed_row import ParsedRow


def _refuel_row(
    row_number: int, date: str, odometer: str, litres: str = "10", amount: str = "900"
) -> ParsedRow:
    return ParsedRow(
        row_number=row_number,
        raw_text=f"row {row_number}",
        source=EntrySource.TEXT_IMPORT,
        entry_type=EntryType.REFUEL,
        date=dt.date.fromisoformat(date),
        odometer_km=Decimal(odometer),
        litres=Decimal(litres),
        amount_rs=Decimal(amount),
        price_per_litre=(Decimal(amount) / Decimal(litres)),
        fill_type=FillType.FULL,
    )


def _removal_row(row_number: int, date: str, litres: str, odometer: str | None = None) -> ParsedRow:
    return ParsedRow(
        row_number=row_number,
        raw_text=f"row {row_number}",
        source=EntrySource.TEXT_IMPORT,
        entry_type=EntryType.FUEL_REMOVED,
        date=dt.date.fromisoformat(date),
        odometer_km=Decimal(odometer) if odometer else None,
        litres=Decimal(litres),
        notes="took some out",
    )


# --- dedup -------------------------------------------------------------------


def test_mark_duplicates_flags_rows_matching_existing_entry(
    db_session: Session, test_vehicle: Vehicle
) -> None:
    existing = FuelEntry(
        vehicle_id=test_vehicle.id,
        entry_type=EntryType.REFUEL,
        date=dt.date(2026, 6, 8),
        odometer_km=Decimal("3767.0"),
        litres=Decimal("12.5"),
        amount_rs=Decimal("1000"),
        fill_type=FillType.FULL,
    )
    db_session.add(existing)
    db_session.commit()

    new_row = _refuel_row(1, "2026-06-08", "3767.0")
    mark_duplicates([new_row], [existing])
    assert new_row.is_duplicate is True


def test_mark_duplicates_does_not_flag_distinct_entries(
    db_session: Session, test_vehicle: Vehicle
) -> None:
    existing = FuelEntry(
        vehicle_id=test_vehicle.id,
        entry_type=EntryType.REFUEL,
        date=dt.date(2026, 6, 8),
        odometer_km=Decimal("3767.0"),
        litres=Decimal("12.5"),
        amount_rs=Decimal("1000"),
        fill_type=FillType.FULL,
    )
    new_row = _refuel_row(1, "2026-06-15", "4000.0")
    mark_duplicates([new_row], [existing])
    assert new_row.is_duplicate is False


def test_mark_duplicates_catches_duplicates_within_the_same_batch() -> None:
    row_a = _refuel_row(1, "2026-06-08", "3767.0")
    row_b = _refuel_row(2, "2026-06-08", "3767.0")
    mark_duplicates([row_a, row_b], [])
    assert row_a.is_duplicate is False
    assert row_b.is_duplicate is True


def test_mark_duplicates_soft_matches_removals_without_odometer() -> None:
    existing_orm = FuelEntry(
        vehicle_id=1,
        entry_type=EntryType.FUEL_REMOVED,
        date=dt.date(2026, 6, 10),
        litres=Decimal("2"),
        odometer_km=None,
        notes="took some out",
    )
    new_row = _removal_row(1, "2026-06-10", "2")
    mark_duplicates([new_row], [existing_orm])
    assert new_row.is_duplicate is True


def test_mark_duplicates_does_not_soft_match_different_litres() -> None:
    existing_orm = FuelEntry(
        vehicle_id=1,
        entry_type=EntryType.FUEL_REMOVED,
        date=dt.date(2026, 6, 10),
        litres=Decimal("2"),
        odometer_km=None,
        notes="took some out",
    )
    new_row = _removal_row(1, "2026-06-10", "3")
    mark_duplicates([new_row], [existing_orm])
    assert new_row.is_duplicate is False


# --- commit -------------------------------------------------------------------


def test_commit_rows_inserts_only_clean_rows(db_session: Session, test_vehicle: Vehicle) -> None:
    clean = _refuel_row(1, "2026-06-08", "3767.0")
    with_error = _refuel_row(2, "2026-06-09", "3800.0")
    with_error.errors.append("something's wrong")
    duplicate = _refuel_row(3, "2026-06-10", "3900.0")
    duplicate.is_duplicate = True

    result = commit_rows(db_session, test_vehicle.id, [clean, with_error, duplicate])

    assert result.imported == 1
    assert result.skipped_errors == 1
    assert result.skipped_duplicates == 1

    saved = db_session.query(FuelEntry).filter(FuelEntry.vehicle_id == test_vehicle.id).all()
    assert len(saved) == 1
    assert saved[0].odometer_km == Decimal("3767.0")


def test_commit_rows_can_include_duplicates_when_asked(
    db_session: Session, test_vehicle: Vehicle
) -> None:
    duplicate = _refuel_row(1, "2026-06-08", "3767.0")
    duplicate.is_duplicate = True

    result = commit_rows(db_session, test_vehicle.id, [duplicate], skip_duplicates=False)
    assert result.imported == 1
    assert result.skipped_duplicates == 0


def test_commit_rows_imports_fuel_removed_entries(
    db_session: Session, test_vehicle: Vehicle
) -> None:
    removal = _removal_row(1, "2026-06-10", "2")
    result = commit_rows(db_session, test_vehicle.id, [removal])
    assert result.imported == 1

    saved = db_session.query(FuelEntry).filter(FuelEntry.vehicle_id == test_vehicle.id).one()
    assert saved.entry_type == EntryType.FUEL_REMOVED
    assert saved.odometer_km is None
