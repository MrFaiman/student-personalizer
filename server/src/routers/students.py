from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..audit.service import log_event
from ..auth.current_user import CurrentUser
from ..auth.dependencies import get_current_user, require_permission, require_school_scope
from ..auth.permissions import PermissionKey
from ..constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..database import get_session
from ..schemas.student import (
    AttendanceResponse,
    DashboardStats,
    GradeResponse,
    StudentDetailResponse,
    StudentListResponse,
    StudentTimelineResponse,
)
from ..services.students import StudentService
from ..views.masking import apply_student_mask
from ..views.students import StudentDefaultView

router = APIRouter(
    prefix="/api/students",
    tags=["students"],
    dependencies=[
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.students_read.value)),
    ],
)


@router.get("", response_model=StudentListResponse)
async def list_students(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, le=MAX_PAGE_SIZE),
    class_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None),
    at_risk_only: bool = Query(default=False),
    period: str | None = Query(default=None),
    year: str | None = Query(default=None),
    sort_by: str | None = Query(default=None, description="Column to sort by: student_name, average_grade, total_absences, class_name"),
    sort_order: str = Query(default="asc", description="Sort direction: asc or desc"),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List students with optional filtering and sorting."""
    service = StudentService(session)
    view = StudentDefaultView()

    data = service.list_students(
        current_user=current_user,
        page=page,
        page_size=page_size,
        class_id=class_id,
        search=search,
        at_risk_only=at_risk_only,
        period=period,
        year=year,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    data["items"] = [apply_student_mask(item, current_user.role) for item in data["items"]]
    log_event(session, action="students_list", user_id=current_user.user_id, user_email=current_user.email, success=True, detail={"school_id": current_user.school_id, "page": page})
    return view.render_list(data)


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    class_id: UUID | None = Query(default=None),
    period: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    _current_user: CurrentUser = Depends(get_current_user),
):
    """Get dashboard statistics."""
    service = StudentService(session)
    view = StudentDefaultView()

    data = service.get_dashboard_stats(class_id=class_id, period=period, year=year)
    return view.render_dashboard(data)


@router.get("/{student_tz}", response_model=StudentDetailResponse)
async def get_student(
    student_tz: str,
    period: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a specific student by TZ."""
    service = StudentService(session)
    view = StudentDefaultView()

    data = service.get_student_detail(current_user=current_user, student_tz=student_tz, period=period, year=year)
    if not data:
        raise HTTPException(status_code=404, detail="Student not found")
    log_event(session, action="student_access", user_id=current_user.user_id, user_email=current_user.email, success=True, detail={"school_id": current_user.school_id, "student_tz": student_tz})
    return view.render_detail(apply_student_mask(data, current_user.role))


@router.get("/{student_tz}/grades", response_model=list[GradeResponse])
async def get_student_grades(
    student_tz: str,
    period: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    _current_user: CurrentUser = Depends(get_current_user),
):
    """Get all grades for a student."""
    service = StudentService(session)
    view = StudentDefaultView()

    data = service.get_student_grades(current_user=_current_user, student_tz=student_tz, period=period, year=year)
    if data is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return view.render_grades(data)


@router.get("/{student_tz}/attendance", response_model=list[AttendanceResponse])
async def get_student_attendance(
    student_tz: str,
    period: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    _current_user: CurrentUser = Depends(get_current_user),
):
    """Get all attendance records for a student."""
    service = StudentService(session)
    view = StudentDefaultView()

    data = service.get_student_attendance(current_user=_current_user, student_tz=student_tz, period=period, year=year)
    if data is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return view.render_attendance(data)


@router.get("/{student_tz}/timeline", response_model=StudentTimelineResponse)
async def get_student_timeline(
    student_tz: str,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get multi-year timeline data for a student."""
    service = StudentService(session)
    data = service.get_student_timeline(current_user=current_user, student_tz=student_tz)
    if not data:
        raise HTTPException(status_code=404, detail="Student not found")
    return StudentTimelineResponse(**apply_student_mask(data, current_user.role))

