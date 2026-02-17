"""Analytics-related schemas."""

from uuid import UUID

from pydantic import BaseModel


class LayerKPIsResponse(BaseModel):
    """Layer/grade-level KPIs."""

    layer_average: float | None
    avg_absences: float
    at_risk_students: int
    total_students: int


class ClassComparisonItem(BaseModel):
    """Single class in comparison chart."""

    id: UUID
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
    distribution: dict
    total_students: int
    average_grade: float | None
    subjects: list[str] = []


class SubjectGradeItem(BaseModel):
    """Subject grade for radar chart."""

    subject: str
    grade: float


class MetadataResponse(BaseModel):
    """Available filters metadata."""

    periods: list[str]
    grade_levels: list[str]
    teachers: list[str]


class TeacherListItem(BaseModel):
    """Teacher in the teachers list."""

    id: str | None
    name: str
    subjects: list[str] = []
    student_count: int
    average_grade: float | None


class TeacherDetailStats(BaseModel):
    """Aggregated stats for a teacher."""

    student_count: int
    average_grade: float | None
    at_risk_count: int
    classes_count: int


class TeacherClassDetail(BaseModel):
    """Per-class detail for a teacher."""

    id: str
    name: str
    student_count: int
    average_grade: float
    at_risk_count: int


class TeacherDetailResponse(BaseModel):
    """Detailed teacher analytics."""

    id: str
    name: str
    stats: TeacherDetailStats
    subjects: list[str]
    classes: list[TeacherClassDetail]
