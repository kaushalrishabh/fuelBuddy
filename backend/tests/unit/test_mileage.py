import datetime as dt
from decimal import Decimal

from app.models.enums import FillType, OdometerEventType, OdometerStatus
from app.services.mileage import (
    FuelRemovedEntry,
    OdometerEventData,
    RefuelEntry,
    SegmentStatus,
    compute_fill_preview,
    compute_segments,
    effective_odometer,
    validate_new_refuel,
)

TANK_13 = Decimal(13)


def refuel(
    id: int,
    date: str,
    odometer: str,
    litres: str,
    amount: str,
    price: str | None = None,
    fill_type: FillType = FillType.FULL,
    status: OdometerStatus = OdometerStatus.OK,
    override: str | None = None,
) -> RefuelEntry:
    return RefuelEntry(
        id=id,
        date=dt.date.fromisoformat(date),
        odometer_km=Decimal(odometer),
        litres=Decimal(litres),
        amount_rs=Decimal(amount),
        price_per_litre=Decimal(price)
        if price is not None
        else (Decimal(amount) / Decimal(litres)),
        fill_type=fill_type,
        odometer_status=status,
        distance_override_km=Decimal(override) if override is not None else None,
    )


def removed(id: int, date: str, litres: str) -> FuelRemovedEntry:
    return FuelRemovedEntry(id=id, date=dt.date.fromisoformat(date), litres=Decimal(litres))


def replaced_event(start_date: str, old: str, new: str) -> OdometerEventData:
    return OdometerEventData(
        event_type=OdometerEventType.REPLACED,
        start_date=dt.date.fromisoformat(start_date),
        old_reading_at_change=Decimal(old),
        new_reading_at_change=Decimal(new),
    )


def faulty_period(start_date: str, end_date: str | None) -> OdometerEventData:
    return OdometerEventData(
        event_type=OdometerEventType.FAULTY_PERIOD,
        start_date=dt.date.fromisoformat(start_date),
        end_date=dt.date.fromisoformat(end_date) if end_date else None,
    )


# --- effective_odometer ---------------------------------------------------


def test_effective_odometer_with_no_events_is_unchanged() -> None:
    entry = refuel(1, "2026-01-01", "1000.0", "10", "900")
    assert effective_odometer(entry, []) == Decimal("1000.0")


def test_effective_odometer_applies_offset_from_prior_replacement() -> None:
    entry = refuel(1, "2026-04-10", "500.0", "10", "900")
    event = replaced_event("2026-04-02", "42000", "0")
    assert effective_odometer(entry, [event]) == Decimal("42500.0")


def test_effective_odometer_ignores_event_after_entry_date() -> None:
    entry = refuel(1, "2026-04-01", "42000.0", "10", "900")
    event = replaced_event("2026-04-02", "42000", "0")
    assert effective_odometer(entry, [event]) == Decimal("42000.0")


def test_effective_odometer_applies_event_on_exact_boundary_date() -> None:
    entry = refuel(1, "2026-04-02", "0.0", "10", "900")
    event = replaced_event("2026-04-02", "42000", "0")
    assert effective_odometer(entry, [event]) == Decimal("42000.0")


def test_effective_odometer_composes_sequential_replacements() -> None:
    entry = refuel(1, "2026-06-01", "100.0", "10", "900")
    events = [
        replaced_event("2026-04-02", "42000", "0"),
        replaced_event("2026-05-02", "60000", "0"),
    ]
    assert effective_odometer(entry, events) == Decimal("100.0") + Decimal("42000") + Decimal(
        "60000"
    )


# --- compute_segments: basic math -----------------------------------------


def test_simple_segment_computes_distance_km_per_l_and_rs_per_km() -> None:
    start = refuel(1, "2026-01-01", "1000.0", "10", "900", price="90")
    end = refuel(2, "2026-01-15", "1500.0", "10", "900", price="90")

    segments = compute_segments([start, end], [], [], TANK_13)

    assert len(segments) == 1
    seg = segments[0]
    assert seg.distance_km == Decimal("500.0")
    assert seg.net_litres == Decimal("10")
    assert seg.km_per_l == Decimal("50.0")
    assert seg.cost_rs == Decimal("900")
    assert seg.rs_per_km == Decimal("1.8")
    assert seg.status == SegmentStatus.VALID
    assert seg.reason is None


