import datetime as dt
from decimal import Decimal
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.models.enums import EntrySource, FillType, OdometerStatus


class RefuelCreate(BaseModel):
    entry_type: Literal["refuel"] = "refuel"
    date: dt.date
    odometer_km: Decimal
    litres: Decimal = Field(gt=0)
    amount_rs: Decimal | None = Field(default=None, ge=0)
    price_per_litre: Decimal | None = Field(default=None, ge=0)
    fill_type: FillType = FillType.FULL
    location: str | None = None
    station_name: str | None = None
    notes: str | None = None
    odometer_status: OdometerStatus = OdometerStatus.OK
    distance_override_km: Decimal | None = None
    source: EntrySource = EntrySource.MANUAL
    raw_text: str | None = None

    @model_validator(mode="after")
    def fill_price_per_litre(self) -> Self:
        if self.amount_rs is None and self.price_per_litre is None:
            raise ValueError("Provide amount_rs or price_per_litre")
        if self.price_per_litre is None and self.amount_rs is not None:
            self.price_per_litre = (self.amount_rs / self.litres).quantize(Decimal("0.01"))
        elif self.amount_rs is None and self.price_per_litre is not None:
            self.amount_rs = (self.price_per_litre * self.litres).quantize(Decimal("0.01"))
        return self


class FuelRemovedCreate(BaseModel):
    entry_type: Literal["fuel_removed"] = "fuel_removed"
    date: dt.date
    litres: Decimal = Field(gt=0)
    odometer_km: Decimal | None = None
    notes: str = Field(min_length=1)
    odometer_status: OdometerStatus = OdometerStatus.OK
    source: EntrySource = EntrySource.MANUAL
    raw_text: str | None = None


EntryCreate = Annotated[RefuelCreate | FuelRemovedCreate, Field(discriminator="entry_type")]


class EntryUpdate(BaseModel):
    date: dt.date | None = None
    odometer_km: Decimal | None = None
    litres: Decimal | None = None
    amount_rs: Decimal | None = None
    price_per_litre: Decimal | None = None
    fill_type: FillType | None = None
    location: str | None = None
    station_name: str | None = None
    notes: str | None = None
    odometer_status: OdometerStatus | None = None
    distance_override_km: Decimal | None = None


class EntryRead(BaseModel):
    id: int
    vehicle_id: int
    entry_type: Literal["refuel", "fuel_removed"]
    date: dt.date
    odometer_km: Decimal | None
    litres: Decimal
    amount_rs: Decimal | None
    price_per_litre: Decimal | None
    fill_type: FillType | None
    location: str | None
    station_name: str | None
    notes: str | None
    odometer_status: OdometerStatus
    distance_override_km: Decimal | None
    source: EntrySource
    raw_text: str | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class EntryListResponse(BaseModel):
    items: list[EntryRead]
    total: int
    page: int
    page_size: int


class SuggestedFixOut(BaseModel):
    action: str
    label: str
    prefill: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class ValidationWarningOut(BaseModel):
    code: str
    message: str
    suggested_fixes: list[SuggestedFixOut] = []

    model_config = {"from_attributes": True}


class FillPreview(BaseModel):
    distance_since_last_full_km: Decimal | None
    km_per_l: Decimal | None
    rs_per_km: Decimal | None


class EntrySaveResponse(BaseModel):
    entry: EntryRead
    warnings: list[ValidationWarningOut] = []
    preview: FillPreview | None = None
