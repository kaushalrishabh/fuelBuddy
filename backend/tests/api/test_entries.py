from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entry_audit import EntryAudit
from app.models.vehicle import Vehicle


def test_create_refuel_computes_price_per_litre(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/entries",
        json={
            "entry_type": "refuel",
            "date": "2026-06-08",
            "odometer_km": "3767.0",
            "litres": "12.50",
            "amount_rs": "1000.00",
            "location": "ngp",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["price_per_litre"]) == Decimal("80.00")
    assert body["fill_type"] == "full"
    assert body["odometer_status"] == "ok"


def test_create_refuel_computes_amount_from_price(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/entries",
        json={
            "entry_type": "refuel",
            "date": "2026-06-08",
            "odometer_km": "3767.0",
            "litres": "10.00",
            "price_per_litre": "90.50",
        },
    )
    assert response.status_code == 201
    assert Decimal(response.json()["amount_rs"]) == Decimal("905.00")


def test_create_refuel_without_amount_or_price_rejected(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/entries",
        json={
            "entry_type": "refuel",
            "date": "2026-06-08",
            "odometer_km": "3767.0",
            "litres": "10.00",
        },
    )
    assert response.status_code == 422


def test_create_fuel_removed_requires_notes(auth_client: TestClient, test_vehicle: Vehicle) -> None:
    response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/entries",
        json={"entry_type": "fuel_removed", "date": "2026-06-10", "litres": "2.00", "notes": ""},
    )
    assert response.status_code == 422


def test_create_fuel_removed_entry(auth_client: TestClient, test_vehicle: Vehicle) -> None:
    response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/entries",
        json={
            "entry_type": "fuel_removed",
            "date": "2026-06-10",
            "litres": "2.00",
            "notes": "Took 2L for the generator",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["entry_type"] == "fuel_removed"
    assert body["odometer_km"] is None
    assert body["amount_rs"] is None


def test_duplicate_refuel_entry_is_rejected(auth_client: TestClient, test_vehicle: Vehicle) -> None:
    payload = {
        "entry_type": "refuel",
        "date": "2026-06-08",
        "odometer_km": "3767.0",
        "litres": "12.50",
        "amount_rs": "1000.00",
    }
    first = auth_client.post(f"/api/vehicles/{test_vehicle.id}/entries", json=payload)
    assert first.status_code == 201

    second = auth_client.post(f"/api/vehicles/{test_vehicle.id}/entries", json=payload)
    assert second.status_code == 409


def test_list_entries_pagination_and_filters(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    for i in range(3):
        auth_client.post(
            f"/api/vehicles/{test_vehicle.id}/entries",
            json={
                "entry_type": "refuel",
                "date": f"2026-0{i + 1}-15",
                "odometer_km": str(1000 + i * 300),
                "litres": "10.00",
                "amount_rs": "900.00",
                "location": "ngp" if i < 2 else "cwa",
            },
        )

    all_entries = auth_client.get(f"/api/vehicles/{test_vehicle.id}/entries?page_size=2")
    assert all_entries.status_code == 200
    body = all_entries.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2

    filtered = auth_client.get(f"/api/vehicles/{test_vehicle.id}/entries?location=cwa")
    assert filtered.json()["total"] == 1

    bad_sort = auth_client.get(
        f"/api/vehicles/{test_vehicle.id}/entries?sort_by=notes; DROP TABLE users"
    )
    assert bad_sort.status_code == 400


def test_update_entry_writes_audit_record(
    auth_client: TestClient, test_vehicle: Vehicle, db_session: Session
) -> None:
    create_response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/entries",
        json={
            "entry_type": "refuel",
            "date": "2026-06-08",
            "odometer_km": "3767.0",
            "litres": "12.50",
            "amount_rs": "1000.00",
        },
    )
    entry_id = create_response.json()["id"]

    update_response = auth_client.patch(
        f"/api/vehicles/{test_vehicle.id}/entries/{entry_id}",
        json={"odometer_status": "faulty", "notes": "Speedo was acting up"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["odometer_status"] == "faulty"

    audit_rows = db_session.query(EntryAudit).filter(EntryAudit.fuel_entry_id == entry_id).all()
    assert len(audit_rows) == 1
    assert audit_rows[0].old_values["odometer_status"] == "ok"
    assert audit_rows[0].new_values["odometer_status"] == "faulty"


def test_update_entry_with_no_changes_skips_audit(
    auth_client: TestClient, test_vehicle: Vehicle, db_session: Session
) -> None:
    create_response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/entries",
        json={
            "entry_type": "refuel",
            "date": "2026-06-08",
            "odometer_km": "3767.0",
            "litres": "12.50",
            "amount_rs": "1000.00",
        },
    )
    entry_id = create_response.json()["id"]

    auth_client.patch(f"/api/vehicles/{test_vehicle.id}/entries/{entry_id}", json={})

    audit_rows = db_session.query(EntryAudit).filter(EntryAudit.fuel_entry_id == entry_id).all()
    assert len(audit_rows) == 0


def test_entries_require_auth(client: TestClient, test_vehicle: Vehicle) -> None:
    assert client.get(f"/api/vehicles/{test_vehicle.id}/entries").status_code == 401


def test_entries_scoped_to_vehicle_owner(auth_client: TestClient) -> None:
    assert auth_client.get("/api/vehicles/999999/entries").status_code == 404
