import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.entry_audit import EntryAudit
from app.models.enums import EntryType, OdometerStatus
from app.models.fuel_entry import FuelEntry
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.fuel_entry import (
    EntryCreate,
    EntryListResponse,
    EntryRead,
    EntrySaveResponse,
    EntryUpdate,
    ValidationWarningOut,
)
from app.services.entry_feedback import build_refuel_feedback

router = APIRouter()

SORTABLE_FIELDS = {
    "date",
    "odometer_km",
    "litres",
    "amount_rs",
    "price_per_litre",
    "location",
    "entry_type",
    "odometer_status",
    "created_at",
}


def _get_owned_vehicle(db: Session, vehicle_id: int, user: User) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    return vehicle


def _get_owned_entry(db: Session, vehicle_id: int, entry_id: int) -> FuelEntry:
    entry = db.get(FuelEntry, entry_id)
    if entry is None or entry.vehicle_id != vehicle_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entry not found")
    return entry


def _build_save_response(db: Session, vehicle: Vehicle, entry: FuelEntry) -> EntrySaveResponse:
    entry_read = EntryRead.model_validate(entry)
    if entry.entry_type != EntryType.REFUEL:
        return EntrySaveResponse(entry=entry_read)

    warnings, preview = build_refuel_feedback(db, vehicle, entry)
    return EntrySaveResponse(
        entry=entry_read,
        warnings=[ValidationWarningOut.model_validate(w) for w in warnings],
        preview=preview,
    )


@router.get("", response_model=EntryListResponse)
def list_entries(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    location: str | None = None,
    entry_type: EntryType | None = None,
    odometer_status: OdometerStatus | None = None,
    sort_by: str = "date",
    sort_dir: str = "desc",
) -> EntryListResponse:
    _get_owned_vehicle(db, vehicle_id, current_user)
    if sort_by not in SORTABLE_FIELDS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Cannot sort by '{sort_by}'")

    query = db.query(FuelEntry).filter(FuelEntry.vehicle_id == vehicle_id)
    if date_from is not None:
        query = query.filter(FuelEntry.date >= date_from)
    if date_to is not None:
        query = query.filter(FuelEntry.date <= date_to)
    if location is not None:
        query = query.filter(FuelEntry.location == location)
    if entry_type is not None:
        query = query.filter(FuelEntry.entry_type == entry_type)
    if odometer_status is not None:
        query = query.filter(FuelEntry.odometer_status == odometer_status)

    total = query.count()
    order_fn = asc if sort_dir == "asc" else desc
    query = query.order_by(order_fn(getattr(FuelEntry, sort_by)))
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return EntryListResponse(items=list(items), total=total, page=page, page_size=page_size)


@router.get("/{entry_id}", response_model=EntryRead)
def get_entry(
    vehicle_id: int,
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FuelEntry:
    _get_owned_vehicle(db, vehicle_id, current_user)
    return _get_owned_entry(db, vehicle_id, entry_id)


@router.post("", response_model=EntrySaveResponse, status_code=201)
def create_entry(
    vehicle_id: int,
    payload: EntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntrySaveResponse:
    vehicle = _get_owned_vehicle(db, vehicle_id, current_user)

    data = payload.model_dump()
    data["entry_type"] = EntryType(data["entry_type"])
    entry = FuelEntry(vehicle_id=vehicle_id, **data)
    db.add(entry)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An entry already exists for this vehicle, date, and odometer reading",
        ) from exc
    db.refresh(entry)
    return _build_save_response(db, vehicle, entry)


@router.patch("/{entry_id}", response_model=EntrySaveResponse)
def update_entry(
    vehicle_id: int,
    entry_id: int,
    payload: EntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntrySaveResponse:
    vehicle = _get_owned_vehicle(db, vehicle_id, current_user)
    entry = _get_owned_entry(db, vehicle_id, entry_id)

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return _build_save_response(db, vehicle, entry)

    old_values = EntryRead.model_validate(entry).model_dump(mode="json")
    for field, value in changes.items():
        setattr(entry, field, value)
    db.flush()
    new_values = EntryRead.model_validate(entry).model_dump(mode="json")

    db.add(
        EntryAudit(
            fuel_entry_id=entry.id,
            changed_by=current_user.id,
            old_values=old_values,
            new_values=new_values,
        )
    )
    db.commit()
    db.refresh(entry)
    return _build_save_response(db, vehicle, entry)
