"""Dashboard analytics routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..database import get_session
from ..schemas.analytics import (
    CascadingFilterOptions,
    ClassComparisonItem,
    LayerKPIsResponse,
    MetadataResponse,
    PeriodComparisonResponse,
    RedStudentListResponse,
    RedStudentSegmentation,
    SubjectGradeItem,
    VersusChartData,
)
from ..services.analytics import AnalyticsService
from ..views.analytics import AnalyticsDefaultView

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/kpis", response_model=LayerKPIsResponse)
async def get_layer_kpis(
    period: str | None = Query(default=None, description="Period filter (e.g., 'Q1')"),
    grade_level: str | None = Query(default=None, description="Grade level filter (e.g., 'י')"),
    session: Session = Depends(get_session),
):
    """Get Dashboard KPIs."""
    service = AnalyticsService(session)
    view = AnalyticsDefaultView()
    
    data = service.get_layer_kpis(period, grade_level)
    return view.render_kpis(data)


@router.get("/class-comparison", response_model=list[ClassComparisonItem])
async def get_class_comparison(
    period: str | None = Query(default=None, description="Period filter"),
    grade_level: str | None = Query(default=None, description="Grade level filter"),
    session: Session = Depends(get_session),
):
    """Get class comparison data."""
    service = AnalyticsService(session)
    view = AnalyticsDefaultView()
    
    data = service.get_class_comparison(period, grade_level)
    return view.render_class_comparison(data)


@router.get("/student/{student_tz}/radar", response_model=list[SubjectGradeItem])
async def get_student_radar(
    student_tz: str,
    period: str | None = Query(default=None, description="Period filter"),
    session: Session = Depends(get_session),
):
    """Get radar chart data for a student."""
    service = AnalyticsService(session)
    view = AnalyticsDefaultView()
    
    data = service.get_student_radar(student_tz, period)
    if not data:
        raise HTTPException(status_code=404, detail=f"Student '{student_tz}' not found or has no grades")
        
    return view.render_student_radar(data)


@router.get("/metadata", response_model=MetadataResponse)
async def get_metadata(
    session: Session = Depends(get_session),
):
    """Get available filter options."""
    service = AnalyticsService(session)
    view = AnalyticsDefaultView()
    
    data = service.get_metadata_options()
    return view.render_metadata(data)


@router.get("/period-comparison", response_model=PeriodComparisonResponse)
async def get_period_comparison(
    period_a: str = Query(..., description="First period to compare"),
    period_b: str = Query(..., description="Second period to compare"),
    comparison_type: str = Query(
        default="class",
        description="Comparison type: class, subject_teacher, or subject",
    ),
    grade_level: str | None = Query(default=None, description="Grade level filter"),
    class_id: str | None = Query(default=None, description="Class ID filter"),
    session: Session = Depends(get_session),
):
    """Compare average grades between two periods."""
    service = AnalyticsService(session)
    view = AnalyticsDefaultView()
    
    data = service.get_period_comparison(
        period_a=period_a,
        period_b=period_b,
        comparison_type=comparison_type,
        grade_level=grade_level,
        class_id=class_id,
    )
    return view.render_period_comparison(data)


@router.get("/red-students/segmentation", response_model=RedStudentSegmentation)
async def get_red_student_segmentation(
    period: str | None = Query(default=None, description="Period filter"),
    grade_level: str | None = Query(default=None, description="Grade level filter"),
    session: Session = Depends(get_session),
):
    """Get at-risk student segmentation."""
    service = AnalyticsService(session)
    view = AnalyticsDefaultView()
    
    data = service.get_red_student_segmentation(
        period=period,
        grade_level=grade_level,
    )
    return view.render_red_student_segmentation(data)


@router.get("/red-students/list", response_model=RedStudentListResponse)
async def get_red_student_list(
    period: str | None = Query(default=None, description="Period filter"),
    grade_level: str | None = Query(default=None, description="Grade level filter"),
    class_id: str | None = Query(default=None, description="Class ID filter"),
    teacher_name: str | None = Query(default=None, description="Teacher name filter"),
    subject: str | None = Query(default=None, description="Subject filter"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_session),
):
    """Get paginated list of at-risk students."""
    service = AnalyticsService(session)
    view = AnalyticsDefaultView()
    
    data = service.get_red_student_list(
        period=period,
        grade_level=grade_level,
        class_id=class_id,
        teacher_name=teacher_name,
        subject=subject,
        page=page,
        page_size=page_size,
    )
    return view.render_red_student_list(data)


@router.get("/versus", response_model=VersusChartData)
async def get_versus_comparison(
    comparison_type: str = Query(..., description="Type of comparison: class, teacher, or layer"),
    entity_ids: str = Query(..., description="Comma-separated list of entity IDs to compare"),
    period: str | None = Query(default=None, description="Period filter"),
    metric: str = Query(default="average_grade", description="Metric to compare: average_grade or at_risk_count"),
    session: Session = Depends(get_session),
):
    """Get versus comparison data."""
    service = AnalyticsService(session)
    view = AnalyticsDefaultView()
    
    ids = [id.strip() for id in entity_ids.split(",")]
    
    data = service.get_versus_comparison(
        comparison_type=comparison_type,
        entity_ids=ids,
        period=period,
        metric=metric,
    )
    return view.render_versus_comparison(data)


@router.get("/filter-options", response_model=CascadingFilterOptions)
async def get_cascading_filter_options(
    grade_level: str | None = Query(default=None, description="Selected grade level"),
    class_id: str | None = Query(default=None, description="Selected class ID"),
    period: str | None = Query(default=None, description="Selected period"),
    session: Session = Depends(get_session),
):
    """Get available filter options."""
    service = AnalyticsService(session)
    view = AnalyticsDefaultView()
    
    data = service.get_cascading_filter_options(
        grade_level=grade_level,
        class_id=class_id,
        period=period,
    )
    return view.render_cascading_filter_options(data)
