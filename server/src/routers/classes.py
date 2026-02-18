from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_class_service
from ..schemas.analytics import TopBottomResponse
from ..schemas.student import ClassResponse
from ..services.classes import ClassService
from ..views.classes import ClassDefaultView

router = APIRouter(prefix="/api/classes", tags=["classes"])


@router.get("", response_model=list[ClassResponse])
async def list_classes(
    period: str | None = Query(default=None),
    service: ClassService = Depends(get_class_service),
):
    """Get all classes with statistics."""
    view = ClassDefaultView()

    data = service.list_classes_with_stats(period)
    return view.render_list(data)


@router.get("/{class_id}/heatmap")
async def get_class_heatmap(
    class_id: UUID,
    period: str | None = Query(default=None, description="Period filter"),
    service: ClassService = Depends(get_class_service),
):
    """Get heatmap data for a specific class."""
    view = ClassDefaultView()

    data = service.get_class_heatmap(class_id, period)
    if not data:
        raise HTTPException(status_code=404, detail=f"Class ID '{class_id}' not found or has no data")
    return view.render_heatmap(data)


@router.get("/{class_id}/rankings", response_model=TopBottomResponse)
async def get_class_rankings(
    class_id: UUID,
    period: str | None = Query(default=None, description="Period filter"),
    top_n: int = Query(default=5, ge=1, le=20, description="Number of top students"),
    bottom_n: int = Query(default=5, ge=1, le=20, description="Number of bottom students"),
    service: ClassService = Depends(get_class_service),
):
    """Get top and bottom students in a class."""
    view = ClassDefaultView()

    data = service.get_top_bottom_students(class_id, period, top_n, bottom_n)
    return view.render_rankings(data)
