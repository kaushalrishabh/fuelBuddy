"""Analytics endpoints.

The page has one global date-range filter, but not every section should
obey it: "lifetime km/L", seasonality, riding pattern, and the data-quality
panel are inherently whole-history views (the brief calls the first one out
by name, and filtering the other three to a narrow window would make them
meaningless or actively misleading). Everything else -- totals, monthly/
price/cost-efficiency trends, location ranking, records -- respects the
selected window. Each case below says which it is and why.
"""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.enums import EntryType
from app.models.fuel_entry import FuelEntry
from app.models.odometer_event import OdometerEvent
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.analytics import (
    CostEfficiencyOut,
    CostEfficiencyPointOut,
    DataQualityReportOut,
    KPIsOut,
    MileagePointOut,
    MonthlyPointOut,
    PriceTrendOut,
    RankedPlaceOut,
    RecordsOut,
    RidingPatternOut,
    SeasonalityPointOut,
    YearlySummaryOut,
)
from app.services.analytics import (
    DateRangeType,
    compute_cost_efficiency,
    compute_data_quality,
    compute_kpis,
    compute_location_ranking,
    compute_mileage_over_time,
    compute_monthly_breakdown,
    compute_price_trend,
    compute_records,
    compute_riding_pattern,
    compute_seasonality,
    compute_station_ranking,
    resolve_date_range,
)
from app.services.entry_mapping import (
    to_fuel_removed_entry,
    to_odometer_event_data,
    to_refuel_entry,
)
from app.services.mileage import FuelRemovedEntry, RefuelEntry, SegmentResult, compute_segments

router = APIRouter()


def _get_owned_vehicle(db: Session, vehicle_id: int, user: User) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    return vehicle


