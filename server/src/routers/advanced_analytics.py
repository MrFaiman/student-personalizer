"""Grades analytics API routes."""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from ..database import get_session
from ..schemas.advanced_analytics import (
    CascadingFilterOptions,
    PeriodComparisonResponse,
    RedStudentListResponse,
    RedStudentSegmentation,
    VersusChartData,
)
from ..services.advanced_analytics import AdvancedAnalytics

router = APIRouter(prefix="/api/advanced-analytics", tags=["advanced-analytics"])


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
    """
    Compare average grades between two periods.

    Returns comparison data formatted for multi-series bar charts.
    Supports three comparison types:
    - class: Compare class averages
    - subject_teacher: Compare subject-teacher combination averages
    - subject: Compare subject averages
    """
    analytics = AdvancedAnalytics(session)
    return analytics.get_period_comparison(
        period_a=period_a,
        period_b=period_b,
        comparison_type=comparison_type,
        grade_level=grade_level,
        class_id=class_id,
    )


@router.get("/red-students/segmentation", response_model=RedStudentSegmentation)
async def get_red_student_segmentation(
    period: str | None = Query(default=None, description="Period filter"),
    grade_level: str | None = Query(default=None, description="Grade level filter"),
    session: Session = Depends(get_session),
):
    """
    Get at-risk student segmentation by class, layer, teacher, and subject.

    Red students are those with average grade below the threshold (default: 55).
    Returns breakdowns showing distribution of at-risk students across dimensions.
    """
    analytics = AdvancedAnalytics(session)
    return analytics.get_red_student_segmentation(
        period=period,
        grade_level=grade_level,
    )


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
    """
    Get paginated list of at-risk students with details.

    Returns detailed information including failing subjects for each student.
    Results are sorted by average grade ascending (worst performers first).
    """
    analytics = AdvancedAnalytics(session)
    return analytics.get_red_student_list(
        period=period,
        grade_level=grade_level,
        class_id=class_id,
        teacher_name=teacher_name,
        subject=subject,
        page=page,
        page_size=page_size,
    )


@router.get("/versus", response_model=VersusChartData)
async def get_versus_comparison(
    comparison_type: str = Query(
        ...,
        description="Type of comparison: class, teacher, or layer",
    ),
    entity_ids: str = Query(
        ...,
        description="Comma-separated list of entity IDs to compare",
    ),
    period: str | None = Query(default=None, description="Period filter"),
    metric: str = Query(
        default="average_grade",
        description="Metric to compare: average_grade or at_risk_count",
    ),
    session: Session = Depends(get_session),
):
    """
    Get versus comparison data for unified comparison chart.

    Supports Class vs Class, Teacher vs Teacher, or Layer vs Layer comparisons.
    Select 2-6 entities to compare their performance metrics.
    """
    analytics = AdvancedAnalytics(session)
    ids = [id.strip() for id in entity_ids.split(",")]
    return analytics.get_versus_comparison(
        comparison_type=comparison_type,
        entity_ids=ids,
        period=period,
        metric=metric,
    )


@router.get("/filter-options", response_model=CascadingFilterOptions)
async def get_cascading_filter_options(
    grade_level: str | None = Query(default=None, description="Selected grade level"),
    class_id: str | None = Query(default=None, description="Selected class ID"),
    period: str | None = Query(default=None, description="Selected period"),
    session: Session = Depends(get_session),
):
    """
    Get available filter options based on current selections.

    Implements cascading filter logic where selecting a grade level
    filters the available classes and teachers.
    """
    analytics = AdvancedAnalytics(session)
    return analytics.get_cascading_filter_options(
        grade_level=grade_level,
        class_id=class_id,
        period=period,
    )
