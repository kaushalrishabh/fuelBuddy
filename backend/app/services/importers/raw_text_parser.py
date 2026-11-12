"""Parses free-text refuel notes (see CLAUDE.md / plan for the sample format).

Fields are identified by pattern, not position, because the user's notes use
inconsistent separators and field order. Each regex match is blanked out of
a working copy of the line as it's consumed, so whatever's left at the end
is treated as the location; nothing recognized-but-unplaceable is dropped
silently -- it goes into `notes` instead.
"""

import datetime as dt
import re
from decimal import Decimal

from app.models.enums import EntrySource, EntryType, FillType, OdometerStatus
from app.services.importers.parsed_row import ParsedRow

LITRE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:ltr|lt|l)\b", re.IGNORECASE)
AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*rs\b", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")
FULL_TANK_RE = re.compile(r"\bfull\s*tank\b", re.IGNORECASE)
FULL_RE = re.compile(r"\bfull\b", re.IGNORECASE)
PARTIAL_RE = re.compile(r"\b(?:partial|half)\b", re.IGNORECASE)
PLAIN_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")

REMOVAL_RE = re.compile(r"\b(took out|drained|removed|took)\b", re.IGNORECASE)
FAULTY_RE = re.compile(
    r"\b(odometer (?:not working|faulty)|meter (?:not working|faulty)|speedo(?:meter)?)\b",
    re.IGNORECASE,
)

_ParsedLine = tuple[ParsedRow, int | None, int | None, int | None]


def _remove_span(text: str, span: tuple[int, int]) -> str:
    start, end = span
    return text[:start] + " " + text[end:]


def _clean_leftover(text: str) -> str | None:
    cleaned = " ".join(re.sub(r"[-,]", " ", text).split())
    return cleaned or None


def _append_note(existing: str, addition: str) -> str:
    return f"{existing}; {addition}" if existing else addition


def _extract_date(working: str) -> tuple[str, int | None, int | None, int | None, str | None]:
    match = DATE_RE.search(working)
    if not match:
        return working, None, None, None, "Could not find a date (expected DD/MM or DD/MM/YY(YY))"

    day_str, month_str, year_str = match.groups()
    day, month = int(day_str), int(month_str)
    year = None
    if year_str:
        year = int(year_str)
        if len(year_str) == 2:
            year += 2000
    return _remove_span(working, match.span()), month, day, year, None


def _extract_fill_type(working: str) -> tuple[str, FillType, str | None]:
    if FULL_TANK_RE.search(working):
        return FULL_TANK_RE.sub("", working, count=1), FillType.FULL, None
    if FULL_RE.search(working):
        return FULL_RE.sub("", working, count=1), FillType.FULL, None
    if PARTIAL_RE.search(working):
        return PARTIAL_RE.sub("", working, count=1), FillType.PARTIAL, None
    return working, FillType.FULL, "No fill type found in the line; defaulting to full"


def _parse_refuel_line(line: str, row_number: int) -> _ParsedLine:
    working = line
    row = ParsedRow(
        row_number=row_number,
        raw_text=line,
        source=EntrySource.TEXT_IMPORT,
        entry_type=EntryType.REFUEL,
    )

    faulty_match = FAULTY_RE.search(working)
    if faulty_match:
        row.odometer_status = OdometerStatus.FAULTY
        row.notes = _append_note(row.notes, f"faulty hint: '{faulty_match.group(0)}'")
        working = _remove_span(working, faulty_match.span())

    litres_match = LITRE_RE.search(working)
    if litres_match:
        row.litres = Decimal(litres_match.group(1))
        working = _remove_span(working, litres_match.span())
    else:
        row.errors.append("Could not find litres (expected a number followed by lt/ltr/l)")

    amount_match = AMOUNT_RE.search(working)
    if amount_match:
        row.amount_rs = Decimal(amount_match.group(1))
        working = _remove_span(working, amount_match.span())

    working, month, day, year, date_error = _extract_date(working)
    if date_error:
        row.errors.append(date_error)

    working, fill_type, fill_warning = _extract_fill_type(working)
    row.fill_type = fill_type
    if fill_warning:
        row.warnings.append(fill_warning)

    number_match = PLAIN_NUMBER_RE.search(working)
    if number_match:
        row.odometer_km = Decimal(number_match.group(0))
        working = _remove_span(working, number_match.span())
    else:
        row.errors.append("Could not find an odometer reading")

    row.location = _clean_leftover(working)

    if row.litres is not None and row.amount_rs is not None:
        row.price_per_litre = (row.amount_rs / row.litres).quantize(Decimal("0.01"))

    return row, month, day, year


def _parse_removal_line(line: str, row_number: int, removal_phrase: str) -> _ParsedLine:
    working = line
    row = ParsedRow(
        row_number=row_number,
        raw_text=line,
        source=EntrySource.TEXT_IMPORT,
        entry_type=EntryType.FUEL_REMOVED,
    )

    litres_match = LITRE_RE.search(working)
    if litres_match:
        row.litres = Decimal(litres_match.group(1))
        working = _remove_span(working, litres_match.span())
    else:
        row.errors.append("Could not find litres removed (expected a number followed by lt/ltr/l)")

    working, month, day, year, date_error = _extract_date(working)
    if date_error:
        row.errors.append(date_error)

    number_match = PLAIN_NUMBER_RE.search(working)
    if number_match:
        row.odometer_km = Decimal(number_match.group(0))
        working = _remove_span(working, number_match.span())

    notes_parts = [f"removal hint: '{removal_phrase}'"]
    leftover = _clean_leftover(working)
    if leftover:
        notes_parts.append(leftover)
    row.notes = "; ".join(notes_parts)

    return row, month, day, year


def _parse_line(line: str, row_number: int) -> _ParsedLine:
    removal_match = REMOVAL_RE.search(line)
    if removal_match:
        return _parse_removal_line(line, row_number, removal_match.group(0))
    return _parse_refuel_line(line, row_number)


def parse_raw_text(text: str, start_year: int) -> list[ParsedRow]:
    """Parses pasted notes into rows, inferring the year from month rollovers.

    `start_year` is the year of the first line; the year increments whenever
    a line's month is earlier than the previous line's month (e.g. 12 -> 01).
    """
    pending: list[_ParsedLine] = []
    row_number = 0
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        row_number += 1
        pending.append(_parse_line(stripped, row_number))

    rows: list[ParsedRow] = []
    current_year = start_year
    previous_month: int | None = None
    previous_odometer: Decimal | None = None

    for row, month, day, explicit_year in pending:
        if month is not None and day is not None:
            if explicit_year is not None:
                current_year = explicit_year
            elif previous_month is not None and month < previous_month:
                current_year += 1

            try:
                row.date = dt.date(current_year, month, day)
            except ValueError:
                row.errors.append(f"'{day:02d}/{month:02d}/{current_year}' is not a valid date")
            else:
                previous_month = month

        if row.date is not None and row.odometer_km is not None:
            if previous_odometer is not None and row.odometer_km < previous_odometer:
                row.warnings.append(
                    "Odometer is lower than the previous parsed row — check the inferred year"
                )
            previous_odometer = row.odometer_km

        rows.append(row)

    return rows
