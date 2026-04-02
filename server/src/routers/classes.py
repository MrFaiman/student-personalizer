from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..auth.dependencies import require_permission, require_school_scope
from ..auth.current_user import CurrentUser
from ..auth.dependencies import get_current_user
from ..auth.permissions import PermissionKey
from ..database import get_session
from ..schemas.analytics import TopBottomResponse
from ..schemas.student import ClassResponse
from ..services.classes import ClassService
from ..views.classes import ClassDefaultView

router = APIRouter(
    prefix="/api/classes",
    tags=["classes"],
    dependencies=[
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.analytics_read.value)),
    ],
)


@router.get("", response_model=list[ClassResponse])
async def list_classes(
    period: str | None = Query(default=None),
    year: str | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get all classes with statistics."""
    service = ClassService(session)
    view = ClassDefaultView()

    data = service.list_classes_with_stats(current_user=current_user, period=period, year=year)
    return view.render_list(data)


@router.get("/{class_id}/heatmap")
async def get_class_heatmap(
    class_id: UUID,
    period: str | None = Query(default=None, description="Period filter"),
    year: str | None = Query(default=None, description="Year filter"),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get heatmap data for a specific class."""
    service = ClassService(session)
    view = ClassDefaultView()

    data = service.get_class_heatmap(current_user=current_user, class_id=class_id, period=period, year=year)
    if not data:
        raise HTTPException(status_code=404, detail=f"Class ID '{class_id}' not found or has no data")
    return view.render_heatmap(data)


@router.get("/{class_id}/rankings", response_model=TopBottomResponse)
async def get_class_rankings(
    class_id: UUID,
    period: str | None = Query(default=None, description="Period filter"),
    top_n: int = Query(default=5, ge=1, le=20, description="Number of top students"),
    bottom_n: int = Query(default=5, ge=1, le=20, description="Number of bottom students"),
    year: str | None = Query(default=None, description="Year filter"),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get top and bottom students in a class."""
    service = ClassService(session)
    view = ClassDefaultView()

    data = service.get_top_bottom_students(
        current_user=current_user,
        class_id=class_id,
        period=period,
        top_n=top_n,
        bottom_n=bottom_n,
        year=year,
    )
    return view.render_rankings(data)
