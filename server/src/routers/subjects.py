from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..auth.current_user import CurrentUser
from ..auth.dependencies import get_current_user, require_permission, require_school_scope
from ..auth.permissions import PermissionKey
from ..database import get_session
from ..schemas.subject import SubjectDetailResponse, SubjectListItem, SubjectStatsResponse
from ..services.subjects import SubjectService
from ..views.subjects import SubjectDefaultView

router = APIRouter(
    prefix="/api/subjects",
    tags=["subjects"],
    dependencies=[
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.analytics_read.value)),
    ],
)


@router.get("", response_model=list[str])
async def list_subject_names(
    period: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get list of all subject names."""
    service = SubjectService(session)
    return service.list_subjects(current_user=current_user, period=period, year=year)


@router.get("/list", response_model=list[SubjectListItem])
async def get_subjects_list(
    period: str | None = Query(default=None),
    grade_level: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get list of all subjects with summary stats."""
    service = SubjectService(session)
    view = SubjectDefaultView()

    data = service.get_subjects_list_with_stats(
        current_user=current_user,
        period=period,
        grade_level=grade_level,
        year=year,
    )
    return view.render_list(data)


@router.get("/{subject_name}/stats", response_model=SubjectStatsResponse)
async def get_subject_stats(
    subject_name: str,
    period: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get grade distribution statistics by subject name."""
    service = SubjectService(session)
    view = SubjectDefaultView()

    data = service.get_subject_stats(
        current_user=current_user,
        subject_name=subject_name,
        period=period,
        year=year,
    )

    if data["total_students"] == 0:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_name}' not found or has no grades")

    return view.render_stats(data)


@router.get("/{subject_id}/detail", response_model=SubjectDetailResponse)
async def get_subject_detail(
    subject_id: UUID,
    period: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get detailed analytics for a specific subject identity."""
    service = SubjectService(session)
    view = SubjectDefaultView()

    data = service.get_subject_detail(
        current_user=current_user,
        subject_id=subject_id,
        period=period,
        year=year,
    )

    if not data:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_id}' not found")

    return view.render_detail(data)
