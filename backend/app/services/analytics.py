"""Pure analytics functions over SegmentResult + raw entries.

Like mileage.py, everything here is DB-free and unit-tested directly. The
API layer (app/api/analytics.py) loads entries, runs compute_segments once
over the vehicle's *full* history, resolves the requested date range, and
calls into these functions -- never recomputing segment math itself.

"Usable" segments (valid or estimated) are the only ones whose distance,
km/L, or Rs/km feed into any aggregate here; excluded segments are left
out of every metric except the data-quality report, which exists to
surface them.
"""

import datetime as dt
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from app.services.mileage import FuelRemovedEntry, RefuelEntry, SegmentResult, SegmentStatus

USABLE_STATUSES = (SegmentStatus.VALID, SegmentStatus.ESTIMATED)
MIN_PRICE_RS = Decimal(60)
MAX_PRICE_RS = Decimal(200)
MIN_SAMPLE_SIZE_FOR_RANKING = 3
GAP_WARNING_DAYS = 60
SUSPICIOUS_MILEAGE_LOW = Decimal("0.5")
SUSPICIOUS_MILEAGE_HIGH = Decimal("1.5")


def _usable(segments: Sequence[SegmentResult]) -> list[SegmentResult]:
    return [s for s in segments if s.status in USABLE_STATUSES]


def _average(values: Sequence[Decimal]) -> Decimal | None:
    return sum(values, Decimal(0)) / len(values) if values else None


# --- date range resolution ---------------------------------------------------


class DateRangeType(StrEnum):
    LAST_3_MONTHS = "last_3_months"
    LAST_6_MONTHS = "last_6_months"
    LAST_12_MONTHS = "last_12_months"
    CALENDAR_YEAR = "calendar_year"
    ALL_TIME = "all_time"
    CUSTOM = "custom"


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (dt.date(year, month + 1, 1) - dt.date(year, month, 1)).days


def _subtract_months(d: dt.date, months: int) -> dt.date:
    month_index = d.month - 1 - months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, _days_in_month(year, month))
    return dt.date(year, month, day)


