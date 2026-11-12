"""Pure, DB-free mileage/odometer engine.

Inputs are plain dataclasses (not ORM models) so this module has no
dependency on SQLAlchemy or a live database and can be exhaustively
unit tested. Callers (API routes, analytics endpoints) map ORM rows
into these dataclasses before calling in.

Every SegmentResult reports distance/km-per-L/Rs-per-km unconditionally,
even for excluded/anomalous segments (useful for the data-quality panel
to show *why* something looks wrong). It is the caller's job to decide
whether to include a given segment's distance-based numbers in an
aggregate, based on `status`: litres and spend always count toward
totals; distance, km/L, and Rs/km only count for `valid`/`estimated`
segments.
"""

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.models.enums import FillType, OdometerEventType, OdometerStatus

MAX_PLAUSIBLE_KM_PER_L = Decimal(45)


class SegmentStatus(StrEnum):
    VALID = "valid"
    EXCLUDED_FAULTY = "excluded_faulty"
    EXCLUDED_ANOMALOUS = "excluded_anomalous"
    ESTIMATED = "estimated"


@dataclass(frozen=True)
class RefuelEntry:
    id: int
    date: dt.date
    odometer_km: Decimal
    litres: Decimal
    amount_rs: Decimal
    price_per_litre: Decimal
    fill_type: FillType
    odometer_status: OdometerStatus = OdometerStatus.OK
    distance_override_km: Decimal | None = None
    location: str | None = None
    station_name: str | None = None


@dataclass(frozen=True)
class FuelRemovedEntry:
    id: int
    date: dt.date
    litres: Decimal


@dataclass(frozen=True)
class OdometerEventData:
    event_type: OdometerEventType
    start_date: dt.date
    end_date: dt.date | None = None
    old_reading_at_change: Decimal | None = None
    new_reading_at_change: Decimal | None = None


@dataclass(frozen=True)
class SegmentResult:
    start_entry_id: int
    end_entry_id: int
    start_date: dt.date
    end_date: dt.date
    raw_distance_km: Decimal
    distance_km: Decimal
    litres_added: Decimal
    litres_removed: Decimal
    net_litres: Decimal
    km_per_l: Decimal | None
    cost_rs: Decimal
    removed_fuel_cost_rs: Decimal
    rs_per_km: Decimal | None
    status: SegmentStatus
    reason: str | None


@dataclass(frozen=True)
class SuggestedFix:
    action: str
    label: str
    prefill: dict[str, Any] | None = None


@dataclass(frozen=True)
class ValidationWarning:
    code: str
    message: str
    suggested_fixes: list[SuggestedFix] = field(default_factory=list)


def effective_odometer(entry: RefuelEntry, odometer_events: Sequence[OdometerEventData]) -> Decimal:
    """Raw reading plus the cumulative offset from every replace/reset at or before this date."""
    offset = Decimal(0)
    for event in odometer_events:
        if (
            event.event_type in (OdometerEventType.REPLACED, OdometerEventType.RESET)
            and event.start_date <= entry.date
        ):
            assert event.old_reading_at_change is not None
            assert event.new_reading_at_change is not None
            offset += event.old_reading_at_change - event.new_reading_at_change
    return entry.odometer_km + offset


def _last_known_price(
    removal_date: dt.date, sorted_refuels: Sequence[RefuelEntry]
) -> Decimal | None:
    candidates = [e for e in sorted_refuels if e.date <= removal_date]
    if not candidates:
        return None
    return max(candidates, key=lambda e: e.date).price_per_litre


def _valued_removed_fuel_cost(
    removals: Sequence[FuelRemovedEntry], price_candidates: Sequence[RefuelEntry]
) -> Decimal:
    return sum(
        (r.litres * (_last_known_price(r.date, price_candidates) or Decimal(0)) for r in removals),
        Decimal(0),
    )


def _overlaps_faulty_period(
    start_date: dt.date, end_date: dt.date, event: OdometerEventData
) -> bool:
    period_end = event.end_date or dt.date.max
    return start_date <= period_end and end_date >= event.start_date


