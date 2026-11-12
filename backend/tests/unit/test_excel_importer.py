import datetime as dt
from decimal import Decimal
from io import BytesIO

from app.models.enums import EntryType, FillType, OdometerStatus
from app.services.importers.excel_importer import build_import_template, parse_excel_file
from app.services.importers.parsed_row import EXCEL_COLUMNS


def _workbook_bytes(rows: list[list]) -> bytes:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(EXCEL_COLUMNS)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_template_has_expected_header_and_example_row() -> None:
    workbook = build_import_template()
    sheet = workbook.active
    header = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
    assert header == EXCEL_COLUMNS
    assert sheet.max_row == 2


def test_parses_a_valid_refuel_row_with_string_date() -> None:
    file_bytes = _workbook_bytes(
        [["refuel", "08/06/2026", 3767.0, 12.5, 1000.0, "", "full", "ngp", "", "ok", "", ""]]
    )
    rows = parse_excel_file(file_bytes)
    assert len(rows) == 1
    row = rows[0]
    assert row.errors == []
    assert row.entry_type == EntryType.REFUEL
    assert row.date == dt.date(2026, 6, 8)
    assert row.odometer_km == Decimal("3767.0")
    assert row.litres == Decimal("12.5")
    assert row.price_per_litre == Decimal("80.00")


def test_parses_a_valid_refuel_row_with_native_excel_date() -> None:
    file_bytes = _workbook_bytes(
        [["refuel", dt.date(2026, 6, 8), 3767.0, 12.5, 1000.0, "", "full", "ngp", "", "ok", "", ""]]
    )
    rows = parse_excel_file(file_bytes)
    assert rows[0].date == dt.date(2026, 6, 8)
    assert rows[0].errors == []


def test_price_per_litre_computed_when_only_amount_given() -> None:
    file_bytes = _workbook_bytes(
        [["refuel", "08/06/2026", 3767.0, 10, 905, "", "full", "", "", "ok", "", ""]]
    )
    row = parse_excel_file(file_bytes)[0]
    assert row.price_per_litre == Decimal("90.50")


def test_amount_computed_when_only_price_given() -> None:
    file_bytes = _workbook_bytes(
        [["refuel", "08/06/2026", 3767.0, 10, "", 90.5, "full", "", "", "ok", "", ""]]
    )
    row = parse_excel_file(file_bytes)[0]
    assert row.amount_rs == Decimal("905.0")


def test_fuel_removed_row_requires_notes() -> None:
    file_bytes = _workbook_bytes(
        [["fuel_removed", "10/06/2026", "", 2, "", "", "", "", "", "ok", "", ""]]
    )
    row = parse_excel_file(file_bytes)[0]
    assert row.entry_type == EntryType.FUEL_REMOVED
    assert any("notes is required" in e for e in row.errors)


def test_fuel_removed_row_with_notes_parses_cleanly() -> None:
    file_bytes = _workbook_bytes(
        [["fuel_removed", "10/06/2026", "", 2, "", "", "", "", "", "ok", "", "for generator"]]
    )
    row = parse_excel_file(file_bytes)[0]
    assert row.errors == []
    assert row.notes == "for generator"
    assert row.odometer_km is None


def test_invalid_entry_type_is_flagged() -> None:
    file_bytes = _workbook_bytes(
        [["not_a_type", "08/06/2026", 3767.0, 12.5, 1000.0, "", "full", "", "", "ok", "", ""]]
    )
    row = parse_excel_file(file_bytes)[0]
    assert any("entry_type must be" in e for e in row.errors)


def test_malformed_date_string_is_flagged_not_dropped() -> None:
    file_bytes = _workbook_bytes(
        [["refuel", "2026-06-08", 3767.0, 12.5, 1000.0, "", "full", "", "", "ok", "", ""]]
    )
    row = parse_excel_file(file_bytes)[0]
    assert any("DD/MM/YYYY" in e for e in row.errors)


def test_faulty_odometer_status_round_trips() -> None:
    file_bytes = _workbook_bytes(
        [["refuel", "08/06/2026", 3767.0, 12.5, 1000.0, "", "full", "", "", "faulty", "", ""]]
    )
    row = parse_excel_file(file_bytes)[0]
    assert row.odometer_status == OdometerStatus.FAULTY


def test_distance_override_parsed() -> None:
    file_bytes = _workbook_bytes(
        [["refuel", "08/06/2026", 3767.0, 12.5, 1000.0, "", "partial", "", "", "ok", "420.5", ""]]
    )
    row = parse_excel_file(file_bytes)[0]
    assert row.fill_type == FillType.PARTIAL
    assert row.distance_override_km == Decimal("420.5")


def test_blank_rows_are_skipped() -> None:
    file_bytes = _workbook_bytes(
        [
            ["refuel", "08/06/2026", 3767.0, 12.5, 1000.0, "", "full", "", "", "ok", "", ""],
            [None, None, None, None, None, None, None, None, None, None, None, None],
            ["refuel", "15/06/2026", 3800.0, 5.0, 450.0, "", "partial", "", "", "ok", "", ""],
        ]
    )
    rows = parse_excel_file(file_bytes)
    assert len(rows) == 2


def test_extra_unknown_column_is_ignored() -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append([*EXCEL_COLUMNS, "raw_text"])
    sheet.append(
        [
            "refuel",
            "08/06/2026",
            3767.0,
            12.5,
            1000.0,
            "",
            "full",
            "",
            "",
            "ok",
            "",
            "",
            "orig line",
        ]
    )
    buffer = BytesIO()
    workbook.save(buffer)

    row = parse_excel_file(buffer.getvalue())[0]
    assert row.errors == []
