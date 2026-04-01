"""
Role-based access control tests (MoE section 4.1).
Verifies roles are correctly restricted from endpoints above their level.
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

RBAC_USERS = {
    "system_admin": ("rbac_admin@test.com", "Admin@Rbac1234!", "RBAC Admin", UserRole.system_admin),
    "teacher":      ("rbac_teacher@test.com", "Teacher@Rbac1!",  "RBAC Teacher", UserRole.teacher),
}

RBAC_SCHOOL_ID = 100


@pytest.fixture(scope="module")
def rbac_engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)

    with Session(eng) as s:
        svc = AuthService(s)
        for key, (email, password, display_name, role) in RBAC_USERS.items():
            svc.create_user(
                CreateUserRequest(
                    email=email,
                    password=password,
                    display_name=display_name,
                    role=role,
                    school_id=RBAC_SCHOOL_ID,
                    school_name="RBAC School",
                )
            )

    return eng


@pytest.fixture(scope="module")
def rbac_client(rbac_engine):
    def override():
        with Session(rbac_engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    c = TestClient(app, raise_server_exceptions=False)
    yield c
    app.dependency_overrides.pop(get_session, None)


def _token(client, role: str) -> str:
    email, password, _, _ = RBAC_USERS[role]
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {role}: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def admin_tok(rbac_client):
    return _token(rbac_client, "system_admin")


@pytest.fixture(scope="module")
def teacher_tok(rbac_client):
    return _token(rbac_client, "teacher")


@pytest.fixture(scope="module")
def test_unauthenticated_students_list(rbac_client):
    resp = rbac_client.get("/api/students/")
    assert resp.status_code == 401


def test_unauthenticated_analytics(rbac_client):
    resp = rbac_client.get("/api/analytics/kpis")
    assert resp.status_code == 401


def test_unauthenticated_upload(rbac_client):
    resp = rbac_client.post("/api/ingest/upload")
    assert resp.status_code == 401



def test_teacher_can_access_analytics(rbac_client, teacher_tok):
    resp = rbac_client.get("/api/analytics/kpis", headers={"Authorization": f"Bearer {teacher_tok}"})
    # 200 or 422 (no data) - but NOT 401/403
    assert resp.status_code not in (401, 403)


def test_teacher_cannot_upload(rbac_client, teacher_tok):
    resp = rbac_client.post("/api/ingest/upload", headers={"Authorization": f"Bearer {teacher_tok}"})
    assert resp.status_code == 403



def test_teacher_can_list_students(rbac_client, teacher_tok):
    resp = rbac_client.get("/api/students/", headers={"Authorization": f"Bearer {teacher_tok}"})
    assert resp.status_code not in (401, 403)


def test_teacher_cannot_create_user(rbac_client, teacher_tok):
    resp = rbac_client.post(
        "/api/auth/users",
        json={"email": "new2@test.com", "password": "Valid@Pass1!", "display_name": "New2", "role": "teacher"},
        headers={"Authorization": f"Bearer {teacher_tok}"},
    )
    assert resp.status_code == 403



def test_admin_can_list_users(rbac_client, admin_tok):
    resp = rbac_client.get("/api/auth/users", headers={"Authorization": f"Bearer {admin_tok}"})
    assert resp.status_code == 200


def test_admin_can_create_user(rbac_client, admin_tok):
    resp = rbac_client.post(
        "/api/auth/users",
        json={"email": "created_by_admin@test.com", "password": "Admin@Created1!", "display_name": "Created", "role": "teacher"},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert resp.status_code == 201



def test_teacher_student_list_unmasks_tz(rbac_client, teacher_tok, rbac_engine):
    """Teacher sees unmasked student_tz."""
    from src.crypto.field_encryption import hash_for_lookup
    from src.models import Class, Student

    # Seed a student so the list is non-empty
    with Session(rbac_engine) as s:
        existing = s.exec(
            __import__("sqlmodel", fromlist=["select"]).select(Class).where(Class.class_name == "RBAC-Test-10")
        ).first()
        if not existing:
            cls = Class(class_name="RBAC-Test-10", grade_level="10", school_id=RBAC_SCHOOL_ID)
            s.add(cls)
            s.commit()
            s.refresh(cls)
            class_id = cls.id
        else:
            class_id = existing.id

        if not s.exec(
            __import__("sqlmodel", fromlist=["select"]).select(Student).where(Student.student_tz == "123456789")
        ).first():
            s.add(Student(
                student_tz="123456789",
                student_name="Test Student",
                class_id=class_id,
                student_tz_hash=hash_for_lookup("123456789"),
                school_id=RBAC_SCHOOL_ID,
            ))
            s.commit()

    resp = rbac_client.get("/api/students/", headers={"Authorization": f"Bearer {teacher_tok}"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    for item in items:
        assert not item["student_tz"].startswith("***"), f"Teacher saw masked tz: {item['student_tz']}"
