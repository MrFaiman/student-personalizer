"""
Audit log tests (MoE section 3.x - immutable audit trail).
Verifies that security-relevant events are recorded in the AuditLog table.
"""

import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-32chars!!")
os.environ.setdefault("AUTH_REQUIRED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from src.audit.models import AuditLog
from src.auth.models import UserRole
from src.auth.schemas import CreateUserRequest
from src.auth.service import AuthService
from src.database import get_session
from src.main import app

AUDIT_USERS = {
    "admin": ("audit_admin@test.com", "AuditAdmin@1234!", "Audit Admin", UserRole.system_admin),
    "bad":   ("audit_bad@test.com",   "AuditBad@1234!",  "Audit Bad",   UserRole.teacher),
}


@pytest.fixture(scope="module")
def audit_engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)

    with Session(eng) as s:
        svc = AuthService(s)
        for key, (email, password, display_name, role) in AUDIT_USERS.items():
            svc.create_user(CreateUserRequest(email=email, password=password, display_name=display_name, role=role))

    return eng


@pytest.fixture(scope="module")
def audit_client(audit_engine):
    def override():
        with Session(audit_engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    c = TestClient(app, raise_server_exceptions=False)
    yield c
    app.dependency_overrides.pop(get_session, None)


def _count_logs(engine, action: str, success: bool | None = None) -> int:
    with Session(engine) as s:
        q = select(AuditLog).where(AuditLog.action == action)
        if success is not None:
            q = q.where(AuditLog.success == success)
        return len(s.exec(q).all())



def test_successful_login_creates_audit_log(audit_client, audit_engine):
    before = _count_logs(audit_engine, "login", success=True)

    resp = audit_client.post("/api/auth/login", json={
        "email": "audit_admin@test.com",
        "password": "AuditAdmin@1234!",
    })
    assert resp.status_code == 200

    after = _count_logs(audit_engine, "login", success=True)
    assert after > before, "Expected a successful login audit log entry"


def test_failed_login_creates_audit_log(audit_client, audit_engine):
    before = _count_logs(audit_engine, "login", success=False)

    resp = audit_client.post("/api/auth/login", json={
        "email": "audit_admin@test.com",
        "password": "WrongPassword!",
    })
    assert resp.status_code == 401

    after = _count_logs(audit_engine, "login", success=False)
    assert after > before, "Expected a failed login audit log entry"


def test_login_unknown_email_creates_audit_log(audit_client, audit_engine):
    before = _count_logs(audit_engine, "login", success=False)

    audit_client.post("/api/auth/login", json={
        "email": "nobody@nowhere.com",
        "password": "AnyPass!",
    })

    after = _count_logs(audit_engine, "login", success=False)
    assert after > before, "Expected a failed login audit log for unknown email"



def test_logout_creates_audit_log(audit_client, audit_engine):
    login = audit_client.post("/api/auth/login", json={
        "email": "audit_admin@test.com",
        "password": "AuditAdmin@1234!",
    })
    token = login.json()["access_token"]

    before = _count_logs(audit_engine, "logout")

    audit_client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

    after = _count_logs(audit_engine, "logout")
    assert after > before, "Expected a logout audit log entry"



def test_audit_log_records_user_email(audit_client, audit_engine):
    audit_client.post("/api/auth/login", json={
        "email": "audit_admin@test.com",
        "password": "AuditAdmin@1234!",
    })

    with Session(audit_engine) as s:
        log = s.exec(
            select(AuditLog)
            .where(AuditLog.action == "login")
            .where(AuditLog.success == True)  # noqa: E712
            .order_by(AuditLog.timestamp.desc())
        ).first()

    assert log is not None
    assert log.user_email == "audit_admin@test.com"
    assert log.timestamp is not None


def test_audit_log_has_no_plaintext_passwords(audit_client, audit_engine):
    """Audit log detail must never contain plaintext passwords."""
    with Session(audit_engine) as s:
        logs = s.exec(select(AuditLog)).all()

    for log in logs:
        detail = log.detail or ""
        assert "AuditAdmin@1234!" not in detail, "Plaintext password found in audit log detail!"
        assert "WrongPassword!" not in detail, "Plaintext password found in audit log detail!"
