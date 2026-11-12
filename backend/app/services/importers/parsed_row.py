"""Shared row representation for both importers (Excel + raw-text paste).

Deliberately not a Pydantic Create schema: a parsed row can be partial or
invalid (missing fields, bad values) and must still be returned in the
preview with errors attached, rather than failing validation outright.
"""

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

from app.models.enums import EntrySource, EntryType, FillType, OdometerStatus

EXCEL_COLUMNS = [
    "entry_type",
    "date",
    "odometer_km",
    "litres",
    "amount_rs",
    "price_per_litre",
    "fill_type",
    "location",
    "station_name",
    "odometer_status",
    "distance_override_km",
    "notes",
]


@dataclass
class ParsedRow:
    row_number: int
    raw_text: str
    source: EntrySource = EntrySource.MANUAL
    entry_type: EntryType | None = None
    date: dt.date | None = None
    odometer_km: Decimal | None = None
    litres: Decimal | None = None
    amount_rs: Decimal | None = None
    price_per_litre: Decimal | None = None
    fill_type: FillType | None = None
    location: str | None = None
    station_name: str | None = None
    odometer_status: OdometerStatus = OdometerStatus.OK
    distance_override_km: Decimal | None = None
    notes: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_duplicate: bool = False