def test_segment_includes_interior_partial_fill_litres_and_cost() -> None:
    start = refuel(1, "2026-01-01", "1000.0", "10", "900", price="90")
    partial = refuel(2, "2026-01-05", "1200.0", "5", "400", price="80", fill_type=FillType.PARTIAL)
    end = refuel(3, "2026-01-10", "1520.0", "8", "640", price="80")

    segments = compute_segments([start, partial, end], [], [], TANK_13)

    assert len(segments) == 1
    seg = segments[0]
    assert seg.distance_km == Decimal("520.0")
    assert seg.litres_added == Decimal("13")
    assert seg.km_per_l == Decimal("40")
    assert seg.cost_rs == Decimal("1040")
    assert seg.rs_per_km == Decimal("2.0")


# --- compute_segments: fuel removal ----------------------------------------


def test_fuel_removed_inside_segment_reduces_net_litres_and_cost() -> None:
    start = refuel(1, "2026-02-01", "2000.0", "10", "900", price="90")
    end = refuel(2, "2026-02-15", "2500.0", "10", "900", price="90")
    removal = removed(10, "2026-02-08", "2")

    segments = compute_segments([start, end], [removal], [], TANK_13)

    seg = segments[0]
    assert seg.litres_removed == Decimal("2")
    assert seg.net_litres == Decimal("8")
    assert seg.km_per_l == Decimal("62.5")
    assert seg.removed_fuel_cost_rs == Decimal("180")  # 2L at last known price (90/L)
    assert seg.cost_rs == Decimal("720")  # 900 - 180
    assert seg.rs_per_km == Decimal("1.44")


def test_removal_on_start_date_is_not_attributed_to_this_segment() -> None:
    start = refuel(1, "2026-02-01", "2000.0", "10", "900", price="90")
    end = refuel(2, "2026-02-15", "2500.0", "10", "900", price="90")
    removal_on_start = removed(10, "2026-02-01", "2")

    seg = compute_segments([start, end], [removal_on_start], [], TANK_13)[0]
    assert seg.litres_removed == Decimal("0")


def test_removal_on_end_date_is_attributed_to_this_segment() -> None:
    start = refuel(1, "2026-02-01", "2000.0", "10", "900", price="90")
    end = refuel(2, "2026-02-15", "2500.0", "10", "900", price="90")
    removal_on_end = removed(10, "2026-02-15", "2")

    seg = compute_segments([start, end], [removal_on_end], [], TANK_13)[0]
    assert seg.litres_removed == Decimal("2")


def test_net_litres_zero_or_negative_leaves_km_per_l_undefined() -> None:
    start = refuel(1, "2026-02-01", "2000.0", "10", "900", price="90")
    end = refuel(2, "2026-02-15", "2500.0", "5", "450", price="90")
    removal = removed(10, "2026-02-08", "5")  # equals end.litres -> net 0

    seg = compute_segments([start, end], [removal], [], TANK_13)[0]
    assert seg.net_litres == Decimal("0")
    assert seg.km_per_l is None
    assert seg.rs_per_km is not None  # distance is nonzero, cost math still defined


# --- compute_segments: faulty exclusion -------------------------------------


def test_faulty_entry_excludes_segment_but_keeps_litres_and_cost() -> None:
    start = refuel(1, "2026-03-01", "3000.0", "10", "900", price="90", status=OdometerStatus.FAULTY)
    end = refuel(2, "2026-03-15", "3500.0", "10", "900", price="90")

    seg = compute_segments([start, end], [], [], TANK_13)[0]
    assert seg.status == SegmentStatus.EXCLUDED_FAULTY
    assert "faulty" in (seg.reason or "")
    assert seg.litres_added == Decimal("10")
    assert seg.cost_rs == Decimal("900")


