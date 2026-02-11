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


class TeacherListItem(BaseModel):
    """Teacher in the teachers list."""

    id: str
    name: str
    subject_count: int
    student_count: int
    average_grade: float | None


class GradeHistogramBin(BaseModel):
    """Single bin in a grade histogram."""

    grade: int
    count: int


class TeacherClassPerformance(BaseModel):
    """Per-class performance for a teacher."""

    class_name: str
    class_id: str
    average_grade: float
    student_count: int
    distribution: list[GradeDistributionItem]
    grade_histogram: list[GradeHistogramBin]


class TeacherSubjectPerformance(BaseModel):
    """Per-subject performance for a teacher."""

    subject: str
    average_grade: float
    student_count: int


class TeacherDetailResponse(BaseModel):
    """Detailed teacher analytics."""

    id: str
    name: str
    subjects: list[str]
    classes: list[str]
    student_count: int
    average_grade: float | None
    distribution: list[GradeDistributionItem]
    grade_histogram: list[GradeHistogramBin]
    class_performance: list[TeacherClassPerformance]
    subject_performance: list[TeacherSubjectPerformance]
