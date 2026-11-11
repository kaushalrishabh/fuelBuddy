from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.odometer_event import OdometerEvent
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.odometer_event import OdometerEventCreate, OdometerEventRead, OdometerEventUpdate

router = APIRouter()


def _get_owned_vehicle(db: Session, vehicle_id: int, user: User) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    return vehicle


@router.get("", response_model=list[OdometerEventRead])
def list_odometer_events(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OdometerEvent]:
    _get_owned_vehicle(db, vehicle_id, current_user)
    return list(
        db.query(OdometerEvent)
        .filter(OdometerEvent.vehicle_id == vehicle_id)
        .order_by(OdometerEvent.start_date)
        .all()
    )


@router.post("", response_model=OdometerEventRead, status_code=201)
def create_odometer_event(
    vehicle_id: int,
    payload: OdometerEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OdometerEvent:
    _get_owned_vehicle(db, vehicle_id, current_user)
    event = OdometerEvent(vehicle_id=vehicle_id, **payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.patch("/{event_id}", response_model=OdometerEventRead)
def update_odometer_event(
    vehicle_id: int,
    event_id: int,
    payload: OdometerEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OdometerEvent:
    _get_owned_vehicle(db, vehicle_id, current_user)
    event = db.get(OdometerEvent, event_id)
    if event is None or event.vehicle_id != vehicle_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Odometer event not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event
