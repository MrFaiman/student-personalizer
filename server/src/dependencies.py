"""Dependency injection factories for all services."""

from uuid import UUID

from fastapi import Depends
from sqlmodel import Session

from .auth import get_current_school_id
from .database import get_session
from .services.analytics import AnalyticsService
from .services.classes import ClassService
from .services.ingestion import IngestionService
from .services.ml import MLService
from .services.students import StudentService
from .services.teachers import TeacherService


def get_student_service(
    session: Session = Depends(get_session),
    school_id: UUID = Depends(get_current_school_id),
) -> StudentService:
    return StudentService(session, school_id)


def get_class_service(
    session: Session = Depends(get_session),
    school_id: UUID = Depends(get_current_school_id),
) -> ClassService:
    return ClassService(session, school_id)


def get_teacher_service(
    session: Session = Depends(get_session),
    school_id: UUID = Depends(get_current_school_id),
) -> TeacherService:
    return TeacherService(session, school_id)


def get_analytics_service(
    session: Session = Depends(get_session),
    school_id: UUID = Depends(get_current_school_id),
) -> AnalyticsService:
    return AnalyticsService(session, school_id)


def get_ml_service(
    session: Session = Depends(get_session),
    school_id: UUID = Depends(get_current_school_id),
) -> MLService:
    return MLService(session, school_id)


def get_ingestion_service(
    session: Session = Depends(get_session),
    school_id: UUID = Depends(get_current_school_id),
) -> IngestionService:
    return IngestionService(session, school_id)
