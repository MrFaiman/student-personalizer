"""Analytics-related schemas."""

from pydantic import BaseModel


class LayerKPIsResponse(BaseModel):
    """Layer/grade-level KPIs."""

    layer_average: float | None
    avg_absences: float
    at_risk_students: int
    total_students: int


class ClassComparisonItem(BaseModel):
    """Single class in comparison chart."""

    id: int
    class_name: str
    average_grade: float
    student_count: int


class StudentRankItem(BaseModel):
    """Student ranking item."""

    student_name: str
    student_tz: str
    average: float


class TopBottomResponse(BaseModel):
    """Top and bottom students response."""

    top: list[StudentRankItem]
    bottom: list[StudentRankItem]


class GradeDistributionItem(BaseModel):
    """Grade distribution category."""

    category: str
    count: int


class TeacherStatsResponse(BaseModel):
    """Teacher statistics response."""

    teacher_name: str
    distribution: list[GradeDistributionItem]
    total_students: int
    average_grade: float | None


class SubjectGradeItem(BaseModel):
    """Subject grade for radar chart."""

    subject: str
    grade: float


class MetadataResponse(BaseModel):
    """Available filters metadata."""

    periods: list[str]
    grade_levels: list[str]
    teachers: list[str]
