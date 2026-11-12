import datetime as dt
from decimal import Decimal

from app.models.enums import EntryType, FillType, OdometerStatus
from app.services.importers.raw_text_parser import parse_raw_text

SAMPLE_LINES = """
12.50 lt - 1000rs - 3767 - 08/06 - full tank - ngp
9.11 lt - 810.33 rs - 4136 - 23/06 - full tank - cwa
9.36 lt - 830 rs 4479.3 - 22/07 - full - cwa
9.25 lt - 840 rs 4818 - 22/08 full cwa
8.95 lt - 800 rs 5172.8 - 13/09 - Pachmari - full
"""


def test_sample_lines_all_parse_without_errors() -> None:
    rows = parse_raw_text(SAMPLE_LINES, start_year=2026)
    assert len(rows) == 5
    for row in rows:
        assert row.errors == [], f"row {row.row_number} ({row.raw_text!r}) had errors: {row.errors}"
        assert row.entry_type == EntryType.REFUEL


def test_first_sample_line_fields() -> None:
    row = parse_raw_text(SAMPLE_LINES, start_year=2026)[0]
    assert row.litres == Decimal("12.50")
    assert row.amount_rs == Decimal("1000")
    assert row.odometer_km == Decimal("3767")
    assert row.date == dt.date(2026, 6, 8)
    assert row.fill_type == FillType.FULL
    assert row.location == "ngp"
    assert row.price_per_litre == Decimal("80.00")


def test_swapped_amount_and_odometer_with_no_separator() -> None:
    # "830 rs 4479.3" -- amount and odometer run together with no separator
    row = parse_raw_text(SAMPLE_LINES, start_year=2026)[2]
    assert row.amount_rs == Decimal("830")
    assert row.odometer_km == Decimal("4479.3")
    assert row.fill_type == FillType.FULL
    assert row.location == "cwa"


def test_missing_separators_and_fill_type_location_swap() -> None:
    # "9.25 lt - 840 rs 4818 - 22/08 full cwa" -- no dashes around fill type/location
    row = parse_raw_text(SAMPLE_LINES, start_year=2026)[3]
    assert row.fill_type == FillType.FULL
    assert row.location == "cwa"


def test_location_before_fill_type_swap() -> None:
    # "8.95 lt - 800 rs 5172.8 - 13/09 - Pachmari - full" -- last two fields swapped
    row = parse_raw_text(SAMPLE_LINES, start_year=2026)[4]
    assert row.fill_type == FillType.FULL
    assert row.location == "Pachmari"


def test_year_rolls_over_when_month_goes_backwards() -> None:
    text = "10 lt - 900 rs - 1000 - 15/12 - full - ngp\n10 lt - 900 rs - 1300 - 05/01 - full - ngp"
    rows = parse_raw_text(text, start_year=2026)
    assert rows[0].date == dt.date(2026, 12, 15)
    assert rows[1].date == dt.date(2027, 1, 5)


def test_explicit_four_digit_year_is_used_as_is() -> None:
    row = parse_raw_text("10 lt - 900 rs - 1000 - 15/12/2030 - full - ngp", start_year=2026)[0]
    assert row.date == dt.date(2030, 12, 15)


def test_explicit_two_digit_year_is_expanded() -> None:
    row = parse_raw_text("10 lt - 900 rs - 1000 - 15/12/27 - full - ngp", start_year=2026)[0]
    assert row.date == dt.date(2027, 12, 15)


def test_odometer_decrease_after_year_inference_flags_warning() -> None:
    # Looks like odometer went backwards even after year rollover -- should warn, not error.
    text = "10 lt - 900 rs - 5000 - 15/12 - full - ngp\n10 lt - 900 rs - 1000 - 05/01 - full - ngp"
    rows = parse_raw_text(text, start_year=2026)
    assert rows[1].errors == []
    assert any("lower than the previous" in w for w in rows[1].warnings)


def test_removal_line_detected_as_fuel_removed() -> None:
    row = parse_raw_text("took out 2 lt - 15/06 - for generator", start_year=2026)[0]
    assert row.entry_type == EntryType.FUEL_REMOVED
    assert row.litres == Decimal("2")
    assert row.date == dt.date(2026, 6, 15)
    assert "removal hint" in row.notes
    assert "for generator" in row.notes


def test_drained_removal_variant() -> None:
    row = parse_raw_text("drained 1.5 lt 20/07 for cleaning carb", start_year=2026)[0]
    assert row.entry_type == EntryType.FUEL_REMOVED
    assert row.litres == Decimal("1.5")
    assert row.date == dt.date(2026, 7, 20)


def test_faulty_meter_hint_marks_entry_faulty() -> None:
    row = parse_raw_text(
        "12.50 lt - 1000rs - 3767 - 08/06 - full tank - ngp - speedo not working", start_year=2026
    )[0]
    assert row.odometer_status == OdometerStatus.FAULTY
    assert "faulty hint" in row.notes


def test_odometer_faulty_phrase_variant() -> None:
    row = parse_raw_text(
        "9.11 lt - 810 rs - 4136 - 23/06 - full tank - odometer faulty", start_year=2026
    )[0]
    assert row.odometer_status == OdometerStatus.FAULTY


def test_line_missing_litres_is_flagged_with_error_not_dropped() -> None:
    rows = parse_raw_text("1000rs - 3767 - 08/06 - full tank - ngp", start_year=2026)
    assert len(rows) == 1
    row = rows[0]
    assert any("litres" in e for e in row.errors)
    assert row.raw_text == "1000rs - 3767 - 08/06 - full tank - ngp"


def test_line_with_no_fill_type_defaults_to_full_with_warning() -> None:
    row = parse_raw_text("12.50 lt - 1000rs - 3767 - 08/06 - ngp", start_year=2026)[0]
    assert row.fill_type == FillType.FULL
    assert any("defaulting to full" in w for w in row.warnings)


def test_blank_lines_are_skipped() -> None:
    text = (
        "12.50 lt - 1000rs - 3767 - 08/06 - full tank - ngp\n"
        "\n\n"
        "9.11 lt - 810 rs - 4136 - 23/06 - full tank - cwa"
    )
    rows = parse_raw_text(text, start_year=2026)
    assert len(rows) == 2


def test_partial_fill_type_recognized() -> None:
    row = parse_raw_text("5 lt - 450 rs - 4000 - 10/06 - partial - ngp", start_year=2026)[0]
    assert row.fill_type == FillType.PARTIAL


def test_half_is_recognized_as_partial() -> None:
    row = parse_raw_text("5 lt - 450 rs - 4000 - 10/06 - half - ngp", start_year=2026)[0]
    assert row.fill_type == FillType.PARTIAL
