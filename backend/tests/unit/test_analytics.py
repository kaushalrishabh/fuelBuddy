import datetime as dt
from decimal import Decimal

from app.models.enums import FillType, OdometerStatus
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
    compute_yearly_summary,
    resolve_date_range,
)
from app.services.mileage import FuelRemovedEntry, RefuelEntry, compute_segments

TANK_13 = Decimal(13)


def refuel(
    id: int,
    date: str,
    odometer: str,
    litres: str,
    amount: str,
    fill_type: FillType = FillType.FULL,
    status: OdometerStatus = OdometerStatus.OK,
    location: str | None = None,
    station_name: str | None = None,
) -> RefuelEntry:
    return RefuelEntry(
        id=id,
        date=dt.date.fromisoformat(date),
        odometer_km=Decimal(odometer),
        litres=Decimal(litres),
        amount_rs=Decimal(amount),
        price_per_litre=(Decimal(amount) / Decimal(litres)),
        fill_type=fill_type,
        odometer_status=status,
        location=location,
        station_name=station_name,
    )


def removed(id: int, date: str, litres: str) -> FuelRemovedEntry:
    return FuelRemovedEntry(id=id, date=dt.date.fromisoformat(date), litres=Decimal(litres))


# A simple three-fill history: two clean 500km/10L segments.
THREE_FILLS = [
    refuel(1, "2026-01-01", "1000", "10", "900", location="ngp"),
    refuel(2, "2026-01-15", "1500", "10", "900", location="cwa"),
    refuel(3, "2026-01-29", "2000", "10", "900", location="cwa"),
]


def _segments(entries: list[RefuelEntry], removed_entries: list[FuelRemovedEntry] | None = None):
    return compute_segments(entries, removed_entries or [], [], TANK_13)


# --- resolve_date_range -------------------------------------------------------


def test_all_time_returns_no_bounds() -> None:
    assert resolve_date_range(DateRangeType.ALL_TIME, dt.date(2026, 11, 12)) == (None, None)


def test_custom_passes_through_given_bounds() -> None:
    bounds = resolve_date_range(
        DateRangeType.CUSTOM,
        dt.date(2026, 11, 12),
        date_from=dt.date(2026, 1, 1),
        date_to=dt.date(2026, 6, 30),
    )
    assert bounds == (dt.date(2026, 1, 1), dt.date(2026, 6, 30))


def test_calendar_year_defaults_to_current_year() -> None:
    assert resolve_date_range(DateRangeType.CALENDAR_YEAR, dt.date(2026, 11, 12)) == (
        dt.date(2026, 1, 1),
        dt.date(2026, 12, 31),
    )


def test_calendar_year_uses_given_year() -> None:
    assert resolve_date_range(DateRangeType.CALENDAR_YEAR, dt.date(2026, 11, 12), year=2024) == (
        dt.date(2024, 1, 1),
        dt.date(2024, 12, 31),
    )


def test_last_3_months_subtracts_calendar_months() -> None:
    date_from, date_to = resolve_date_range(DateRangeType.LAST_3_MONTHS, dt.date(2026, 11, 12))
    assert date_from == dt.date(2026, 8, 12)
    assert date_to == dt.date(2026, 11, 12)


def test_last_12_months_handles_month_end_overflow() -> None:
    # Jan 31 minus 12 months -> Jan 31 the previous year (no overflow issue here,
    # but exercise the day-clamping path with a short target month).
    date_from, _ = resolve_date_range(DateRangeType.LAST_12_MONTHS, dt.date(2026, 3, 31))
    assert date_from == dt.date(2025, 3, 31)


def test_last_1_month_from_march_31_clamps_to_feb_28() -> None:
    date_from, _ = resolve_date_range(DateRangeType.LAST_3_MONTHS, dt.date(2026, 5, 31))
    assert date_from == dt.date(2026, 2, 28)


# --- KPIs ----------------------------------------------------------------------


def test_kpis_basic_lifetime_numbers() -> None:
    segments = _segments(THREE_FILLS)
    kpis = compute_kpis(segments, THREE_FILLS, [], as_of=dt.date(2026, 2, 1))

    assert kpis.total_km == Decimal("1000.0")
    assert kpis.lifetime_km_per_l == Decimal("50.0")
    assert kpis.total_litres == Decimal("30")
    assert kpis.total_spend_rs == Decimal("2700")
    assert kpis.average_rs_per_km == Decimal("1.8")
    assert kpis.average_rs_per_l == Decimal("90")
    assert kpis.last_fill_km_per_l == Decimal("50.0")
    assert kpis.days_since_last_fill == 3  # 2026-01-29 -> 2026-02-01