def _segment_status(
    start: RefuelEntry,
    end: RefuelEntry,
    raw_distance_km: Decimal,
    tank_capacity_l: Decimal,
    odometer_events: Sequence[OdometerEventData],
) -> tuple[SegmentStatus, str | None]:
    if end.distance_override_km is not None:
        return SegmentStatus.ESTIMATED, "distance manually overridden"

    if start.odometer_status == OdometerStatus.FAULTY:
        return SegmentStatus.EXCLUDED_FAULTY, f"entry on {start.date} is marked faulty"
    if end.odometer_status == OdometerStatus.FAULTY:
        return SegmentStatus.EXCLUDED_FAULTY, f"entry on {end.date} is marked faulty"

    for event in odometer_events:
        if event.event_type == OdometerEventType.FAULTY_PERIOD and _overlaps_faulty_period(
            start.date, end.date, event
        ):
            return (
                SegmentStatus.EXCLUDED_FAULTY,
                f"overlaps faulty period starting {event.start_date}",
            )

    if raw_distance_km < 0:
        return SegmentStatus.EXCLUDED_ANOMALOUS, "odometer reading decreased (negative distance)"
    if raw_distance_km > tank_capacity_l * MAX_PLAUSIBLE_KM_PER_L:
        return (
            SegmentStatus.EXCLUDED_ANOMALOUS,
            f"distance {raw_distance_km}km exceeds plausible max for a {tank_capacity_l}L tank",
        )

    return SegmentStatus.VALID, None


def compute_segments(
    refuel_entries: Sequence[RefuelEntry],
    fuel_removed_entries: Sequence[FuelRemovedEntry],
    odometer_events: Sequence[OdometerEventData],
    tank_capacity_l: Decimal,
) -> list[SegmentResult]:
    sorted_refuels = sorted(refuel_entries, key=lambda e: (e.date, e.odometer_km))
    full_fills = [e for e in sorted_refuels if e.fill_type == FillType.FULL]

    segments: list[SegmentResult] = []
    for start, end in zip(full_fills, full_fills[1:], strict=False):
        interior_partials = [
            e
            for e in sorted_refuels
            if e.fill_type == FillType.PARTIAL
            and e.id not in (start.id, end.id)
            and start.date <= e.date <= end.date
        ]
        removals_in_segment = [r for r in fuel_removed_entries if start.date < r.date <= end.date]

        raw_distance_km = effective_odometer(end, odometer_events) - effective_odometer(
            start, odometer_events
        )
        status, reason = _segment_status(
            start, end, raw_distance_km, tank_capacity_l, odometer_events
        )
        distance_km = raw_distance_km
        if status == SegmentStatus.ESTIMATED and end.distance_override_km is not None:
            distance_km = end.distance_override_km

        litres_added = end.litres + sum((p.litres for p in interior_partials), Decimal(0))
        litres_removed = sum((r.litres for r in removals_in_segment), Decimal(0))
        net_litres = litres_added - litres_removed

        removed_fuel_cost_rs = _valued_removed_fuel_cost(removals_in_segment, sorted_refuels)
        fill_cost_rs = end.amount_rs + sum((p.amount_rs for p in interior_partials), Decimal(0))
        cost_rs = fill_cost_rs - removed_fuel_cost_rs

        km_per_l = distance_km / net_litres if net_litres > 0 else None
        rs_per_km = cost_rs / distance_km if distance_km != 0 else None

        segments.append(
            SegmentResult(
                start_entry_id=start.id,
                end_entry_id=end.id,
                start_date=start.date,
                end_date=end.date,
                raw_distance_km=raw_distance_km,
                distance_km=distance_km,
                litres_added=litres_added,
                litres_removed=litres_removed,
                net_litres=net_litres,
                km_per_l=km_per_l,
                cost_rs=cost_rs,
                removed_fuel_cost_rs=removed_fuel_cost_rs,
                rs_per_km=rs_per_km,
                status=status,
                reason=reason,
            )
        )

    return segments


