"""
Shared fixtures for security tests (auth, RBAC, headers, audit).

Import pattern in test files:
    from tests.conftest_security import auth_client, admin_token, teacher_token, viewer_token
"""

import os

# Must be set before any server module is imported
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-32chars!!")
os.environ.setdefault("AUTH_REQUIRED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")  # overridden by fixture

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Import app and overrideable dependencies after env vars are set
from src.database import get_session
from src.main import app
from src.auth.models import User, UserRole
from src.auth.schemas import CreateUserRequest
from src.auth.service import AuthService
from src.auth.schemas import LoginRequest


TEST_USERS = {
    "admin":   ("admin@test.com",   "Admin@Test1234!", "Test Admin",   UserRole.admin),
    "teacher": ("teacher@test.com", "Teacher@Test1!", "Test Teacher", UserRole.teacher),
    "viewer":  ("viewer@test.com",  "Viewer@Test1!",  "Test Viewer",  UserRole.viewer),
}


def _make_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _seed_users(engine) -> dict[str, User]:
    SQLModel.metadata.create_all(engine)
    users = {}
    with Session(engine) as session:
        svc = AuthService(session)
        for key, (email, password, display_name, role) in TEST_USERS.items():
            req = CreateUserRequest(
                email=email,
                password=password,
                display_name=display_name,
                role=role,
            )
            user = svc.create_user(req)
            users[key] = user
    return users


@pytest.fixture(scope="module")
def security_engine():
    """In-memory SQLite engine seeded with test users."""
    engine = _make_engine()
    _seed_users(engine)
    return engine


@pytest.fixture(scope="module")
def auth_client(security_engine):
    """TestClient with session override pointing to in-memory SQLite."""
    def override_session():
        with Session(security_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.pop(get_session, None)


def _get_token(client: TestClient, role: str) -> str:
    email, password, _, _ = TEST_USERS[role]
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {role}: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token(auth_client):
    return _get_token(auth_client, "admin")


@pytest.fixture(scope="module")
def teacher_token(auth_client):
    return _get_token(auth_client, "teacher")


@pytest.fixture(scope="module")
def viewer_token(auth_client):
    return _get_token(auth_client, "viewer")