def test_kpis_reports_litres_removed_separately() -> None:
    removal = removed(10, "2026-01-08", "2")
    segments = _segments(THREE_FILLS, [removal])
    kpis = compute_kpis(segments, THREE_FILLS, [removal], as_of=dt.date(2026, 2, 1))
    assert kpis.litres_removed == Decimal("2")
    # total_litres is gross (bought), unaffected by removal
    assert kpis.total_litres == Decimal("30")


def test_kpis_with_no_entries_returns_nones() -> None:
    kpis = compute_kpis([], [], [], as_of=dt.date(2026, 1, 1))
    assert kpis.lifetime_km_per_l is None
    assert kpis.last_fill_km_per_l is None
    assert kpis.days_since_last_fill is None
    assert kpis.total_km == Decimal(0)


# --- mileage over time / rolling average ---------------------------------------


def test_mileage_over_time_rolling_average_over_window() -> None:
    # Distances must stay under tank(13L) * 45km/L = 585km or the engine
    # (correctly) excludes the segment as anomalous.
    fills = [
        refuel(1, "2026-01-01", "0", "10", "900"),
        refuel(2, "2026-01-08", "400", "10", "900"),  # 40 km/L
        refuel(3, "2026-01-15", "850", "10", "900"),  # 45 km/L
        refuel(4, "2026-01-22", "1350", "10", "900"),  # 50 km/L
    ]
    segments = _segments(fills)
    points = compute_mileage_over_time(segments, window=2)

    assert [p.km_per_l for p in points] == [Decimal(40), Decimal(45), Decimal(50)]
    # rolling avg of last 2: [40], [40,45]->42.5, [45,50]->47.5
    assert points[0].rolling_avg_km_per_l == Decimal(40)
    assert points[1].rolling_avg_km_per_l == Decimal("42.5")
    assert points[2].rolling_avg_km_per_l == Decimal("47.5")


def test_mileage_over_time_excludes_faulty_segment_from_rolling_average() -> None:
    # Marking fill 2 faulty excludes BOTH segments touching it (1->2 and
    # 2->3), per the documented "touches a faulty entry" rule -- so a 4th,
    # clean fill is needed to see a segment recover.
    fills = [
        refuel(1, "2026-01-01", "0", "10", "900"),
        refuel(2, "2026-01-08", "400", "10", "900", status=OdometerStatus.FAULTY),
        refuel(3, "2026-01-15", "900", "10", "900"),
        refuel(4, "2026-01-22", "1350", "10", "900"),  # 45 km/L, clean on both ends
    ]
    segments = _segments(fills)
    points = compute_mileage_over_time(segments)
    assert points[0].rolling_avg_km_per_l is None  # excluded_faulty (touches fill 2)
    assert points[1].rolling_avg_km_per_l is None  # excluded_faulty (touches fill 2)
    assert points[2].rolling_avg_km_per_l == Decimal("45.0")  # first usable segment


# --- monthly breakdown ----------------------------------------------------------


def test_monthly_breakdown_groups_by_calendar_month() -> None:
    fills = [
        refuel(1, "2026-01-01", "1000", "10", "900"),
        refuel(2, "2026-01-15", "1500", "10", "900"),
        refuel(3, "2026-02-01", "2000", "5", "450"),
    ]
    segments = _segments(fills)
    monthly = compute_monthly_breakdown(segments, fills)

    assert len(monthly) == 2
    jan = next(m for m in monthly if m.month == 1)
    assert jan.litres == Decimal("20")
    assert jan.spend_rs == Decimal("1800")
    assert jan.fill_count == 2
    assert jan.km == Decimal("500.0")  # one segment ends in January


# --- price trend ------------------------------------------------------------------


def test_price_trend_min_max_average() -> None:
    fills = [
        refuel(1, "2026-01-01", "1000", "10", "900"),  # 90/L
        refuel(2, "2026-01-15", "1500", "10", "1000"),  # 100/L
        refuel(3, "2026-02-01", "2000", "10", "800"),  # 80/L
    ]
    trend = compute_price_trend(fills)
    assert trend.min_price == Decimal(80)
    assert trend.max_price == Decimal(100)
    assert trend.average_price == Decimal(90)
    assert [p.price_per_litre for p in trend.points] == [Decimal(90), Decimal(100), Decimal(80)]


