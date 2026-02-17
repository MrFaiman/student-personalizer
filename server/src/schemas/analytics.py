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


class GradeHistogramBin(BaseModel):
    """Single bin in a grade histogram."""

    grade: int
    count: int


class TeacherDetailResponse(BaseModel):
    """Detailed teacher analytics."""

    id: str
    name: str
    stats: TeacherDetailStats
    subjects: list[str]
    classes: list[TeacherClassDetail]
    grade_histogram: list[GradeHistogramBin]


class PeriodComparisonItem(BaseModel):
    """Single item in period comparison."""

    id: str
    name: str
    period_a_average: float | None
    period_b_average: float | None
    change: float | None
    change_percent: float | None
    student_count_a: int
    student_count_b: int
    teacher_name: str | None = None
    subject: str | None = None
    class_name: str | None = None


class PeriodComparisonResponse(BaseModel):
    """Response for period comparison endpoint."""

    comparison_type: str
    period_a: str
    period_b: str
    data: list[PeriodComparisonItem]


class RedStudentGroup(BaseModel):
    """Grouping of at-risk students."""

    id: str
    name: str
    red_student_count: int
    total_student_count: int
    percentage: float
    average_grade: float


class FailingSubject(BaseModel):
    """Subject where student is failing."""

    subject: str
    teacher_name: str | None
    grade: float


class RedStudentDetail(BaseModel):
    """Detailed at-risk student info."""

    student_tz: str
    student_name: str
    class_name: str | None
    grade_level: str | None
    average_grade: float
    failing_subjects: list[FailingSubject]


class RedStudentSegmentation(BaseModel):
    """Full red student segmentation response."""

    total_red_students: int
    threshold: float
    by_class: list[RedStudentGroup]
    by_layer: list[RedStudentGroup]
    by_teacher: list[RedStudentGroup]
    by_subject: list[RedStudentGroup]


class RedStudentListResponse(BaseModel):
    """Paginated list of red students."""

    total: int
    page: int
    page_size: int
    students: list[RedStudentDetail]


class VersusSeriesItem(BaseModel):
    """Single series in versus comparison."""

    id: str
    name: str
    value: float
    student_count: int
    subjects: list[str] = []
    teacher_name: str | None = None


class VersusChartData(BaseModel):
    """Response for versus comparison chart."""

    comparison_type: str
    metric: str
    series: list[VersusSeriesItem]


class ClassOption(BaseModel):
    """Class option for cascading filters."""

    id: str
    class_name: str
    grade_level: str


class TeacherOption(BaseModel):
    """Teacher option for cascading filters."""

    id: str | None
    name: str
    subjects: list[str]


class CascadingFilterOptions(BaseModel):
    """Available options for cascading filters."""

    classes: list[ClassOption]
    teachers: list[TeacherOption]
    subjects: list[str]
