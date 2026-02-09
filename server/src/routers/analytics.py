"""Dashboard analytics routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..database import get_session
from ..schemas.analytics import (
    ClassComparisonItem,
    LayerKPIsResponse,
    MetadataResponse,
    SubjectGradeItem,
    TeacherStatsResponse,
    TopBottomResponse,
)
from ..services.analytics import DashboardAnalytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# Routes
@router.get("/kpis", response_model=LayerKPIsResponse)
async def get_layer_kpis(
    period: str | None = Query(default=None, description="Period filter (e.g., 'Q1')"),
    grade_level: str | None = Query(default=None, description="Grade level filter (e.g., 'י')"),
    session: Session = Depends(get_session),
):
    """
    Get Dashboard KPIs for a layer/grade level.
    
    Returns:
    - layer_average: Average grade across all students
    - avg_absences: Average number of absences per student
    - at_risk_students: Count of students with average < 55
    - total_students: Total number of students
    """
    analytics = DashboardAnalytics(session)
    return analytics.get_layer_kpis(period=period, grade_level=grade_level)


@router.get("/class-comparison", response_model=list[ClassComparisonItem])
async def get_class_comparison(
    period: str | None = Query(default=None, description="Period filter"),
    grade_level: str | None = Query(default=None, description="Grade level filter"),
    session: Session = Depends(get_session),
):
    """
    Get class comparison data for bar chart.
    
    Returns list of classes with their average grades.
    """
    analytics = DashboardAnalytics(session)
    return analytics.get_class_comparison(period=period, grade_level=grade_level)


@router.get("/class/{class_id}/heatmap")
async def get_class_heatmap(
    class_id: int,
    period: str | None = Query(default=None, description="Period filter"),
    session: Session = Depends(get_session),
):
    """
    Get heatmap data for a specific class.
    
    Returns a matrix of students x subjects with grades.
    Each row represents a student with their grades per subject.
    """
    analytics = DashboardAnalytics(session)
    data = analytics.get_class_heatmap(class_id=class_id, period=period)
    
    if not data:
        raise HTTPException(status_code=404, detail=f"Class ID '{class_id}' not found or has no data")
    
    return data


@router.get("/class/{class_id}/rankings", response_model=TopBottomResponse)
async def get_class_rankings(
    class_id: int,
    period: str | None = Query(default=None, description="Period filter"),
    top_n: int = Query(default=5, ge=1, le=20, description="Number of top students"),
    bottom_n: int = Query(default=5, ge=1, le=20, description="Number of bottom students"),
    session: Session = Depends(get_session),
):
    """
    Get top and bottom students in a class.
    
    Returns:
    - top: List of top N students by average grade
    - bottom: List of bottom N students by average grade
    """
    analytics = DashboardAnalytics(session)
    return analytics.get_top_bottom_students(
        class_id=class_id,
        period=period,
        top_n=top_n,
        bottom_n=bottom_n,
    )


@router.get("/teacher/{teacher_name}/stats", response_model=TeacherStatsResponse)
async def get_teacher_stats(
    teacher_name: str,
    period: str | None = Query(default=None, description="Period filter"),
    session: Session = Depends(get_session),
):
    """
    Get grade distribution statistics for a teacher.
    
    Returns distribution of grades in categories:
    - Fail (<55)
    - Medium (55-75)
    - Good (76-90)
    - Excellent (>90)
    """
    analytics = DashboardAnalytics(session)
    result = analytics.get_teacher_stats(teacher_name=teacher_name, period=period)
    
    if result["total_students"] == 0:
        raise HTTPException(status_code=404, detail=f"Teacher '{teacher_name}' not found or has no grades")
    
    return result


@router.get("/student/{student_tz}/radar", response_model=list[SubjectGradeItem])
async def get_student_radar(
    student_tz: str,
    period: str | None = Query(default=None, description="Period filter"),
    session: Session = Depends(get_session),
):
    """
    Get radar chart data for a student.
    
    Returns list of subjects with the student's average grade in each.
    """
    analytics = DashboardAnalytics(session)
    data = analytics.get_student_radar(student_tz=student_tz, period=period)
    
    if not data:
        raise HTTPException(status_code=404, detail=f"Student '{student_tz}' not found or has no grades")
    
    return data


@router.get("/teachers", response_model=list[str])
async def list_teachers(
    period: str | None = Query(default=None, description="Period filter"),
    session: Session = Depends(get_session),
):
    """Get list of all teachers with grades."""
    analytics = DashboardAnalytics(session)
    return analytics.get_available_teachers(period=period)


@router.get("/metadata", response_model=MetadataResponse)
async def get_metadata(
    session: Session = Depends(get_session),
):
    """
    Get available filter options.
    
    Returns:
    - periods: Available time periods
    - grade_levels: Available grade levels (e.g., "י", "יא")
    - teachers: Available teachers
    """
    analytics = DashboardAnalytics(session)
    return MetadataResponse(
        periods=analytics.get_available_periods(),
        grade_levels=analytics.get_available_grade_levels(),
        teachers=analytics.get_available_teachers(),
    )