def _date_range_params(
    range: DateRangeType = Query(default=DateRangeType.ALL_TIME),
    year: int | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> tuple[dt.date | None, dt.date | None]:
    return resolve_date_range(
        range, dt.date.today(), year=year, date_from=date_from, date_to=date_to
    )


class _VehicleData:
    def __init__(
        self,
        vehicle: Vehicle,
        refuel_entries: list[RefuelEntry],
        removed_entries: list[FuelRemovedEntry],
        segments: list[SegmentResult],
    ) -> None:
        self.vehicle = vehicle
        self.refuel_entries = refuel_entries
        self.removed_entries = removed_entries
        self.segments = segments

    def in_range(self, date_from: dt.date | None, date_to: dt.date | None) -> "_VehicleData":
        def ok(d: dt.date) -> bool:
            if date_from is not None and d < date_from:
                return False
            if date_to is not None and d > date_to:
                return False
            return True

        return _VehicleData(
            self.vehicle,
            [e for e in self.refuel_entries if ok(e.date)],
            [e for e in self.removed_entries if ok(e.date)],
            [s for s in self.segments if ok(s.end_date)],
        )


def _load_vehicle_data(db: Session, vehicle_id: int, user: User) -> _VehicleData:
    vehicle = _get_owned_vehicle(db, vehicle_id, user)
    all_entries = db.query(FuelEntry).filter(FuelEntry.vehicle_id == vehicle_id).all()
    odometer_events = db.query(OdometerEvent).filter(OdometerEvent.vehicle_id == vehicle_id).all()

    refuel_entries = [to_refuel_entry(e) for e in all_entries if e.entry_type == EntryType.REFUEL]
    removed_entries = [
        to_fuel_removed_entry(e) for e in all_entries if e.entry_type == EntryType.FUEL_REMOVED
    ]
    odometer_event_data = [to_odometer_event_data(e) for e in odometer_events]

    segments = compute_segments(
        refuel_entries, removed_entries, odometer_event_data, vehicle.tank_capacity_l
    )
    return _VehicleData(vehicle, refuel_entries, removed_entries, segments)


DateRange = tuple[dt.date | None, dt.date | None]


@router.get("/kpis", response_model=KPIsOut)
def get_kpis(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_range: DateRange = Depends(_date_range_params),
) -> KPIsOut:
    data = _load_vehicle_data(db, vehicle_id, current_user)
    windowed = data.in_range(*date_range)
    today = dt.date.today()

    # "lifetime" km/L and days-since-last-fill are always whole-history facts,
    # not windowed by the page filter; totals/averages respect the window.
    lifetime = compute_kpis(data.segments, data.refuel_entries, data.removed_entries, as_of=today)
    windowed_kpis = compute_kpis(
        windowed.segments, windowed.refuel_entries, windowed.removed_entries, as_of=today
    )

    return KPIsOut(
        lifetime_km_per_l=lifetime.lifetime_km_per_l,
        last_fill_km_per_l=lifetime.last_fill_km_per_l,
        total_km=windowed_kpis.total_km,
        total_litres=windowed_kpis.total_litres,
        litres_removed=windowed_kpis.litres_removed,
        total_spend_rs=windowed_kpis.total_spend_rs,
        average_rs_per_km=windowed_kpis.average_rs_per_km,
        average_rs_per_l=windowed_kpis.average_rs_per_l,
        days_since_last_fill=lifetime.days_since_last_fill,
    )


@router.get("/mileage-over-time", response_model=list[MileagePointOut])
def get_mileage_over_time(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_range: DateRange = Depends(_date_range_params),
) -> list[MileagePointOut]:
    data = _load_vehicle_data(db, vehicle_id, current_user)
    date_from, date_to = date_range

    # The rolling average needs full history for context even near the start
    # of the selected window, so it's computed over everything and only the
    # resulting points are then sliced down to the window for display.
    all_points = compute_mileage_over_time(data.segments)
    windowed_points = [
        p
        for p in all_points
        if (date_from is None or p.date >= date_from) and (date_to is None or p.date <= date_to)
    ]
    return [MileagePointOut.model_validate(p) for p in windowed_points]


@router.get("/monthly", response_model=list[MonthlyPointOut])
def get_monthly_breakdown(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_range: DateRange = Depends(_date_range_params),
) -> list[MonthlyPointOut]:
    data = _load_vehicle_data(db, vehicle_id, current_user).in_range(*date_range)
    monthly = compute_monthly_breakdown(data.segments, data.refuel_entries)
    return [MonthlyPointOut.model_validate(m) for m in monthly]


@router.get("/price-trend", response_model=PriceTrendOut)
def get_price_trend(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_range: DateRange = Depends(_date_range_params),
) -> PriceTrendOut:
    data = _load_vehicle_data(db, vehicle_id, current_user).in_range(*date_range)
    return PriceTrendOut.model_validate(compute_price_trend(data.refuel_entries))


@router.get("/cost-efficiency", response_model=CostEfficiencyOut)
def get_cost_efficiency(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_range: DateRange = Depends(_date_range_params),
) -> CostEfficiencyOut:
    data = _load_vehicle_data(db, vehicle_id, current_user)
    date_from, date_to = date_range

    # The yearly summary table is always whole-history (that's its purpose);
    # only the Rs/km trend points are sliced to the selected window.
    full = compute_cost_efficiency(data.segments, data.refuel_entries)
    windowed_points = [
        p
        for p in full.points
        if (date_from is None or p.date >= date_from) and (date_to is None or p.date <= date_to)
    ]
    return CostEfficiencyOut(
        points=[CostEfficiencyPointOut.model_validate(p) for p in windowed_points],
        yearly_summary=[YearlySummaryOut.model_validate(y) for y in full.yearly_summary],
    )


@router.get("/locations", response_model=list[RankedPlaceOut])
def get_location_ranking(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_range: DateRange = Depends(_date_range_params),
) -> list[RankedPlaceOut]:
    data = _load_vehicle_data(db, vehicle_id, current_user).in_range(*date_range)
    ranking = compute_location_ranking(data.segments, data.refuel_entries)
    return [RankedPlaceOut.model_validate(r) for r in ranking]


@router.get("/stations", response_model=list[RankedPlaceOut])
def get_station_ranking(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_range: DateRange = Depends(_date_range_params),
) -> list[RankedPlaceOut]:
    data = _load_vehicle_data(db, vehicle_id, current_user).in_range(*date_range)
    ranking = compute_station_ranking(data.segments, data.refuel_entries)
    return [RankedPlaceOut.model_validate(r) for r in ranking]


@router.get("/seasonality", response_model=list[SeasonalityPointOut])
def get_seasonality(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SeasonalityPointOut]:
    # Always whole-history: "average km/L by month of year" needs multiple
    # years of data to mean anything, so the page filter doesn't apply here.
    data = _load_vehicle_data(db, vehicle_id, current_user)
    seasonality = compute_seasonality(data.segments)
    return [SeasonalityPointOut.model_validate(s) for s in seasonality]


@router.get("/riding-pattern", response_model=RidingPatternOut)
def get_riding_pattern(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RidingPatternOut:
    # Always whole-history: "recent" pace is handled internally (the last
    # few segments), not by the page's arbitrary display window.
    data = _load_vehicle_data(db, vehicle_id, current_user)
    return RidingPatternOut.model_validate(compute_riding_pattern(data.segments))


@router.get("/records", response_model=RecordsOut)
def get_records(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_range: DateRange = Depends(_date_range_params),
) -> RecordsOut:
    data = _load_vehicle_data(db, vehicle_id, current_user).in_range(*date_range)
    return RecordsOut.model_validate(compute_records(data.segments, data.refuel_entries))


@router.get("/data-quality", response_model=DataQualityReportOut)
def get_data_quality(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DataQualityReportOut:
    # Always whole-history: bad data anywhere should surface regardless of
    # which window happens to be selected for display elsewhere on the page.
    data = _load_vehicle_data(db, vehicle_id, current_user)
    return DataQualityReportOut.model_validate(
        compute_data_quality(data.segments, data.refuel_entries)
    )
