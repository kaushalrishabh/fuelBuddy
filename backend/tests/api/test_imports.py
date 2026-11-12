from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from app.models.vehicle import Vehicle
from app.services.importers.parsed_row import EXCEL_COLUMNS

SAMPLE_TEXT = (
    "12.50 lt - 1000rs - 3767 - 08/06 - full tank - ngp\n"
    "9.11 lt - 810.33 rs - 4136 - 23/06 - full tank - cwa"
)


def _excel_bytes(rows: list[list]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(EXCEL_COLUMNS)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_raw_text_preview_requires_auth(client: TestClient, test_vehicle: Vehicle) -> None:
    response = client.post(
        f"/api/vehicles/{test_vehicle.id}/import/raw-text/preview",
        json={"text": SAMPLE_TEXT, "start_year": 2026},
    )
    assert response.status_code == 401


def test_raw_text_preview_parses_sample_lines(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/import/raw-text/preview",
        json={"text": SAMPLE_TEXT, "start_year": 2026},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid_count"] == 2
    assert body["error_count"] == 0
    assert body["rows"][0]["location"] == "ngp"


def test_raw_text_preview_flags_duplicate_against_existing_entry(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/entries",
        json={
            "entry_type": "refuel",
            "date": "2026-06-08",
            "odometer_km": "3767.0",
            "litres": "12.50",
            "amount_rs": "1000.00",
        },
    )
    response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/import/raw-text/preview",
        json={"text": SAMPLE_TEXT, "start_year": 2026},
    )
    body = response.json()
    assert body["duplicate_count"] == 1
    assert body["rows"][0]["is_duplicate"] is True


def test_excel_preview_parses_uploaded_file(auth_client: TestClient, test_vehicle: Vehicle) -> None:
    file_bytes = _excel_bytes(
        [["refuel", "08/06/2026", 3767.0, 12.5, 1000.0, "", "full", "ngp", "", "ok", "", ""]]
    )
    response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/import/excel/preview",
        files={
            "file": (
                "entries.xlsx",
                file_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid_count"] == 1
    assert body["rows"][0]["location"] == "ngp"


def test_excel_preview_surfaces_row_errors(auth_client: TestClient, test_vehicle: Vehicle) -> None:
    file_bytes = _excel_bytes(
        [["bogus_type", "08/06/2026", 3767.0, 12.5, 1000.0, "", "full", "", "", "ok", "", ""]]
    )
    response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/import/excel/preview",
        files={
            "file": (
                "entries.xlsx",
                file_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    body = response.json()
    assert body["error_count"] == 1
    assert body["rows"][0]["errors"]


def test_download_template_has_expected_headers(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    response = auth_client.get(f"/api/vehicles/{test_vehicle.id}/import/template.xlsx")
    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.content))
    header = [cell.value for cell in next(workbook.active.iter_rows(min_row=1, max_row=1))]
    assert header == EXCEL_COLUMNS


def test_commit_imports_previewed_rows_in_one_transaction(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    preview = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/import/raw-text/preview",
        json={"text": SAMPLE_TEXT, "start_year": 2026},
    ).json()

    commit_response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/import/commit",
        json={"rows": preview["rows"], "skip_duplicates": True},
    )
    assert commit_response.status_code == 200
    body = commit_response.json()
    assert body["imported"] == 2
    assert body["skipped_duplicates"] == 0
    assert body["skipped_errors"] == 0

    entries = auth_client.get(f"/api/vehicles/{test_vehicle.id}/entries").json()
    assert entries["total"] == 2


def test_commit_skips_rows_with_errors(auth_client: TestClient, test_vehicle: Vehicle) -> None:
    text_with_bad_line = SAMPLE_TEXT + "\n1000rs - 3767 - 08/06 - full tank - ngp"  # missing litres
    preview = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/import/raw-text/preview",
        json={"text": text_with_bad_line, "start_year": 2026},
    ).json()
    assert preview["error_count"] == 1

    commit_response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/import/commit",
        json={"rows": preview["rows"]},
    )
    body = commit_response.json()
    assert body["imported"] == 2
    assert body["skipped_errors"] == 1


def test_commit_recomputes_duplicates_server_side(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    preview = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/import/raw-text/preview",
        json={"text": SAMPLE_TEXT, "start_year": 2026},
    ).json()

    # Commit once...
    auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/import/commit", json={"rows": preview["rows"]}
    )
    # ...then try to commit the exact same (now stale) preview rows again.
    second_commit = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/import/commit", json={"rows": preview["rows"]}
    ).json()
    assert second_commit["imported"] == 0
    assert second_commit["skipped_duplicates"] == 2
