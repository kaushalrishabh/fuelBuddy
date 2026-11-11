from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db
from app.core.rate_limit import reset_rate_limits
from app.core.security import hash_password
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.models.vehicle import Vehicle

CSRF_HEADERS = {"X-FuelBuddy-Client": "test"}
TEST_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> None:
    reset_rate_limits()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.headers.update(CSRF_HEADERS)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(email="rider@example.com", password_hash=hash_password(TEST_PASSWORD))
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_vehicle(db_session: Session, test_user: User) -> Vehicle:
    vehicle = Vehicle(user_id=test_user.id, name="Royal Enfield Classic 350", is_default=True)
    db_session.add(vehicle)
    db_session.commit()
    return vehicle


@pytest.fixture
def auth_client(client: TestClient, test_user: User) -> TestClient:
    response = client.post(
        "/api/auth/login", json={"email": test_user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    return client
