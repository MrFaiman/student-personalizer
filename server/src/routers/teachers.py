from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..auth.current_user import CurrentUser
from ..auth.dependencies import get_current_user, require_permission, require_school_scope
from ..auth.permissions import PermissionKey
from ..database import get_session
from ..schemas.analytics import TeacherDetailResponse, TeacherListItem, TeacherStatsResponse
from ..services.teachers import TeacherService
from ..views.teachers import TeacherDefaultView

router = APIRouter(
    prefix="/api/teachers",
    tags=["teachers"],
    dependencies=[
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.analytics_read.value)),
    ],
)


@router.get("", response_model=list[str])
async def list_teachers(
    period: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get list of all teacher names."""
    service = TeacherService(session)
    return service.list_teachers(current_user=current_user, period=period, year=year)


@router.get("/list", response_model=list[TeacherListItem])
async def get_teachers_list(
    period: str | None = Query(default=None),
    grade_level: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get list of all teachers with summary stats."""
    service = TeacherService(session)
    view = TeacherDefaultView()

    data = service.get_teachers_list_with_stats(
        current_user=current_user,
        period=period,
        grade_level=grade_level,
        year=year,
    )
    return view.render_list(data)


@router.get("/{teacher_name}/stats", response_model=TeacherStatsResponse)
async def get_teacher_stats(
    teacher_name: str,
    period: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get grade distribution statistics for a teacher."""
    service = TeacherService(session)
    view = TeacherDefaultView()

    data = service.get_teacher_stats(
        current_user=current_user,
        teacher_name=teacher_name,
        period=period,
        year=year,
    )

    if data["total_students"] == 0:
        raise HTTPException(status_code=404, detail=f"Teacher '{teacher_name}' not found or has no grades")

    return view.render_stats(data)


@router.get("/{teacher_id}/detail", response_model=TeacherDetailResponse)
async def get_teacher_detail(
    teacher_id: UUID,
    period: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get detailed analytics for a specific teacher."""
    service = TeacherService(session)
    view = TeacherDefaultView()

    data = service.get_teacher_detail(
        current_user=current_user,
        teacher_id=teacher_id,
        period=period,
        year=year,
    )

    if not data:
        raise HTTPException(status_code=404, detail=f"Teacher '{teacher_id}' not found")

    return view.render_detail(data)
