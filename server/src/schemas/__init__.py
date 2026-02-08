"""Pydantic schemas for API responses."""

from .student import (
    StudentResponse,
    StudentDetailResponse,
    GradeResponse,
    AttendanceResponse,
    StudentListResponse,
    ClassResponse,
    DashboardStats,
)

from .analytics import (
    LayerKPIsResponse,
    ClassComparisonItem,
    StudentRankItem,
    TopBottomResponse,
    GradeDistributionItem,
    TeacherStatsResponse,
    SubjectGradeItem,
    MetadataResponse,
)

from .ingestion import (
    ImportResponse,
    ImportLogResponse,
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
    # Ingestion schemas
    "ImportResponse",
    "ImportLogResponse",
]
