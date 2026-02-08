"""Pydantic schemas for API responses."""

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
    # Ingestion schemas
    "ImportResponse",
    "ImportLogResponse",
]