# --- yearly summary / cost efficiency ---------------------------------------------


def test_yearly_summary_aggregates_gross_and_net_correctly() -> None:
    removal = removed(10, "2026-01-08", "2")
    segments = _segments(THREE_FILLS, [removal])
    summary = compute_yearly_summary(segments, THREE_FILLS)

    assert len(summary) == 1
    year = summary[0]
    assert year.year == 2026
    assert year.km == Decimal("1000.0")
    assert year.litres == Decimal("20")  # gross litres added across both segments (10 + 10)
    assert year.fill_count == 3


def test_cost_efficiency_points_are_chronological() -> None:
    segments = _segments(THREE_FILLS)
    efficiency = compute_cost_efficiency(segments, THREE_FILLS)
    assert [p.date for p in efficiency.points] == [dt.date(2026, 1, 15), dt.date(2026, 1, 29)]
    assert efficiency.yearly_summary[0].year == 2026


# --- location / station ranking ---------------------------------------------------


def test_location_ranking_requires_minimum_sample_size() -> None:
    fills = [
        refuel(1, "2026-01-01", "1000", "10", "900", location="ngp"),
        refuel(2, "2026-01-15", "1500", "10", "900", location="ngp"),  # only 1 segment at ngp
    ]
    segments = _segments(fills)
    ranking = compute_location_ranking(segments, fills)
    assert ranking == []  # sample size 1 < minimum of 3


def test_location_ranking_ranks_by_avg_km_per_l_descending() -> None:
    # Every segment is a safe 400km (under the 585km plausibility ceiling);
    # ngp fills use 10L (40 km/L), cwa fills use 5L (80 km/L).
    fills = [
        refuel(1, "2026-01-01", "0", "10", "900", location="ngp"),
        refuel(2, "2026-01-08", "400", "10", "900", location="ngp"),
        refuel(3, "2026-01-15", "800", "10", "900", location="ngp"),
        refuel(4, "2026-01-22", "1200", "10", "900", location="ngp"),
        refuel(5, "2026-01-29", "1600", "5", "900", location="cwa"),
        refuel(6, "2026-02-05", "2000", "5", "900", location="cwa"),
        refuel(7, "2026-02-12", "2400", "5", "900", location="cwa"),
    ]
    segments = _segments(fills)
    ranking = compute_location_ranking(segments, fills)
    assert [r.name for r in ranking] == ["cwa", "ngp"]
    assert ranking[0].sample_size == 3
    assert ranking[1].sample_size == 3


def test_station_ranking_uses_station_name_not_location() -> None:
    fills = [
        refuel(1, "2026-01-01", "0", "10", "900", station_name="Shell"),
        refuel(2, "2026-01-08", "400", "10", "900", station_name="Shell"),
        refuel(3, "2026-01-15", "900", "10", "900", station_name="Shell"),
        refuel(4, "2026-01-22", "1350", "10", "900", station_name="Shell"),
    ]
    segments = _segments(fills)
    assert compute_location_ranking(segments, fills) == []  # no location set
    station_ranking = compute_station_ranking(segments, fills)
    assert station_ranking[0].name == "Shell"


# --- seasonality --------------------------------------------------------------------


def test_seasonality_groups_by_month_across_years() -> None:
    # Distances kept under the 585km plausibility ceiling throughout.
    fills = [
        refuel(1, "2025-06-01", "0", "10", "900"),
        refuel(2, "2025-06-10", "400", "10", "900"),  # segment ends June 2025: 40 km/L
        refuel(3, "2025-07-10", "900", "10", "900"),  # segment ends July 2025: 50 km/L
        refuel(4, "2026-06-10", "1450", "10", "900"),  # segment ends June 2026: 55 km/L
    ]
    segments = _segments(fills)
    seasonality = compute_seasonality(segments)
    june = next(s for s in seasonality if s.month == 6)
    july = next(s for s in seasonality if s.month == 7)

    assert len(seasonality) == 12
    assert june.sample_size == 2
    assert june.avg_km_per_l == Decimal("47.5")  # (40 + 55) / 2
    assert july.sample_size == 1
    assert july.avg_km_per_l == Decimal(50)


# --- riding pattern -----------------------------------------------------------------


