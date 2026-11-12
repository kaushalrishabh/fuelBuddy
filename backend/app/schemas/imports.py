import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import EntrySource, EntryType, FillType, OdometerStatus


class ParsedRowOut(BaseModel):
    row_number: int
    raw_text: str
    source: EntrySource
    entry_type: EntryType | None
    date: dt.date | None
    odometer_km: Decimal | None
    litres: Decimal | None
    amount_rs: Decimal | None
    price_per_litre: Decimal | None
    fill_type: FillType | None
    location: str | None
    station_name: str | None
    odometer_status: OdometerStatus
    distance_override_km: Decimal | None
    notes: str
    errors: list[str]
    warnings: list[str]
    is_duplicate: bool

    model_config = {"from_attributes": True}


class ImportPreviewResponse(BaseModel):
    rows: list[ParsedRowOut]
    valid_count: int
    warning_count: int
    error_count: int
    duplicate_count: int


class RawTextPreviewRequest(BaseModel):
    text: str
    start_year: int = Field(ge=1990, le=2100)


class ImportCommitRequest(BaseModel):
    rows: list[ParsedRowOut]
    skip_duplicates: bool = True


class ImportCommitResponse(BaseModel):
    imported: int
    skipped_duplicates: int
    skipped_errors: int