def test_open_ended_faulty_period_overlapping_segment_excludes_it() -> None:
    start = refuel(1, "2026-03-01", "3000.0", "10", "900", price="90")
    end = refuel(2, "2026-03-15", "3500.0", "10", "900", price="90")
    period = faulty_period("2026-03-10", None)

    seg = compute_segments([start, end], [], [period], TANK_13)[0]
    assert seg.status == SegmentStatus.EXCLUDED_FAULTY


def test_faulty_period_entirely_before_segment_does_not_exclude_it() -> None:
    start = refuel(1, "2026-03-01", "3000.0", "10", "900", price="90")
    end = refuel(2, "2026-03-15", "3500.0", "10", "900", price="90")
    period = faulty_period("2026-01-01", "2026-01-10")

    seg = compute_segments([start, end], [], [period], TANK_13)[0]
    assert seg.status == SegmentStatus.VALID


# --- compute_segments: anomalous distance -----------------------------------


def test_negative_distance_is_excluded_as_anomalous() -> None:
    start = refuel(1, "2026-04-01", "5000.0", "10", "900", price="90")
    end = refuel(2, "2026-04-10", "4800.0", "10", "900", price="90")

    seg = compute_segments([start, end], [], [], TANK_13)[0]
    assert seg.status == SegmentStatus.EXCLUDED_ANOMALOUS
    assert "negative" in (seg.reason or "")


def test_implausible_jump_is_excluded_as_anomalous() -> None:
    start = refuel(1, "2026-04-01", "1000.0", "10", "900", price="90")
    end = refuel(2, "2026-04-10", "1500.0", "10", "900", price="90")

    seg = compute_segments([start, end], [], [], Decimal(10))[0]  # max plausible = 450km
    assert seg.status == SegmentStatus.EXCLUDED_ANOMALOUS
    assert "exceeds plausible max" in (seg.reason or "")


def test_zero_distance_leaves_rs_per_km_undefined_but_is_not_anomalous() -> None:
    start = refuel(1, "2026-04-01", "1000.0", "10", "900", price="90")
    end = refuel(2, "2026-04-10", "1000.0", "10", "900", price="90")

    seg = compute_segments([start, end], [], [], TANK_13)[0]
    assert seg.status == SegmentStatus.VALID
    assert seg.distance_km == Decimal("0.0")
    assert seg.km_per_l == Decimal("0")
    assert seg.rs_per_km is None


# --- compute_segments: override rescues a faulty/anomalous segment ----------


def test_distance_override_rescues_a_faulty_segment_and_marks_estimated() -> None:
    start = refuel(1, "2026-05-01", "6000.0", "10", "900", price="90", status=OdometerStatus.FAULTY)
    end = refuel(2, "2026-05-15", "6500.0", "10", "900", price="90", override="420")

    seg = compute_segments([start, end], [], [], TANK_13)[0]
    assert seg.status == SegmentStatus.ESTIMATED
    assert seg.distance_km == Decimal("420")
    assert seg.raw_distance_km == Decimal("500.0")  # raw value still reported for diagnostics
    assert seg.km_per_l == Decimal("420") / Decimal("10")


# --- compute_segments: replacement offset prevents a false anomaly ---------


def test_replacement_event_prevents_false_negative_distance() -> None:
    start = refuel(1, "2026-04-01", "42000.0", "10", "900", price="90")
    event = replaced_event("2026-04-02", "42000", "0")
    end = refuel(2, "2026-04-10", "500.0", "10", "900", price="90")

    seg = compute_segments([start, end], [], [event], TANK_13)[0]
    assert seg.status == SegmentStatus.VALID
    assert seg.distance_km == Decimal("500.0")


# --- validate_new_refuel -----------------------------------------------------


def test_validate_new_refuel_no_warnings_for_normal_entry() -> None:
    previous = refuel(1, "2026-01-01", "1000.0", "10", "900", price="90")
    new_entry = refuel(2, "2026-01-10", "1300.0", "10", "900", price="90")

    warnings = validate_new_refuel(new_entry, previous, TANK_13, [])
    assert warnings == []


def test_validate_new_refuel_flags_litres_exceeding_tank() -> None:
    new_entry = refuel(1, "2026-01-10", "1300.0", "20", "1800", price="90")
    warnings = validate_new_refuel(new_entry, None, TANK_13, [])
    assert any(w.code == "litres_exceeds_tank" for w in warnings)