def resolve_date_range(
    range_type: DateRangeType,
    today: dt.date,
    year: int | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> tuple[dt.date | None, dt.date | None]:
    if range_type == DateRangeType.ALL_TIME:
        return None, None
    if range_type == DateRangeType.CUSTOM:
        return date_from, date_to
    if range_type == DateRangeType.CALENDAR_YEAR:
        y = year or today.year
        return dt.date(y, 1, 1), dt.date(y, 12, 31)

    months_back = {
        DateRangeType.LAST_3_MONTHS: 3,
        DateRangeType.LAST_6_MONTHS: 6,
        DateRangeType.LAST_12_MONTHS: 12,
    }[range_type]
    return _subtract_months(today, months_back), today


# --- KPIs ---------------------------------------------------------------------


@dataclass(frozen=True)
class KPIs:
    lifetime_km_per_l: Decimal | None
    last_fill_km_per_l: Decimal | None
    total_km: Decimal
    total_litres: Decimal
    litres_removed: Decimal
    total_spend_rs: Decimal
    average_rs_per_km: Decimal | None
    average_rs_per_l: Decimal | None
    days_since_last_fill: int | None


def compute_kpis(
    segments: Sequence[SegmentResult],
    refuel_entries: Sequence[RefuelEntry],
    removed_entries: Sequence[FuelRemovedEntry],
    as_of: dt.date,
) -> KPIs:
    usable = _usable(segments)
    total_km = sum((s.distance_km for s in usable), Decimal(0))
    total_net_litres = sum((s.net_litres for s in usable), Decimal(0))
    total_riding_cost = sum((s.cost_rs for s in usable), Decimal(0))

    total_litres = sum((e.litres for e in refuel_entries), Decimal(0))
    litres_removed = sum((e.litres for e in removed_entries), Decimal(0))
    total_spend = sum((e.amount_rs for e in refuel_entries), Decimal(0))

    last_usable = max(usable, key=lambda s: s.end_date, default=None)
    last_entry = max(refuel_entries, key=lambda e: e.date, default=None)

    return KPIs(
        lifetime_km_per_l=total_km / total_net_litres if total_net_litres > 0 else None,
        last_fill_km_per_l=last_usable.km_per_l if last_usable else None,
        total_km=total_km,
        total_litres=total_litres,
        litres_removed=litres_removed,
        total_spend_rs=total_spend,
        average_rs_per_km=total_riding_cost / total_km if total_km > 0 else None,
        average_rs_per_l=total_spend / total_litres if total_litres > 0 else None,
        days_since_last_fill=(as_of - last_entry.date).days if last_entry else None,
    )


# --- mileage over time ---------------------------------------------------------


@dataclass(frozen=True)
class MileagePoint:
    date: dt.date
    km_per_l: Decimal | None
    rolling_avg_km_per_l: Decimal | None
    status: SegmentStatus


def compute_mileage_over_time(
    segments: Sequence[SegmentResult], window: int = 5
) -> list[MileagePoint]:
    ordered = sorted(segments, key=lambda s: s.end_date)
    points: list[MileagePoint] = []
    usable_km_per_l: list[Decimal] = []

    for seg in ordered:
        rolling_avg = None
        if seg.status in USABLE_STATUSES and seg.km_per_l is not None:
            usable_km_per_l.append(seg.km_per_l)
            rolling_avg = _average(usable_km_per_l[-window:])
        points.append(
            MileagePoint(
                date=seg.end_date,
                km_per_l=seg.km_per_l,
                rolling_avg_km_per_l=rolling_avg,
                status=seg.status,
            )
        )
    return points


# --- monthly breakdown ---------------------------------------------------------


@dataclass(frozen=True)
class MonthlyPoint:
    year: int
    month: int
    litres: Decimal
    spend_rs: Decimal
    km: Decimal
    fill_count: int


def compute_monthly_breakdown(
    segments: Sequence[SegmentResult], refuel_entries: Sequence[RefuelEntry]
) -> list[MonthlyPoint]:
    km_by_month: dict[tuple[int, int], Decimal] = {}
    for seg in _usable(segments):
        key = (seg.end_date.year, seg.end_date.month)
        km_by_month[key] = km_by_month.get(key, Decimal(0)) + seg.distance_km

    litres_by_month: dict[tuple[int, int], Decimal] = {}
    spend_by_month: dict[tuple[int, int], Decimal] = {}
    count_by_month: dict[tuple[int, int], int] = {}
    for entry in refuel_entries:
        key = (entry.date.year, entry.date.month)
        litres_by_month[key] = litres_by_month.get(key, Decimal(0)) + entry.litres
        spend_by_month[key] = spend_by_month.get(key, Decimal(0)) + entry.amount_rs
        count_by_month[key] = count_by_month.get(key, 0) + 1

    all_keys = sorted(set(km_by_month) | set(litres_by_month))
    return [
        MonthlyPoint(
            year=y,
            month=m,
            litres=litres_by_month.get((y, m), Decimal(0)),
            spend_rs=spend_by_month.get((y, m), Decimal(0)),
            km=km_by_month.get((y, m), Decimal(0)),
            fill_count=count_by_month.get((y, m), 0),
        )
        for y, m in all_keys
    ]


# --- price trend ----------------------------------------------------------------


@dataclass(frozen=True)
class PricePoint:
    date: dt.date
    price_per_litre: Decimal


@dataclass(frozen=True)
class PriceTrend:
    points: list[PricePoint]
    min_price: Decimal | None
    max_price: Decimal | None
    average_price: Decimal | None


def compute_price_trend(refuel_entries: Sequence[RefuelEntry]) -> PriceTrend:
    ordered = sorted(refuel_entries, key=lambda e: e.date)
    points = [PricePoint(date=e.date, price_per_litre=e.price_per_litre) for e in ordered]
    prices = [p.price_per_litre for p in points]
    return PriceTrend(
        points=points,
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
        average_price=_average(prices),
    )


# --- yearly summary (shared with the Excel export) ----------------------------


@dataclass(frozen=True)
class YearlySummary:
    year: int
    km: Decimal
    litres: Decimal  # gross litres bought
    spend_rs: Decimal  # gross spend
    avg_km_per_l: Decimal | None  # km / net litres actually consumed riding
    avg_rs_per_l: Decimal | None  # gross spend / gross litres (average pump price)
    fill_count: int


def compute_yearly_summary(
    segments: Sequence[SegmentResult], refuel_entries: Sequence[RefuelEntry]
) -> list[YearlySummary]:
    km_by_year: dict[int, Decimal] = {}
    net_litres_by_year: dict[int, Decimal] = {}
    gross_litres_by_year: dict[int, Decimal] = {}
    gross_spend_by_year: dict[int, Decimal] = {}
    for seg in _usable(segments):
        y = seg.end_date.year
        km_by_year[y] = km_by_year.get(y, Decimal(0)) + seg.distance_km
        net_litres_by_year[y] = net_litres_by_year.get(y, Decimal(0)) + seg.net_litres
        gross_litres_by_year[y] = gross_litres_by_year.get(y, Decimal(0)) + seg.litres_added
        gross_spend_by_year[y] = (
            gross_spend_by_year.get(y, Decimal(0)) + seg.cost_rs + seg.removed_fuel_cost_rs
        )

    fill_count_by_year: dict[int, int] = {}
    for entry in refuel_entries:
        fill_count_by_year[entry.date.year] = fill_count_by_year.get(entry.date.year, 0) + 1

    years = sorted(set(km_by_year) | set(fill_count_by_year))
    summaries = []
    for y in years:
        km = km_by_year.get(y, Decimal(0))
        net_litres = net_litres_by_year.get(y, Decimal(0))
        gross_litres = gross_litres_by_year.get(y, Decimal(0))
        gross_spend = gross_spend_by_year.get(y, Decimal(0))
        summaries.append(
            YearlySummary(
                year=y,
                km=km,
                litres=gross_litres,
                spend_rs=gross_spend,
                avg_km_per_l=(km / net_litres) if net_litres > 0 else None,
                avg_rs_per_l=(gross_spend / gross_litres) if gross_litres > 0 else None,
                fill_count=fill_count_by_year.get(y, 0),
            )
        )
    return summaries


# --- cost efficiency -------------------------------------------------------------


@dataclass(frozen=True)
class CostEfficiencyPoint:
    date: dt.date
    rs_per_km: Decimal | None


@dataclass(frozen=True)
class CostEfficiency:
    points: list[CostEfficiencyPoint]
    yearly_summary: list[YearlySummary]


def compute_cost_efficiency(
    segments: Sequence[SegmentResult], refuel_entries: Sequence[RefuelEntry]
) -> CostEfficiency:
    ordered = sorted(_usable(segments), key=lambda s: s.end_date)
    points = [CostEfficiencyPoint(date=s.end_date, rs_per_km=s.rs_per_km) for s in ordered]
    return CostEfficiency(
        points=points, yearly_summary=compute_yearly_summary(segments, refuel_entries)
    )


# --- location / station ranking --------------------------------------------------


@dataclass(frozen=True)
class RankedPlace:
    name: str
    sample_size: int
    avg_km_per_l: Decimal
    avg_rs_per_l: Decimal | None


def _rank_places(
    segments: Sequence[SegmentResult],
    refuel_entries: Sequence[RefuelEntry],
    key: Callable[[RefuelEntry], str | None],
) -> list[RankedPlace]:
    entries_by_id = {e.id: e for e in refuel_entries}
    grouped: dict[str, list[SegmentResult]] = {}

    for seg in _usable(segments):
        if seg.km_per_l is None:
            continue
        entry = entries_by_id.get(seg.end_entry_id)
        place = key(entry) if entry else None
        if not place:
            continue
        grouped.setdefault(place, []).append(seg)

    results = []
    for place, segs in grouped.items():
        if len(segs) < MIN_SAMPLE_SIZE_FOR_RANKING:
            continue
        km_per_l_values = [s.km_per_l for s in segs if s.km_per_l is not None]
        rs_per_l_values = [s.cost_rs / s.net_litres for s in segs if s.net_litres > 0]
        avg_km_per_l = _average(km_per_l_values)
        assert avg_km_per_l is not None  # guaranteed by the km_per_l is None check above
        results.append(
            RankedPlace(
                name=place,
                sample_size=len(segs),
                avg_km_per_l=avg_km_per_l,
                avg_rs_per_l=_average(rs_per_l_values),
            )
        )

    return sorted(results, key=lambda r: r.avg_km_per_l, reverse=True)


def compute_location_ranking(
    segments: Sequence[SegmentResult], refuel_entries: Sequence[RefuelEntry]
) -> list[RankedPlace]:
    return _rank_places(segments, refuel_entries, lambda e: e.location)


def compute_station_ranking(
    segments: Sequence[SegmentResult], refuel_entries: Sequence[RefuelEntry]
) -> list[RankedPlace]:
    return _rank_places(segments, refuel_entries, lambda e: e.station_name)


# --- seasonality -----------------------------------------------------------------


@dataclass(frozen=True)
class SeasonalityPoint:
    month: int  # 1-12
    avg_km_per_l: Decimal | None
    sample_size: int


def compute_seasonality(segments: Sequence[SegmentResult]) -> list[SeasonalityPoint]:
    by_month: dict[int, list[Decimal]] = {m: [] for m in range(1, 13)}
    for seg in _usable(segments):
        if seg.km_per_l is not None:
            by_month[seg.end_date.month].append(seg.km_per_l)

    return [
        SeasonalityPoint(month=m, avg_km_per_l=_average(values), sample_size=len(values))
        for m, values in sorted(by_month.items())
    ]


# --- riding pattern ---------------------------------------------------------------


@dataclass(frozen=True)
class RidingPattern:
    avg_days_between_fills: Decimal | None
    avg_km_per_day: Decimal | None
    predicted_next_refuel_date: dt.date | None


def compute_riding_pattern(
    segments: Sequence[SegmentResult], recent_window: int = 3
) -> RidingPattern:
    usable = sorted(_usable(segments), key=lambda s: s.end_date)
    paced = [s for s in usable if (s.end_date - s.start_date).days > 0]

    if not paced:
        return RidingPattern(None, None, None)

    days_between = [Decimal((s.end_date - s.start_date).days) for s in paced]
    km_per_day = [s.distance_km / Decimal((s.end_date - s.start_date).days) for s in paced]

    recent = paced[-recent_window:]
    recent_days_between = _average([Decimal((s.end_date - s.start_date).days) for s in recent])
    assert recent_days_between is not None

    return RidingPattern(
        avg_days_between_fills=_average(days_between),
        avg_km_per_day=_average(km_per_day),
        predicted_next_refuel_date=usable[-1].end_date
        + dt.timedelta(days=round(recent_days_between)),
    )


# --- records ------------------------------------------------------------------------


@dataclass(frozen=True)
class Records:
    best_mileage: SegmentResult | None
    worst_mileage: SegmentResult | None
    longest_distance: SegmentResult | None
    most_expensive_fill_entry_id: int | None
    most_expensive_fill_amount_rs: Decimal | None


def _km_per_l_key(segment: SegmentResult) -> Decimal:
    assert segment.km_per_l is not None
    return segment.km_per_l


def compute_records(
    segments: Sequence[SegmentResult], refuel_entries: Sequence[RefuelEntry]
) -> Records:
    with_mileage = [s for s in _usable(segments) if s.km_per_l is not None]
    best = max(with_mileage, key=_km_per_l_key, default=None)
    worst = min(with_mileage, key=_km_per_l_key, default=None)
    longest = max(_usable(segments), key=lambda s: s.distance_km, default=None)
    most_expensive = max(refuel_entries, key=lambda e: e.amount_rs, default=None)

    return Records(
        best_mileage=best,
        worst_mileage=worst,
        longest_distance=longest,
        most_expensive_fill_entry_id=most_expensive.id if most_expensive else None,
        most_expensive_fill_amount_rs=most_expensive.amount_rs if most_expensive else None,
    )


# --- data quality panel -------------------------------------------------------------


@dataclass(frozen=True)
class DataQualityIssue:
    kind: str
    message: str
    entry_ids: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class DataQualityReport:
    issues: list[DataQualityIssue]
    excluded_segment_count: int
    estimated_segment_count: int


def compute_data_quality(
    segments: Sequence[SegmentResult], refuel_entries: Sequence[RefuelEntry]
) -> DataQualityReport:
    issues: list[DataQualityIssue] = []
    excluded_count = 0
    estimated_count = 0

    lifetime_avg = _average([s.km_per_l for s in _usable(segments) if s.km_per_l is not None])

    for seg in segments:
        if seg.status == SegmentStatus.EXCLUDED_ANOMALOUS:
            excluded_count += 1
            issues.append(
                DataQualityIssue(
                    kind="anomalous_segment",
                    message=f"{seg.start_date} → {seg.end_date}: {seg.reason}",
                    entry_ids=[seg.start_entry_id, seg.end_entry_id],
                )
            )
        elif seg.status == SegmentStatus.EXCLUDED_FAULTY:
            excluded_count += 1
            issues.append(
                DataQualityIssue(
                    kind="faulty_segment",
                    message=f"{seg.start_date} → {seg.end_date}: {seg.reason}",
                    entry_ids=[seg.start_entry_id, seg.end_entry_id],
                )
            )
        elif seg.status == SegmentStatus.ESTIMATED:
            estimated_count += 1
            issues.append(
                DataQualityIssue(
                    kind="estimated_segment",
                    message=f"{seg.start_date} → {seg.end_date}: {seg.reason}",
                    entry_ids=[seg.start_entry_id, seg.end_entry_id],
                )
            )
        elif lifetime_avg is not None and seg.km_per_l is not None:
            if (
                seg.km_per_l < lifetime_avg * SUSPICIOUS_MILEAGE_LOW
                or seg.km_per_l > lifetime_avg * SUSPICIOUS_MILEAGE_HIGH
            ):
                issues.append(
                    DataQualityIssue(
                        kind="suspicious_mileage",
                        message=(
                            f"{seg.end_date}: {seg.km_per_l} km/L is far from the lifetime "
                            f"average ({lifetime_avg:.1f})"
                        ),
                        entry_ids=[seg.end_entry_id],
                    )
                )

    for entry in refuel_entries:
        if not (MIN_PRICE_RS <= entry.price_per_litre <= MAX_PRICE_RS):
            issues.append(
                DataQualityIssue(
                    kind="outlier_price",
                    message=(
                        f"{entry.date}: Rs {entry.price_per_litre}/L is outside the usual range"
                    ),
                    entry_ids=[entry.id],
                )
            )

    ordered_entries = sorted(refuel_entries, key=lambda e: e.date)
    for prev, curr in zip(ordered_entries, ordered_entries[1:], strict=False):
        gap_days = (curr.date - prev.date).days
        if gap_days > GAP_WARNING_DAYS:
            issues.append(
                DataQualityIssue(
                    kind="gap",
                    message=f"{gap_days}-day gap between fills on {prev.date} and {curr.date}",
                    entry_ids=[prev.id, curr.id],
                )
            )

    return DataQualityReport(
        issues=issues,
        excluded_segment_count=excluded_count,
        estimated_segment_count=estimated_count,
    )