def _odometer_fix_suggestions(
    new_entry_date: dt.date, old_effective_reading: Decimal, new_raw_reading: Decimal
) -> list[SuggestedFix]:
    return [
        SuggestedFix(action="mark_faulty", label="Mark this entry as faulty"),
        SuggestedFix(
            action="log_odometer_event",
            label="Log an odometer replacement or reset",
            prefill={
                "event_type": "replaced",
                "old_reading_at_change": str(old_effective_reading),
                "new_reading_at_change": str(new_raw_reading),
                "start_date": new_entry_date.isoformat(),
            },
        ),
        SuggestedFix(action="set_distance_override", label="Enter actual distance manually"),
    ]


def validate_new_refuel(
    new_entry: RefuelEntry,
    previous_entry: RefuelEntry | None,
    tank_capacity_l: Decimal,
    odometer_events: Sequence[OdometerEventData],
) -> list[ValidationWarning]:
    """Non-blocking checks on a new/edited refuel entry. Never raises; callers always save."""
    warnings: list[ValidationWarning] = []

    if new_entry.litres > tank_capacity_l:
        warnings.append(
            ValidationWarning(
                code="litres_exceeds_tank",
                message=f"{new_entry.litres}L exceeds the {tank_capacity_l}L tank capacity.",
            )
        )

    if not (Decimal(60) <= new_entry.price_per_litre <= Decimal(200)):
        warnings.append(
            ValidationWarning(
                code="price_out_of_range",
                message=f"Rs {new_entry.price_per_litre}/L is outside the usual Rs 60–200 range.",
            )
        )

    if previous_entry is not None:
        new_effective = effective_odometer(new_entry, odometer_events)
        prev_effective = effective_odometer(previous_entry, odometer_events)
        delta = new_effective - prev_effective

        if delta < 0:
            warnings.append(
                ValidationWarning(
                    code="odometer_decreased",
                    message=(
                        f"Odometer reading is lower than the previous entry "
                        f"({previous_entry.odometer_km} km on {previous_entry.date})."
                    ),
                    suggested_fixes=_odometer_fix_suggestions(
                        new_entry.date, prev_effective, new_entry.odometer_km
                    ),
                )
            )
        elif delta > tank_capacity_l * MAX_PLAUSIBLE_KM_PER_L:
            warnings.append(
                ValidationWarning(
                    code="implausible_jump",
                    message=(
                        f"Distance since the last fill ({delta} km) is implausible "
                        f"for a {tank_capacity_l}L tank."
                    ),
                    suggested_fixes=_odometer_fix_suggestions(
                        new_entry.date, prev_effective, new_entry.odometer_km
                    ),
                )
            )

    return warnings


def compute_fill_preview(
    new_entry: RefuelEntry,
    previous_full_entry: RefuelEntry | None,
    interior_partials: Sequence[RefuelEntry],
    fuel_removed_entries: Sequence[FuelRemovedEntry],
    odometer_events: Sequence[OdometerEventData],
) -> dict[str, Decimal | None]:
    """What the segment ending at new_entry would look like, for the pre-save preview."""
    if previous_full_entry is None:
        return {"distance_since_last_full_km": None, "km_per_l": None, "rs_per_km": None}

    raw_distance = effective_odometer(new_entry, odometer_events) - effective_odometer(
        previous_full_entry, odometer_events
    )
    distance = (
        new_entry.distance_override_km
        if new_entry.distance_override_km is not None
        else raw_distance
    )

    litres_added = new_entry.litres + sum((p.litres for p in interior_partials), Decimal(0))
    removals_in_window = [
        r for r in fuel_removed_entries if previous_full_entry.date < r.date <= new_entry.date
    ]
    litres_removed = sum((r.litres for r in removals_in_window), Decimal(0))
    net_litres = litres_added - litres_removed

    price_candidates = [previous_full_entry, *interior_partials]
    removed_fuel_cost_rs = _valued_removed_fuel_cost(removals_in_window, price_candidates)
    fill_cost_rs = new_entry.amount_rs + sum((p.amount_rs for p in interior_partials), Decimal(0))
    cost_rs = fill_cost_rs - removed_fuel_cost_rs

    km_per_l = distance / net_litres if net_litres > 0 else None
    rs_per_km = cost_rs / distance if distance != 0 else None

    return {
        "distance_since_last_full_km": distance,
        "km_per_l": km_per_l,
        "rs_per_km": rs_per_km,
    }
