"""Builds the full-data Excel export: Entries, Computed, Odometer events, Summary.

Segments are always computed from the vehicle's *entire* entry history (the
mileage engine needs full context -- a filtered slice would lose the
previous-full-fill anchor for the first included segment). The date filter
only decides which rows/segments are shown in each sheet, not how segments
are computed.
"""

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from openpyxl import Workbook

from app.models.enums import EntryType
from app.models.fuel_entry import FuelEntry
from app.models.odometer_event import OdometerEvent
from app.models.vehicle import Vehicle
from app.services.entry_mapping import (
    to_fuel_removed_entry,
    to_odometer_event_data,
    to_refuel_entry,
)
from app.services.importers.parsed_row import EXCEL_COLUMNS
from app.services.mileage import SegmentResult, SegmentStatus, compute_segments

ENTRIES_SHEET_COLUMNS = [*EXCEL_COLUMNS, "raw_text"]
COMPUTED_SHEET_COLUMNS = [
    "start_date",
    "end_date",
    "distance_km",
    "net_litres",
    "km_per_l",
    "rs_per_l",
    "rs_per_km",
    "status",
    "reason",
]
ODOMETER_EVENTS_SHEET_COLUMNS = [
    "event_type",
    "start_date",
    "end_date",
    "old_reading_at_change",
    "new_reading_at_change",
    "notes",
]
SUMMARY_SHEET_COLUMNS = ["year", "km", "litres", "spend", "avg_km_per_l", "avg_rs_per_l", "fills"]


def _num(value: Decimal | None) -> float | str:
    return float(value) if value is not None else ""


def _date_str(value: dt.date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


@dataclass
class YearlyTotals:
    year: int
    km: Decimal = Decimal(0)
    gross_litres: Decimal = Decimal(0)
    net_litres: Decimal = Decimal(0)
    gross_spend: Decimal = Decimal(0)
    fills: int = 0


def _entries_sheet(workbook: Workbook, entries: Sequence[FuelEntry]) -> None:
    sheet = workbook.active
    sheet.title = "Entries"
    sheet.append(ENTRIES_SHEET_COLUMNS)
    for e in sorted(entries, key=lambda x: (x.date, x.odometer_km or Decimal(0))):
        sheet.append(
            [
                e.entry_type.value,
                _date_str(e.date),
                _num(e.odometer_km),
                _num(e.litres),
                _num(e.amount_rs),
                _num(e.price_per_litre),
                e.fill_type.value if e.fill_type else "",
                e.location or "",
                e.station_name or "",
                e.odometer_status.value,
                _num(e.distance_override_km),
                e.notes or "",
                e.raw_text or "",
            ]
        )


def _computed_sheet(workbook: Workbook, segments: Sequence[SegmentResult]) -> None:
    sheet = workbook.create_sheet("Computed")
    sheet.append(COMPUTED_SHEET_COLUMNS)
    for seg in segments:
        rs_per_l = seg.cost_rs / seg.net_litres if seg.net_litres > 0 else None
        sheet.append(
            [
                _date_str(seg.start_date),
                _date_str(seg.end_date),
                _num(seg.distance_km),
                _num(seg.net_litres),
                _num(seg.km_per_l),
                _num(rs_per_l),
                _num(seg.rs_per_km),
                seg.status.value,
                seg.reason or "",
            ]
        )


def _odometer_events_sheet(workbook: Workbook, events: Sequence[OdometerEvent]) -> None:
    sheet = workbook.create_sheet("Odometer events")
    sheet.append(ODOMETER_EVENTS_SHEET_COLUMNS)
    for event in sorted(events, key=lambda e: e.start_date):
        sheet.append(
            [
                event.event_type.value,
                _date_str(event.start_date),
                _date_str(event.end_date),
                _num(event.old_reading_at_change),
                _num(event.new_reading_at_change),
                event.notes or "",
            ]
        )


def _yearly_totals(
    segments: Sequence[SegmentResult], refuel_entries: Sequence[FuelEntry]
) -> list[YearlyTotals]:
    totals: dict[int, YearlyTotals] = {}

    def _get(year: int) -> YearlyTotals:
        if year not in totals:
            totals[year] = YearlyTotals(year=year)
        return totals[year]

    for seg in segments:
        if seg.status not in (SegmentStatus.VALID, SegmentStatus.ESTIMATED):
            continue
        year_totals = _get(seg.end_date.year)
        year_totals.km += seg.distance_km
        year_totals.net_litres += seg.net_litres
        year_totals.gross_litres += seg.litres_added
        year_totals.gross_spend += seg.cost_rs + seg.removed_fuel_cost_rs

    for entry in refuel_entries:
        _get(entry.date.year).fills += 1

    return sorted(totals.values(), key=lambda t: t.year)


def _summary_sheet(
    workbook: Workbook, segments: Sequence[SegmentResult], refuel_entries: Sequence[FuelEntry]
) -> None:
    sheet = workbook.create_sheet("Summary")
    sheet.append(SUMMARY_SHEET_COLUMNS)
    for yearly in _yearly_totals(segments, refuel_entries):
        avg_km_per_l = yearly.km / yearly.net_litres if yearly.net_litres > 0 else None
        avg_rs_per_l = yearly.gross_spend / yearly.gross_litres if yearly.gross_litres > 0 else None
        sheet.append(
            [
                yearly.year,
                _num(yearly.km),
                _num(yearly.gross_litres),
                _num(yearly.gross_spend),
                _num(avg_km_per_l),
                _num(avg_rs_per_l),
                yearly.fills,
            ]
        )


def build_export_workbook(
    vehicle: Vehicle,
    all_entries: Sequence[FuelEntry],
    odometer_events: Sequence[OdometerEvent],
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> Workbook:
    refuel_entries = [e for e in all_entries if e.entry_type == EntryType.REFUEL]
    removed_entries = [e for e in all_entries if e.entry_type == EntryType.FUEL_REMOVED]
    odometer_event_data = [to_odometer_event_data(e) for e in odometer_events]

    all_segments = compute_segments(
        [to_refuel_entry(e) for e in refuel_entries],
        [to_fuel_removed_entry(e) for e in removed_entries],
        odometer_event_data,
        vehicle.tank_capacity_l,
    )

    def _in_range(d: dt.date) -> bool:
        if date_from is not None and d < date_from:
            return False
        if date_to is not None and d > date_to:
            return False
        return True

    filtered_entries = [e for e in all_entries if _in_range(e.date)]
    filtered_segments = [s for s in all_segments if _in_range(s.end_date)]
    filtered_refuels_for_summary = [e for e in refuel_entries if _in_range(e.date)]

    workbook = Workbook()
    _entries_sheet(workbook, filtered_entries)
    _computed_sheet(workbook, filtered_segments)
    _odometer_events_sheet(workbook, odometer_events)
    _summary_sheet(workbook, filtered_segments, filtered_refuels_for_summary)
    return workbook
