from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.models.vehicle import Vehicle


def test_export_requires_auth(client: TestClient, test_vehicle: Vehicle) -> None:
    assert client.get(f"/api/vehicles/{test_vehicle.id}/export.xlsx").status_code == 401


def test_export_returns_workbook_with_all_sheets(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/entries",
        json={
            "entry_type": "refuel",
            "date": "2026-01-01",
            "odometer_km": "1000.0",
            "litres": "10.00",
            "amount_rs": "900.00",
        },
    )
    auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/entries",
        json={
            "entry_type": "refuel",
            "date": "2026-01-15",
            "odometer_km": "1500.0",
            "litres": "10.00",
            "amount_rs": "900.00",
        },
    )

    response = auth_client.get(f"/api/vehicles/{test_vehicle.id}/export.xlsx")
    assert response.status_code == 200
    assert "FuelBuddy_export_" in response.headers["content-disposition"]

    workbook = load_workbook(BytesIO(response.content))
    assert workbook.sheetnames == ["Entries", "Computed", "Odometer events", "Summary"]
    assert workbook["Entries"].max_row == 3  # header + 2 entries
    assert workbook["Computed"].max_row == 2  # header + 1 segment


def test_export_vehicle_not_found(auth_client: TestClient) -> None:
    assert auth_client.get("/api/vehicles/999999/export.xlsx").status_code == 404
