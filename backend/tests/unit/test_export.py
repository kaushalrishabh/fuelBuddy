import datetime as dt
from decimal import Decimal

from app.models.enums import EntrySource, EntryType, FillType, OdometerStatus
from app.models.fuel_entry import FuelEntry
from app.models.vehicle import Vehicle
from app.services.export import build_export_workbook

# These construct FuelEntry objects directly without a DB flush, so column
# defaults (odometer_status, source) must be passed explicitly -- they'd
# otherwise only be filled in by SQLAlchemy at insert time.


def _refuel(date: str, odometer: str, litres: str = "10", amount: str = "900") -> FuelEntry:
    return FuelEntry(
        entry_type=EntryType.REFUEL,
        date=dt.date.fromisoformat(date),
        odometer_km=Decimal(odometer),
        litres=Decimal(litres),
        amount_rs=Decimal(amount),
        price_per_litre=(Decimal(amount) / Decimal(litres)).quantize(Decimal("0.01")),
        fill_type=FillType.FULL,
        odometer_status=OdometerStatus.OK,
        source=EntrySource.MANUAL,
    )


def _removed(date: str, litres: str) -> FuelEntry:
    return FuelEntry(
        entry_type=EntryType.FUEL_REMOVED,
        date=dt.date.fromisoformat(date),
        litres=Decimal(litres),
        notes="took some out",
        odometer_status=OdometerStatus.OK,
        source=EntrySource.MANUAL,
    )


def _vehicle(tank: str = "13") -> Vehicle:
    return Vehicle(id=1, user_id=1, name="Test Bike", tank_capacity_l=Decimal(tank))


def _sheet_rows(workbook, title: str) -> list[tuple]:
    sheet = workbook[title]
    return [tuple(row) for row in sheet.iter_rows(min_row=2, values_only=True)]


def test_entries_sheet_contains_every_entry_sorted_by_date() -> None:
    entries = [_refuel("2026-01-15", "1500"), _refuel("2026-01-01", "1000")]
    workbook = build_export_workbook(_vehicle(), entries, [])
    rows = _sheet_rows(workbook, "Entries")
    assert len(rows) == 2
    assert rows[0][1] == "01/01/2026"  # sorted ascending by date
    assert rows[1][1] == "15/01/2026"


def test_computed_sheet_reports_valid_segment_math() -> None:
    entries = [_refuel("2026-01-01", "1000"), _refuel("2026-01-15", "1500")]
    workbook = build_export_workbook(_vehicle(), entries, [])
    rows = _sheet_rows(workbook, "Computed")
    assert len(rows) == 1
    start, end, distance, net_litres, km_per_l, rs_per_l, rs_per_km, status, reason = rows[0]
    assert distance == 500.0
    assert km_per_l == 50.0
    assert status == "valid"
    assert reason == ""


def test_computed_sheet_reports_removal_adjusted_math() -> None:
    entries = [
        _refuel("2026-02-01", "2000"),
        _refuel("2026-02-15", "2500"),
        _removed("2026-02-08", "2"),
    ]
    workbook = build_export_workbook(_vehicle(), entries, [])
    rows = _sheet_rows(workbook, "Computed")
    _, _, distance, net_litres, km_per_l, *_ = rows[0]
    assert distance == 500.0
    assert net_litres == 8.0
    assert km_per_l == 62.5


def test_summary_sheet_aggregates_by_year() -> None:
    entries = [
        _refuel("2026-01-01", "1000"),
        _refuel("2026-01-15", "1500"),
        _refuel("2026-02-01", "2000"),
    ]
    workbook = build_export_workbook(_vehicle(), entries, [])
    rows = _sheet_rows(workbook, "Summary")
    assert len(rows) == 1
    year, km, litres, spend, avg_km_per_l, avg_rs_per_l, fills = rows[0]
    assert year == 2026
    assert km == 1000.0  # two segments of 500km each
    assert fills == 3


def test_date_filter_restricts_entries_and_segments_but_not_odometer_events() -> None:
    from app.models.enums import OdometerEventType
    from app.models.odometer_event import OdometerEvent

    entries = [
        _refuel("2026-01-01", "1000"),
        _refuel("2026-01-15", "1500"),
        _refuel("2026-03-01", "3000"),
    ]
    event = OdometerEvent(
        event_type=OdometerEventType.FAULTY_PERIOD,
        start_date=dt.date(2025, 1, 1),
        end_date=dt.date(2025, 2, 1),
    )

    workbook = build_export_workbook(
        _vehicle(), entries, [event], date_from=dt.date(2026, 1, 1), date_to=dt.date(2026, 1, 31)
    )

    assert len(_sheet_rows(workbook, "Entries")) == 2  # the March entry is excluded
    assert len(_sheet_rows(workbook, "Computed")) == 1  # only the Jan-ending segment
    assert len(_sheet_rows(workbook, "Odometer events")) == 1  # not filtered by date


def test_entries_sheet_round_trips_through_the_importer() -> None:
    from io import BytesIO

    from app.services.importers.excel_importer import parse_excel_file

    entries = [_refuel("2026-06-08", "3767.0", litres="12.50", amount="1000.00")]
    workbook = build_export_workbook(_vehicle(), entries, [])

    # Re-import the "Entries" sheet on its own, as if it were saved standalone.
    standalone = workbook
    buffer = BytesIO()
    standalone.active = standalone["Entries"]
    standalone.save(buffer)

    parsed = parse_excel_file(buffer.getvalue())
    assert len(parsed) == 1
    row = parsed[0]
    assert row.errors == []
    assert row.odometer_km == Decimal("3767.0")
    assert row.litres == Decimal("12.50")
