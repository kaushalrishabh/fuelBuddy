from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.password_reset import create_reset_token


def test_forgot_password_always_returns_ok_regardless_of_email(
    client: TestClient, test_user: User
) -> None:
    assert (
        client.post("/api/auth/forgot-password", json={"email": "unknown@example.com"}).status_code
        == 200
    )
    assert (
        client.post("/api/auth/forgot-password", json={"email": test_user.email}).status_code == 200
    )


def test_reset_password_with_valid_token_then_login(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    raw_token = create_reset_token(db_session, test_user)

    response = client.post(
        "/api/auth/reset-password", json={"token": raw_token, "new_password": "brand-new-password"}
    )
    assert response.status_code == 200

    login_response = client.post(
        "/api/auth/login", json={"email": test_user.email, "password": "brand-new-password"}
    )
    assert login_response.status_code == 200


def test_reset_password_rejects_invalid_token(client: TestClient) -> None:
    response = client.post(
        "/api/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "whatever123"},
    )
    assert response.status_code == 400


def test_reset_password_token_is_single_use(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    raw_token = create_reset_token(db_session, test_user)
    client.post(
        "/api/auth/reset-password", json={"token": raw_token, "new_password": "first-password"}
    )

    second_attempt = client.post(
        "/api/auth/reset-password", json={"token": raw_token, "new_password": "second-password"}
    )
    assert second_attempt.status_code == 400
