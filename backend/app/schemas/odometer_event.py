import datetime as dt
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, model_validator

from app.models.enums import OdometerEventType


class OdometerEventCreate(BaseModel):
    event_type: OdometerEventType
    start_date: dt.date
    end_date: dt.date | None = None
    old_reading_at_change: Decimal | None = None
    new_reading_at_change: Decimal | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def check_change_readings(self) -> Self:
        if self.event_type in (OdometerEventType.REPLACED, OdometerEventType.RESET) and (
            self.old_reading_at_change is None or self.new_reading_at_change is None
        ):
            raise ValueError(
                "old_reading_at_change and new_reading_at_change are required for replaced/reset"
            )
        return self


class OdometerEventUpdate(BaseModel):
    end_date: dt.date | None = None
    old_reading_at_change: Decimal | None = None
    new_reading_at_change: Decimal | None = None
    notes: str | None = None


class OdometerEventRead(BaseModel):
    id: int
    vehicle_id: int
    event_type: OdometerEventType
    start_date: dt.date
    end_date: dt.date | None
    old_reading_at_change: Decimal | None
    new_reading_at_change: Decimal | None
    notes: str | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}
