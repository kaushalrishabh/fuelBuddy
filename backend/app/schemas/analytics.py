import datetime as dt
from decimal import Decimal

from pydantic import BaseModel

from app.services.mileage import SegmentStatus


class KPIsOut(BaseModel):
    lifetime_km_per_l: Decimal | None
    last_fill_km_per_l: Decimal | None
    total_km: Decimal
    total_litres: Decimal
    litres_removed: Decimal
    total_spend_rs: Decimal
    average_rs_per_km: Decimal | None
    average_rs_per_l: Decimal | None
    days_since_last_fill: int | None


class MileagePointOut(BaseModel):
    date: dt.date
    km_per_l: Decimal | None
    rolling_avg_km_per_l: Decimal | None
    status: SegmentStatus

    model_config = {"from_attributes": True}


class MonthlyPointOut(BaseModel):
    year: int
    month: int
    litres: Decimal
    spend_rs: Decimal
    km: Decimal
    fill_count: int

    model_config = {"from_attributes": True}


class PricePointOut(BaseModel):
    date: dt.date
    price_per_litre: Decimal

    model_config = {"from_attributes": True}


class PriceTrendOut(BaseModel):
    points: list[PricePointOut]
    min_price: Decimal | None
    max_price: Decimal | None
    average_price: Decimal | None

    model_config = {"from_attributes": True}


class YearlySummaryOut(BaseModel):
    year: int
    km: Decimal
    litres: Decimal
    spend_rs: Decimal
    avg_km_per_l: Decimal | None
    avg_rs_per_l: Decimal | None
    fill_count: int

    model_config = {"from_attributes": True}


class CostEfficiencyPointOut(BaseModel):
    date: dt.date
    rs_per_km: Decimal | None

    model_config = {"from_attributes": True}


class CostEfficiencyOut(BaseModel):
    points: list[CostEfficiencyPointOut]
    yearly_summary: list[YearlySummaryOut]


class RankedPlaceOut(BaseModel):
    name: str
    sample_size: int
    avg_km_per_l: Decimal
    avg_rs_per_l: Decimal | None

    model_config = {"from_attributes": True}


class SeasonalityPointOut(BaseModel):
    month: int
    avg_km_per_l: Decimal | None
    sample_size: int

    model_config = {"from_attributes": True}


class RidingPatternOut(BaseModel):
    avg_days_between_fills: Decimal | None
    avg_km_per_day: Decimal | None
    predicted_next_refuel_date: dt.date | None

    model_config = {"from_attributes": True}


class SegmentSummaryOut(BaseModel):
    start_date: dt.date
    end_date: dt.date
    distance_km: Decimal
    km_per_l: Decimal | None
    rs_per_km: Decimal | None
    status: SegmentStatus

    model_config = {"from_attributes": True}


class RecordsOut(BaseModel):
    best_mileage: SegmentSummaryOut | None
    worst_mileage: SegmentSummaryOut | None
    longest_distance: SegmentSummaryOut | None
    most_expensive_fill_entry_id: int | None
    most_expensive_fill_amount_rs: Decimal | None

    model_config = {"from_attributes": True}


class DataQualityIssueOut(BaseModel):
    kind: str
    message: str
    entry_ids: list[int]

    model_config = {"from_attributes": True}


class DataQualityReportOut(BaseModel):
    issues: list[DataQualityIssueOut]
    excluded_segment_count: int
    estimated_segment_count: int

    model_config = {"from_attributes": True}
