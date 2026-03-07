"""Subject-related schemas."""

from pydantic import BaseModel

from .analytics import GradeHistogramBin


class SubjectListItem(BaseModel):
    """Subject in the subjects list."""

    id: str | None
    name: str
    student_count: int
    average_grade: float | None
    teachers: list[str] = []


class SubjectStatsResponse(BaseModel):
    """Subject distribution statistics response."""

    subject_name: str
    distribution: dict
    total_students: int
    average_grade: float | None
    teachers: list[str] = []


class SubjectDetailStats(BaseModel):
    """Aggregated stats for a subject."""

    student_count: int
    average_grade: float | None
    at_risk_count: int
    classes_count: int


class SubjectClassDetail(BaseModel):
    """Per-class detail for a subject."""

    id: str
    name: str
    student_count: int
    average_grade: float
    at_risk_count: int


class SubjectDetailResponse(BaseModel):
    """Detailed analytics for a specific subject identity."""

    id: str
    name: str
    stats: SubjectDetailStats
    teachers: list[str]
    classes: list[SubjectClassDetail]
    grade_histogram: list[GradeHistogramBin]
