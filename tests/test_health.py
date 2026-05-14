"""
Basic tests using FastAPI's TestClient.

Demonstrates:
- TestClient (synchronous test client wrapping httpx)
- Testing a simple endpoint
- Overriding dependencies (swap real DB for test DB)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# ── Test database (in-memory SQLite) ─────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the real DB dependency with the test DB
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_user():
    response = client.post(
        "/api/v1/users/",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data  # never expose the hash


def test_login():
    # First register
    client.post(
        "/api/v1/users/",
        json={
            "email": "login@example.com",
            "username": "loginuser",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        },
    )
    # Then login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "loginuser", "password": "securepassword123"},
    )
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"


def test_protected_route_without_token():
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
