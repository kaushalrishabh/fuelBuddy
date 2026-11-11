from decimal import Decimal

from fastapi.testclient import TestClient

from app.models.vehicle import Vehicle


def test_list_vehicles_requires_auth(client: TestClient, test_vehicle: Vehicle) -> None:
    assert client.get("/api/vehicles").status_code == 401


def test_list_vehicles_returns_owned_vehicle(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    response = auth_client.get("/api/vehicles")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Royal Enfield Classic 350"
    assert Decimal(body[0]["tank_capacity_l"]) == Decimal("13.00")


def test_update_vehicle_tank_capacity(auth_client: TestClient, test_vehicle: Vehicle) -> None:
    response = auth_client.patch(
        f"/api/vehicles/{test_vehicle.id}", json={"tank_capacity_l": "15.50"}
    )
    assert response.status_code == 200
    assert Decimal(response.json()["tank_capacity_l"]) == Decimal("15.50")


def test_update_vehicle_not_found(auth_client: TestClient) -> None:
    response = auth_client.patch("/api/vehicles/999999", json={"name": "Nope"})
    assert response.status_code == 404
