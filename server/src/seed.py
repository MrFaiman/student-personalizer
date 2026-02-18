"""Seed default school and admin user, backfill school_id on legacy data."""

from uuid import UUID

from sqlmodel import Session, select

from .auth import hash_password
from .models import (
    AttendanceRecord,
    Class,
    Grade,
    ImportLog,
    School,
    Student,
    Teacher,
    User,
)


def seed_default_school_and_admin(session: Session) -> UUID:
    """Create default school and admin user if none exist. Returns school id."""
    school = session.exec(select(School)).first()
    if not school:
        school = School(name="Default School", slug="default")
        session.add(school)
        session.flush()

    admin = session.exec(select(User).where(User.role == "admin")).first()
    if not admin:
        admin = User(
            email="admin@school.local",
            hashed_password=hash_password("admin123"),
            full_name="System Admin",
            role="admin",
            school_id=school.id,
        )
        session.add(admin)

    session.commit()
    return school.id


def backfill_school_id(session: Session, school_id: UUID) -> None:
    """Set school_id on all existing rows that have NULL school_id."""
    models = [Teacher, Class, Student, Grade, AttendanceRecord, ImportLog]
    for model in models:
        rows = session.exec(select(model).where(model.school_id.is_(None))).all()  # type: ignore[attr-defined]
        for row in rows:
            row.school_id = school_id
            session.add(row)
    session.commit()
