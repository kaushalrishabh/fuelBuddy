from decimal import Decimal

from fastapi.testclient import TestClient

from app.models.vehicle import Vehicle


def _create_refuel(
    client: TestClient,
    vehicle_id: int,
    date: str,
    odometer: str,
    litres: str = "10",
    amount: str = "900",
) -> None:
    response = client.post(
        f"/api/vehicles/{vehicle_id}/entries",
        json={
            "entry_type": "refuel",
            "date": date,
            "odometer_km": odometer,
            "litres": litres,
            "amount_rs": amount,
        },
    )
    assert response.status_code == 201


def test_analytics_endpoints_require_auth(client: TestClient, test_vehicle: Vehicle) -> None:
    for path in ["kpis", "mileage-over-time", "monthly", "price-trend", "seasonality"]:
        assert client.get(f"/api/vehicles/{test_vehicle.id}/analytics/{path}").status_code == 401


def test_kpis_lifetime_fields_ignore_the_date_filter(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    # Two segments, both safely under the 13L*45km/L=585km plausibility ceiling.
    _create_refuel(auth_client, test_vehicle.id, "2026-01-01", "0")
    _create_refuel(auth_client, test_vehicle.id, "2026-01-15", "500")  # 50 km/L
    _create_refuel(auth_client, test_vehicle.id, "2026-02-01", "1000")  # 50 km/L

    # Restrict the window to just January -- only the first segment ends there.
    response = auth_client.get(
        f"/api/vehicles/{test_vehicle.id}/analytics/kpis",
        params={"range": "custom", "date_from": "2026-01-01", "date_to": "2026-01-31"},
    )
    assert response.status_code == 200
    body = response.json()

    # Lifetime km/L reflects BOTH segments (whole history), not just the window.
    assert Decimal(body["lifetime_km_per_l"]) == Decimal("50.0")
    # Windowed total_km reflects only the segment ending inside January.
    assert Decimal(body["total_km"]) == Decimal("500.0")


def test_monthly_breakdown_respects_the_filter(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    _create_refuel(auth_client, test_vehicle.id, "2026-01-01", "0")
    _create_refuel(auth_client, test_vehicle.id, "2026-01-15", "500")
    _create_refuel(auth_client, test_vehicle.id, "2026-02-01", "1000")

    response = auth_client.get(
        f"/api/vehicles/{test_vehicle.id}/analytics/monthly",
        params={"range": "custom", "date_from": "2026-01-01", "date_to": "2026-01-31"},
    )
    body = response.json()
    assert len(body) == 1
    assert body[0]["month"] == 1


def test_mileage_over_time_returns_rolling_average(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    _create_refuel(auth_client, test_vehicle.id, "2026-01-01", "0")
    _create_refuel(auth_client, test_vehicle.id, "2026-01-15", "500")
    _create_refuel(auth_client, test_vehicle.id, "2026-02-01", "1000")

    response = auth_client.get(f"/api/vehicles/{test_vehicle.id}/analytics/mileage-over-time")
    assert response.status_code == 200
    points = response.json()
    assert len(points) == 2
    assert points[0]["status"] == "valid"
    assert Decimal(points[1]["rolling_avg_km_per_l"]) == Decimal("50.0")


def test_price_trend_reports_min_max_average(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    _create_refuel(auth_client, test_vehicle.id, "2026-01-01", "0", amount="800")  # 80/L
    _create_refuel(auth_client, test_vehicle.id, "2026-01-15", "500", amount="1000")  # 100/L

    response = auth_client.get(f"/api/vehicles/{test_vehicle.id}/analytics/price-trend")
    body = response.json()
    assert Decimal(body["min_price"]) == Decimal(80)
    assert Decimal(body["max_price"]) == Decimal(100)


def test_cost_efficiency_yearly_summary_ignores_filter_but_points_respect_it(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    _create_refuel(auth_client, test_vehicle.id, "2026-01-01", "0")
    _create_refuel(auth_client, test_vehicle.id, "2026-01-15", "500")
    _create_refuel(auth_client, test_vehicle.id, "2026-02-01", "1000")

    response = auth_client.get(
        f"/api/vehicles/{test_vehicle.id}/analytics/cost-efficiency",
        params={"range": "custom", "date_from": "2026-01-01", "date_to": "2026-01-31"},
    )
    body = response.json()
    assert len(body["points"]) == 1  # only the January-ending segment
    assert len(body["yearly_summary"]) == 1
    assert body["yearly_summary"][0]["fill_count"] == 3  # whole year, not just the window


def test_locations_ranking_endpoint(auth_client: TestClient, test_vehicle: Vehicle) -> None:
    response = auth_client.get(f"/api/vehicles/{test_vehicle.id}/analytics/locations")
    assert response.status_code == 200
    assert response.json() == []  # no entries yet, nothing to rank


def test_seasonality_always_returns_twelve_months(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    response = auth_client.get(f"/api/vehicles/{test_vehicle.id}/analytics/seasonality")
    assert response.status_code == 200
    assert len(response.json()) == 12


def test_riding_pattern_with_no_data_returns_nulls(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    response = auth_client.get(f"/api/vehicles/{test_vehicle.id}/analytics/riding-pattern")
    assert response.status_code == 200
    body = response.json()
    assert body["avg_days_between_fills"] is None
    assert body["predicted_next_refuel_date"] is None


def test_records_endpoint_reports_most_expensive_fill(
    auth_client: TestClient, test_vehicle: Vehicle
) -> None:
    _create_refuel(auth_client, test_vehicle.id, "2026-01-01", "0", amount="900")
    _create_refuel(auth_client, test_vehicle.id, "2026-01-15", "500", amount="2000")

    response = auth_client.get(f"/api/vehicles/{test_vehicle.id}/analytics/records")
    body = response.json()
    assert Decimal(body["most_expensive_fill_amount_rs"]) == Decimal(2000)


def test_data_quality_flags_outlier_price(auth_client: TestClient, test_vehicle: Vehicle) -> None:
    _create_refuel(auth_client, test_vehicle.id, "2026-01-01", "0", amount="2500")  # 250/L

    response = auth_client.get(f"/api/vehicles/{test_vehicle.id}/analytics/data-quality")
    body = response.json()
    assert any(issue["kind"] == "outlier_price" for issue in body["issues"])


def test_analytics_vehicle_not_found(auth_client: TestClient) -> None:
    assert auth_client.get("/api/vehicles/999999/analytics/kpis").status_code == 404