def test_validate_new_refuel_flags_price_out_of_range() -> None:
    new_entry = refuel(1, "2026-01-10", "1300.0", "10", "2500", price="250")
    warnings = validate_new_refuel(new_entry, None, TANK_13, [])
    assert any(w.code == "price_out_of_range" for w in warnings)


def test_validate_new_refuel_flags_odometer_decreased_with_suggested_fixes() -> None:
    previous = refuel(1, "2026-01-01", "1000.0", "10", "900", price="90")
    new_entry = refuel(2, "2026-01-10", "900.0", "10", "900", price="90")

    warnings = validate_new_refuel(new_entry, previous, TANK_13, [])
    warning = next(w for w in warnings if w.code == "odometer_decreased")

    actions = {fix.action for fix in warning.suggested_fixes}
    assert actions == {"mark_faulty", "log_odometer_event", "set_distance_override"}

    log_fix = next(f for f in warning.suggested_fixes if f.action == "log_odometer_event")
    assert log_fix.prefill == {
        "event_type": "replaced",
        "old_reading_at_change": "1000.0",
        "new_reading_at_change": "900.0",
        "start_date": "2026-01-10",
    }


def test_validate_new_refuel_flags_implausible_jump() -> None:
    previous = refuel(1, "2026-01-01", "1000.0", "10", "900", price="90")
    new_entry = refuel(2, "2026-01-10", "2000.0", "10", "900", price="90")  # +1000km on a 13L tank

    warnings = validate_new_refuel(new_entry, previous, TANK_13, [])
    assert any(w.code == "implausible_jump" for w in warnings)


def test_validate_new_refuel_uses_effective_odometer_not_raw() -> None:
    previous = refuel(1, "2026-04-01", "42000.0", "10", "900", price="90")
    event = replaced_event("2026-04-02", "42000", "0")
    new_entry = refuel(2, "2026-04-10", "500.0", "10", "900", price="90")

    warnings = validate_new_refuel(new_entry, previous, TANK_13, [event])
    assert warnings == []


# --- compute_fill_preview ----------------------------------------------------


def test_fill_preview_with_no_previous_full_entry_returns_none() -> None:
    new_entry = refuel(1, "2026-01-01", "1000.0", "10", "900", price="90")
    preview = compute_fill_preview(new_entry, None, [], [], [])
    assert preview == {
        "distance_since_last_full_km": None,
        "km_per_l": None,
        "rs_per_km": None,
    }


def test_fill_preview_computes_distance_mileage_and_cost() -> None:
    previous_full = refuel(1, "2026-01-01", "1000.0", "10", "900", price="90")
    new_entry = refuel(2, "2026-01-15", "1500.0", "10", "900", price="90")

    preview = compute_fill_preview(new_entry, previous_full, [], [], [])
    assert preview["distance_since_last_full_km"] == Decimal("500.0")
    assert preview["km_per_l"] == Decimal("50.0")
    assert preview["rs_per_km"] == Decimal("1.8")


def test_fill_preview_uses_distance_override_when_set() -> None:
    previous_full = refuel(1, "2026-01-01", "1000.0", "10", "900", price="90")
    new_entry = refuel(2, "2026-01-15", "1500.0", "10", "900", price="90", override="300")

    preview = compute_fill_preview(new_entry, previous_full, [], [], [])
    assert preview["distance_since_last_full_km"] == Decimal("300")
    assert preview["km_per_l"] == Decimal("30")


def test_fill_preview_excludes_removed_fuel_from_cost_and_litres() -> None:
    previous_full = refuel(1, "2026-02-01", "2000.0", "10", "900", price="90")
    new_entry = refuel(2, "2026-02-15", "2500.0", "10", "900", price="90")
    removal = removed(10, "2026-02-08", "2")

    preview = compute_fill_preview(new_entry, previous_full, [], [removal], [])
    assert preview["distance_since_last_full_km"] == Decimal("500.0")
    assert preview["km_per_l"] == Decimal("62.5")  # net litres 8, not 10
    assert preview["rs_per_km"] == Decimal("1.44")  # cost net of 2L valued at 90/L
