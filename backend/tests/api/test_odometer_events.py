from fastapi.testclient import TestClient

from app.models.vehicle import Vehicle


def test_create_faulty_period_event(auth_client: TestClient, test_vehicle: Vehicle) -> None:
    response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/odometer-events",
        json={
            "event_type": "faulty_period",
            "start_date": "2023-01-01",
            "end_date": "2023-03-15",
            "notes": "Speedo cable snapped",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["event_type"] == "faulty_period"
    assert body["end_date"] == "2023-03-15"


def test_create_replaced_event_requires_both_readings(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/odometer-events",
        json={"event_type": "replaced", "start_date": "2024-06-01"},
    )
    assert response.status_code == 422


def test_create_replaced_event_with_readings(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/odometer-events",
        json={
            "event_type": "replaced",
            "start_date": "2024-06-01",
            "old_reading_at_change": "42000.0",
            "new_reading_at_change": "0.0",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["old_reading_at_change"] == "42000.0"
    assert body["new_reading_at_change"] == "0.0"


def test_update_odometer_event(auth_client: TestClient, test_vehicle: Vehicle) -> None:
    create_response = auth_client.post(
        f"/api/vehicles/{test_vehicle.id}/odometer-events",
        json={"event_type": "faulty_period", "start_date": "2023-01-01"},
    )
    event_id = create_response.json()["id"]

    update_response = auth_client.patch(
        f"/api/vehicles/{test_vehicle.id}/odometer-events/{event_id}",
        json={"end_date": "2023-02-01"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["end_date"] == "2023-02-01"


def test_odometer_events_scoped_to_vehicle_owner(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    response = auth_client.get("/api/vehicles/999999/odometer-events")
    assert response.status_code == 404
