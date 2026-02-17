from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..database import get_session
from ..schemas.student import (
    AttendanceResponse,
    DashboardStats,
    GradeResponse,
    StudentDetailResponse,
    StudentListResponse,
)
from ..services.students import StudentService
from ..views.students import StudentDefaultView

router = APIRouter(prefix="/api/students", tags=["students"])


@router.get("", response_model=StudentListResponse)
async def list_students(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, le=MAX_PAGE_SIZE),
    class_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None),
    at_risk_only: bool = Query(default=False),
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """List students with optional filtering."""
    service = StudentService(session)
    view = StudentDefaultView()

    data = service.list_students(
        page=page,
        page_size=page_size,
        class_id=class_id,
        search=search,
        at_risk_only=at_risk_only,
        period=period,
    )
    return view.render_list(data)


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    class_id: UUID | None = Query(default=None),
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """Get dashboard statistics."""
    service = StudentService(session)
    view = StudentDefaultView()

    data = service.get_dashboard_stats(class_id=class_id, period=period)
    return view.render_dashboard(data)


@router.get("/{student_tz}", response_model=StudentDetailResponse)
async def get_student(
    student_tz: str,
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """Get a specific student by TZ."""
    service = StudentService(session)
    view = StudentDefaultView()

    data = service.get_student_detail(student_tz, period)
    if not data:
        raise HTTPException(status_code=404, detail="Student not found")
    return view.render_detail(data)


@router.get("/{student_tz}/grades", response_model=list[GradeResponse])
async def get_student_grades(
    student_tz: str,
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """Get all grades for a student."""
    service = StudentService(session)
    view = StudentDefaultView()

    data = service.get_student_grades(student_tz, period)
    if data is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return view.render_grades(data)


@router.get("/{student_tz}/attendance", response_model=list[AttendanceResponse])
async def get_student_attendance(
    student_tz: str,
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """Get all attendance records for a student."""
    service = StudentService(session)
    view = StudentDefaultView()

    data = service.get_student_attendance(student_tz, period)
    if data is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return view.render_attendance(data)
