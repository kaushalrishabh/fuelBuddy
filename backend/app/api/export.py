import datetime as dt
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.fuel_entry import FuelEntry
from app.models.odometer_event import OdometerEvent
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.export import build_export_workbook

router = APIRouter()


@router.get("/export.xlsx")
def export_vehicle_data(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> Response:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")

    all_entries = db.query(FuelEntry).filter(FuelEntry.vehicle_id == vehicle_id).all()
    odometer_events = db.query(OdometerEvent).filter(OdometerEvent.vehicle_id == vehicle_id).all()

    workbook = build_export_workbook(vehicle, all_entries, odometer_events, date_from, date_to)
    buffer = BytesIO()
    workbook.save(buffer)

    filename = f"FuelBuddy_export_{dt.date.today().isoformat()}.xlsx"
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
