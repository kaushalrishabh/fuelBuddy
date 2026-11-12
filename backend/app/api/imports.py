from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.fuel_entry import FuelEntry
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.imports import (
    ImportCommitRequest,
    ImportCommitResponse,
    ImportPreviewResponse,
    ParsedRowOut,
    RawTextPreviewRequest,
)
from app.services.importers.commit import commit_rows
from app.services.importers.dedup import mark_duplicates
from app.services.importers.excel_importer import build_import_template, parse_excel_file
from app.services.importers.parsed_row import ParsedRow
from app.services.importers.raw_text_parser import parse_raw_text

router = APIRouter()


def _get_owned_vehicle(db: Session, vehicle_id: int, user: User) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    return vehicle


def _build_preview_response(
    db: Session, vehicle_id: int, rows: list[ParsedRow]
) -> ImportPreviewResponse:
    existing = db.query(FuelEntry).filter(FuelEntry.vehicle_id == vehicle_id).all()
    mark_duplicates(rows, existing)

    return ImportPreviewResponse(
        rows=[ParsedRowOut.model_validate(r) for r in rows],
        valid_count=sum(1 for r in rows if not r.errors and not r.is_duplicate),
        warning_count=sum(1 for r in rows if r.warnings),
        error_count=sum(1 for r in rows if r.errors),
        duplicate_count=sum(1 for r in rows if r.is_duplicate),
    )


@router.post("/raw-text/preview", response_model=ImportPreviewResponse)
def preview_raw_text(
    vehicle_id: int,
    payload: RawTextPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportPreviewResponse:
    _get_owned_vehicle(db, vehicle_id, current_user)
    rows = parse_raw_text(payload.text, payload.start_year)
    return _build_preview_response(db, vehicle_id, rows)


@router.post("/excel/preview", response_model=ImportPreviewResponse)
async def preview_excel(
    vehicle_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportPreviewResponse:
    _get_owned_vehicle(db, vehicle_id, current_user)
    file_bytes = await file.read()
    rows = parse_excel_file(file_bytes)
    return _build_preview_response(db, vehicle_id, rows)


@router.post("/commit", response_model=ImportCommitResponse)
def commit_import(
    vehicle_id: int,
    payload: ImportCommitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportCommitResponse:
    _get_owned_vehicle(db, vehicle_id, current_user)
    rows = [ParsedRow(**row_out.model_dump()) for row_out in payload.rows]

    # Duplicate status is recomputed server-side against the current DB
    # state, never trusted from the client (the preview could be stale).
    existing = db.query(FuelEntry).filter(FuelEntry.vehicle_id == vehicle_id).all()
    mark_duplicates(rows, existing)

    result = commit_rows(db, vehicle_id, rows, skip_duplicates=payload.skip_duplicates)
    return ImportCommitResponse(
        imported=result.imported,
        skipped_duplicates=result.skipped_duplicates,
        skipped_errors=result.skipped_errors,
    )


@router.get("/template.xlsx")
def download_template(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _get_owned_vehicle(db, vehicle_id, current_user)
    buffer = BytesIO()
    build_import_template().save(buffer)
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=FuelBuddy_import_template.xlsx"},
    )
