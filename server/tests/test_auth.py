"""
Auth flow tests (MoE section 4.1).
Tests: login, lockout, refresh, logout, password policy.
"""

import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-32chars!!")
os.environ.setdefault("AUTH_REQUIRED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.auth.models import UserRole
from src.auth.schemas import CreateUserRequest
from src.auth.service import AuthService
from src.database import get_session
from src.main import app


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="module")
def client(engine):
    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    c = TestClient(app, raise_server_exceptions=False)
    yield c
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture(scope="module")
def seeded_client(engine):
    """Client with a pre-created admin user."""
    with Session(engine) as s:
        svc = AuthService(s)
        try:
            svc.create_user(CreateUserRequest(
                email="auth_admin@test.com",
                password="Admin@Test1234!",
                display_name="Auth Test Admin",
                role=UserRole.admin,
            ))
        except Exception:
            pass  # already exists from previous test run in same session

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    c = TestClient(app, raise_server_exceptions=False)
    yield c
    app.dependency_overrides.pop(get_session, None)



def test_login_success(seeded_client):
    resp = seeded_client.post("/api/auth/login", json={
        "email": "auth_admin@test.com",
        "password": "Admin@Test1234!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(seeded_client):
    resp = seeded_client.post("/api/auth/login", json={
        "email": "auth_admin@test.com",
        "password": "WrongPassword!",
    })
    assert resp.status_code == 401


def test_login_unknown_email(seeded_client):
    resp = seeded_client.post("/api/auth/login", json={
        "email": "nobody@nowhere.com",
        "password": "SomePassword!",
    })
    assert resp.status_code == 401


def test_login_email_case_insensitive(seeded_client):
    resp = seeded_client.post("/api/auth/login", json={
        "email": "AUTH_ADMIN@TEST.COM",
        "password": "Admin@Test1234!",
    })
    assert resp.status_code == 200



def test_account_lockout_after_five_failures(seeded_client, engine):
    """5 consecutive bad passwords should lock the account."""
    with Session(engine) as s:
        svc = AuthService(s)
        try:
            svc.create_user(CreateUserRequest(
                email="lockout@test.com",
                password="Lockout@Test1!",
                display_name="Lockout Test",
                role=UserRole.viewer,
            ))
        except Exception:
            pass  # already exists

    for _ in range(5):
        seeded_client.post("/api/auth/login", json={"email": "lockout@test.com", "password": "WrongPass!"})

    resp = seeded_client.post("/api/auth/login", json={"email": "lockout@test.com", "password": "WrongPass!"})
    assert resp.status_code == 429  # Too Many Requests - account temporarily locked



def test_refresh_returns_new_tokens(seeded_client):
    login = seeded_client.post("/api/auth/login", json={
        "email": "auth_admin@test.com",
        "password": "Admin@Test1234!",
    })
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    resp = seeded_client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


def test_refresh_with_invalid_token(seeded_client):
    resp = seeded_client.post("/api/auth/refresh", json={"refresh_token": "not.a.real.token"})
    assert resp.status_code == 401



def test_logout_revokes_session(seeded_client):
    login = seeded_client.post("/api/auth/login", json={
        "email": "auth_admin@test.com",
        "password": "Admin@Test1234!",
    })
    assert login.status_code == 200
    access_token = login.json()["access_token"]
    refresh_token = login.json()["refresh_token"]

    # Logout
    logout = seeded_client.post("/api/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert logout.status_code == 200

    # Refresh should now fail (session revoked)
    resp = seeded_client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401



def test_create_user_rejects_weak_password(seeded_client):
    """Admin creating a user with a weak password should fail with 422."""
    login = seeded_client.post("/api/auth/login", json={
        "email": "auth_admin@test.com",
        "password": "Admin@Test1234!",
    })
    token = login.json()["access_token"]

    resp = seeded_client.post(
        "/api/auth/users",
        json={"email": "weak@test.com", "password": "short", "display_name": "Weak", "role": "viewer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_create_user_rejects_no_uppercase(seeded_client):
    login = seeded_client.post("/api/auth/login", json={
        "email": "auth_admin@test.com",
        "password": "Admin@Test1234!",
    })
    token = login.json()["access_token"]

    resp = seeded_client.post(
        "/api/auth/users",
        json={"email": "lower@test.com", "password": "alllowercase1!", "display_name": "Lower", "role": "viewer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422



def test_me_returns_current_user(seeded_client):
    login = seeded_client.post("/api/auth/login", json={
        "email": "auth_admin@test.com",
        "password": "Admin@Test1234!",
    })
    token = login.json()["access_token"]

    resp = seeded_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "auth_admin@test.com"
    assert resp.json()["role"] == "admin"


def test_me_rejects_missing_token(seeded_client):
    resp = seeded_client.get("/api/auth/me")
    assert resp.status_code == 401
