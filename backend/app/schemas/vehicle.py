import datetime as dt
from decimal import Decimal

from pydantic import BaseModel


class VehicleRead(BaseModel):
    id: int
    name: str
    make: str | None
    model: str | None
    purchase_date: dt.date | None
    tank_capacity_l: Decimal
    initial_odometer_km: Decimal
    is_default: bool

    model_config = {"from_attributes": True}


class VehicleUpdate(BaseModel):
    name: str | None = None
    make: str | None = None
    model: str | None = None
    purchase_date: dt.date | None = None
    tank_capacity_l: Decimal | None = None
    initial_odometer_km: Decimal | None = None
