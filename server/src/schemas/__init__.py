"""Pydantic schemas for API responses."""

from .advanced_analytics import (
    CascadingFilterOptions,
    ClassOption,
    FailingSubject,
    PeriodComparisonItem,
    PeriodComparisonResponse,
    RedStudentDetail,
    RedStudentGroup,
    RedStudentListResponse,
    RedStudentSegmentation,
    TeacherOption,
    VersusChartData,
    VersusSeriesItem,
)
from .analytics import (
    ClassComparisonItem,
    GradeDistributionItem,
    LayerKPIsResponse,
    MetadataResponse,
    StudentRankItem,
    SubjectGradeItem,
    TeacherStatsResponse,
    TopBottomResponse,
)
from .ingestion import (
    ImportLogResponse,
    ImportResponse,
)
from .student import (
    AttendanceResponse,
    ClassResponse,
    DashboardStats,
    GradeResponse,
    StudentDetailResponse,
    StudentListResponse,
    StudentResponse,
)

__all__ = [
    # Student schemas
    "StudentResponse",
    "StudentDetailResponse",
    "GradeResponse",
    "AttendanceResponse",
    "StudentListResponse",
    "ClassResponse",
    "DashboardStats",
    # Analytics schemas
    "LayerKPIsResponse",
    "ClassComparisonItem",
    "StudentRankItem",
    "TopBottomResponse",
    "GradeDistributionItem",
    "TeacherStatsResponse",
    "SubjectGradeItem",
    "MetadataResponse",
    # Grades analytics schemas
    "PeriodComparisonItem",
    "PeriodComparisonResponse",
    "RedStudentGroup",
    "FailingSubject",
    "RedStudentDetail",
    "RedStudentSegmentation",
    "RedStudentListResponse",
    "VersusSeriesItem",
    "VersusChartData",
    "ClassOption",
    "TeacherOption",
    "CascadingFilterOptions",
    # Ingestion schemas
    "ImportResponse",
    "ImportLogResponse",
]
