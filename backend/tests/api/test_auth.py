from fastapi.testclient import TestClient

from app.core.rate_limit import MAX_ATTEMPTS
from app.models.user import User
from tests.conftest import TEST_PASSWORD


def test_login_success(client: TestClient, test_user: User) -> None:
    response = client.post(
        "/api/auth/login", json={"email": test_user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["email"] == test_user.email
    assert "fb_token" in response.cookies


def test_login_wrong_password(client: TestClient, test_user: User) -> None:
    response = client.post("/api/auth/login", json={"email": test_user.email, "password": "nope"})
    assert response.status_code == 401


def test_login_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"email": "ghost@example.com", "password": "whatever"}
    )
    assert response.status_code == 401


def test_login_rate_limited_after_max_attempts(client: TestClient, test_user: User) -> None:
    for _ in range(MAX_ATTEMPTS):
        client.post("/api/auth/login", json={"email": test_user.email, "password": "wrong"})

    response = client.post("/api/auth/login", json={"email": test_user.email, "password": "wrong"})
    assert response.status_code == 429


def test_me_requires_auth(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_valid_cookie(auth_client: TestClient, test_user: User) -> None:
    response = auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == test_user.email


def test_logout_clears_cookie(auth_client: TestClient) -> None:
    response = auth_client.post("/api/auth/logout")
    assert response.status_code == 200
    assert auth_client.get("/api/auth/me").status_code == 401


def test_mutating_request_without_csrf_header_is_rejected(
    client: TestClient, test_user: User
) -> None:
    client.headers.pop("X-FuelBuddy-Client", None)
    response = client.post(
        "/api/auth/login", json={"email": test_user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 403


def test_change_password_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "whatever", "new_password": "new-password-123"},
    )
    assert response.status_code == 401


def test_change_password_rejects_wrong_current_password(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/auth/change-password",
        json={"current_password": "wrong", "new_password": "new-password-123"},
    )
    assert response.status_code == 401


def test_change_password_success_then_login_with_new_password(
    auth_client: TestClient, test_user: User
) -> None:
    response = auth_client.post(
        "/api/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": "new-password-123"},
    )
    assert response.status_code == 200

    login_response = auth_client.post(
        "/api/auth/login", json={"email": test_user.email, "password": "new-password-123"}
    )
    assert login_response.status_code == 200
