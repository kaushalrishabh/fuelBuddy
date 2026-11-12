import datetime as dt
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from openpyxl import Workbook, load_workbook

from app.models.enums import EntrySource, EntryType, FillType, OdometerStatus
from app.services.importers.parsed_row import EXCEL_COLUMNS, ParsedRow

_EXAMPLE_ROW = [
    "refuel",
    "08/06/2026",
    3767.0,
    12.50,
    1000.00,
    "",
    "full",
    "ngp",
    "",
    "ok",
    "",
    "",
]


def build_import_template() -> Workbook:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Entries"
    sheet.append(EXCEL_COLUMNS)
    sheet.append(_EXAMPLE_ROW)
    for column_cells in sheet.columns:
        header = str(column_cells[0].value)
        sheet.column_dimensions[column_cells[0].column_letter].width = max(len(header) + 2, 12)
    return workbook


def _parse_date_cell(value: Any) -> tuple[dt.date | None, str | None]:
    if value in (None, ""):
        return None, None
    if isinstance(value, dt.datetime):
        return value.date(), None
    if isinstance(value, dt.date):
        return value, None
    if isinstance(value, str):
        try:
            return dt.datetime.strptime(value.strip(), "%d/%m/%Y").date(), None
        except ValueError:
            return None, f"date '{value}' is not in DD/MM/YYYY format"
    return None, f"unrecognized date value: {value!r}"


def _parse_decimal_cell(value: Any, field_name: str) -> tuple[Decimal | None, str | None]:
    if value in (None, ""):
        return None, None
    try:
        return Decimal(str(value)), None
    except InvalidOperation:
        return None, f"'{value}' is not a valid number for {field_name}"


def _clean_str_cell(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_excel_row(row_number: int, values: dict[str, Any]) -> ParsedRow:
    raw_text = ", ".join(f"{k}={v}" for k, v in values.items() if v not in (None, ""))
    row = ParsedRow(row_number=row_number, raw_text=raw_text, source=EntrySource.EXCEL)

    entry_type_raw = str(values.get("entry_type") or "").strip().lower()
    if entry_type_raw == EntryType.REFUEL.value:
        row.entry_type = EntryType.REFUEL
    elif entry_type_raw == EntryType.FUEL_REMOVED.value:
        row.entry_type = EntryType.FUEL_REMOVED
    else:
        row.errors.append(f"entry_type must be 'refuel' or 'fuel_removed', got '{entry_type_raw}'")

    date_value, date_error = _parse_date_cell(values.get("date"))
    row.date = date_value
    if date_error:
        row.errors.append(date_error)
    elif date_value is None:
        row.errors.append("date is required")

    for field_name in (
        "odometer_km",
        "litres",
        "amount_rs",
        "price_per_litre",
        "distance_override_km",
    ):
        parsed, error = _parse_decimal_cell(values.get(field_name), field_name)
        setattr(row, field_name, parsed)
        if error:
            row.errors.append(error)

    fill_type_raw = str(values.get("fill_type") or "full").strip().lower()
    try:
        row.fill_type = FillType(fill_type_raw)
    except ValueError:
        row.errors.append(f"fill_type must be 'full' or 'partial', got '{fill_type_raw}'")

    odometer_status_raw = str(values.get("odometer_status") or "ok").strip().lower()
    try:
        row.odometer_status = OdometerStatus(odometer_status_raw)
    except ValueError:
        row.errors.append(
            f"odometer_status must be one of ok/faulty/estimated, got '{odometer_status_raw}'"
        )

    row.location = _clean_str_cell(values.get("location"))
    row.station_name = _clean_str_cell(values.get("station_name"))
    row.notes = _clean_str_cell(values.get("notes")) or ""

    if row.entry_type == EntryType.REFUEL:
        if row.odometer_km is None:
            row.errors.append("odometer_km is required for refuel entries")
        if row.litres is None:
            row.errors.append("litres is required for refuel entries")
        if row.amount_rs is None and row.price_per_litre is None:
            row.errors.append("Provide amount_rs or price_per_litre for refuel entries")
        elif row.litres is not None:
            if row.price_per_litre is None and row.amount_rs is not None:
                row.price_per_litre = (row.amount_rs / row.litres).quantize(Decimal("0.01"))
            elif row.amount_rs is None and row.price_per_litre is not None:
                row.amount_rs = (row.price_per_litre * row.litres).quantize(Decimal("0.01"))
    elif row.entry_type == EntryType.FUEL_REMOVED:
        if row.litres is None:
            row.errors.append("litres is required for fuel_removed entries")
        if not row.notes:
            row.errors.append("notes is required for fuel_removed entries")

    return row


def parse_excel_file(file_bytes: bytes) -> list[ParsedRow]:
    workbook = load_workbook(BytesIO(file_bytes), data_only=True)
    sheet = workbook.active
    if sheet is None:
        return []

    rows_iter = sheet.iter_rows(min_row=1, values_only=True)
    header_row = next(rows_iter, None)
    if header_row is None:
        return []
    header = [str(cell).strip().lower() if cell is not None else "" for cell in header_row]

    rows: list[ParsedRow] = []
    row_number = 0
    for excel_row in rows_iter:
        if all(cell is None or str(cell).strip() == "" for cell in excel_row):
            continue
        row_number += 1
        values = {header[i]: excel_row[i] for i in range(min(len(header), len(excel_row)))}
        rows.append(_parse_excel_row(row_number, values))

    return rows
