"""
Security headers tests (MoE section 3.x).
Verifies that all required HTTP security headers are present on every response.
"""

import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-32chars!!")
os.environ.setdefault("AUTH_REQUIRED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.database import get_session
from src.main import app

# Use SQLite in-memory for all header tests (tables must exist for login endpoint)
_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SQLModel.metadata.create_all(_engine)


def _override():
    with Session(_engine) as s:
        yield s


app.dependency_overrides[get_session] = _override
client = TestClient(app, raise_server_exceptions=False)

REQUIRED_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": None,  # just check presence
}


def _check_security_headers(response):
    headers = {k.lower(): v for k, v in response.headers.items()}
    for header, expected_value in REQUIRED_HEADERS.items():
        assert header in headers, f"Missing security header: {header}"
        if expected_value is not None:
            assert headers[header] == expected_value, (
                f"Header {header}: expected '{expected_value}', got '{headers[header]}'"
            )


def test_health_endpoint_has_security_headers():
    resp = client.get("/health")
    assert resp.status_code == 200
    _check_security_headers(resp)


def test_root_endpoint_has_security_headers():
    resp = client.get("/")
    _check_security_headers(resp)


def test_login_endpoint_has_security_headers():
    resp = client.post("/api/auth/login", json={"email": "x@x.com", "password": "wrong"})
    _check_security_headers(resp)


def test_protected_endpoint_has_security_headers():
    """Even 401 responses from protected endpoints must carry security headers."""
    resp = client.get("/api/students/")
    assert resp.status_code == 401
    _check_security_headers(resp)


def test_x_content_type_options_is_nosniff():
    resp = client.get("/health")
    assert resp.headers.get("x-content-type-options", "").lower() == "nosniff"


def test_x_frame_options_is_deny():
    resp = client.get("/health")
    assert resp.headers.get("x-frame-options", "").upper() == "DENY"


def test_no_server_version_disclosure():
    """Server header should not expose software version details."""
    resp = client.get("/health")
    server_header = resp.headers.get("server", "")
    # uvicorn sets 'uvicorn' - acceptable, but no version string
    assert "uvicorn/" not in server_header.lower(), (
        f"Server header discloses version: {server_header}"
    )