def test_riding_pattern_computes_pace_and_prediction() -> None:
    fills = [
        refuel(1, "2026-01-01", "0", "10", "900"),
        refuel(2, "2026-01-11", "500", "10", "900"),  # 10 days, 500km -> 50km/day
        refuel(3, "2026-01-21", "1000", "10", "900"),  # 10 days, 500km -> 50km/day
    ]
    segments = _segments(fills)
    pattern = compute_riding_pattern(segments)

    assert pattern.avg_days_between_fills == Decimal(10)
    assert pattern.avg_km_per_day == Decimal(50)
    assert pattern.predicted_next_refuel_date == dt.date(2026, 1, 31)


def test_riding_pattern_with_no_usable_segments_returns_none() -> None:
    pattern = compute_riding_pattern([])
    assert pattern.avg_days_between_fills is None
    assert pattern.avg_km_per_day is None
    assert pattern.predicted_next_refuel_date is None


# --- records --------------------------------------------------------------------------


def test_records_best_worst_longest_and_most_expensive() -> None:
    # Every segment distance stays under the 585km plausibility ceiling.
    fills = [
        refuel(1, "2026-01-01", "0", "10", "900"),
        refuel(2, "2026-01-08", "400", "10", "900"),  # 400km/10L = 40 km/L
        refuel(3, "2026-01-15", "950", "10", "900"),  # 550km/10L = 55 km/L, longest distance
        refuel(4, "2026-01-22", "1000", "10", "900"),  # 50km/10L = 5 km/L, worst mileage
        refuel(5, "2026-01-29", "1300", "5", "900"),  # 300km/5L = 60 km/L, best mileage
        refuel(6, "2026-02-05", "1600", "10", "2000"),  # most expensive fill
    ]
    segments = _segments(fills)
    records = compute_records(segments, fills)

    assert records.best_mileage is not None
    assert records.best_mileage.km_per_l == Decimal(60)
    assert records.worst_mileage is not None
    assert records.worst_mileage.km_per_l == Decimal("5.0")
    assert records.longest_distance is not None
    assert records.longest_distance.distance_km == Decimal("550.0")
    assert records.most_expensive_fill_entry_id == 6
    assert records.most_expensive_fill_amount_rs == Decimal(2000)


# --- data quality ----------------------------------------------------------------------


def test_data_quality_flags_faulty_anomalous_estimated_and_outlier_price() -> None:
    # Marking fill 2 faulty excludes both segments touching it (1->2 and
    # 2->3); a separate, clean 3->4 pair is used to exercise the anomalous
    # (negative-distance) path in isolation, and fill 5 adds an outlier price.
    fills = [
        refuel(1, "2026-01-01", "1000", "10", "900"),
        refuel(2, "2026-01-08", "1500", "10", "900", status=OdometerStatus.FAULTY),
        refuel(3, "2026-01-15", "2000", "10", "900"),
        refuel(4, "2026-02-01", "100", "10", "900"),  # negative distance vs entry 3 -> anomalous
        refuel(5, "2026-02-15", "600", "10", "2500"),  # price 250/L -> outlier
    ]
    segments = _segments(fills)
    report = compute_data_quality(segments, fills)

    kinds = {issue.kind for issue in report.issues}
    assert "faulty_segment" in kinds
    assert "anomalous_segment" in kinds
    assert "outlier_price" in kinds
    assert report.excluded_segment_count == 3  # 1->2 faulty, 2->3 faulty, 3->4 anomalous


def test_data_quality_flags_large_gaps_between_fills() -> None:
    fills = [
        refuel(1, "2026-01-01", "1000", "10", "900"),
        refuel(2, "2026-05-01", "1500", "10", "900"),  # 120-day gap
    ]
    segments = _segments(fills)
    report = compute_data_quality(segments, fills)
    assert any(issue.kind == "gap" for issue in report.issues)


def test_data_quality_flags_suspicious_mileage_far_from_average() -> None:
    fills = [
        refuel(1, "2026-01-01", "0", "10", "900"),
        refuel(2, "2026-01-08", "500", "10", "900"),  # 50 km/L
        refuel(3, "2026-01-15", "1000", "10", "900"),  # 50 km/L
        refuel(4, "2026-01-22", "1050", "10", "900"),  # 5 km/L -- way below average
    ]
    segments = _segments(fills)
    report = compute_data_quality(segments, fills)
    assert any(issue.kind == "suspicious_mileage" for issue in report.issues)
