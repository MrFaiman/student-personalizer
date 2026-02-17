"""Grades analytics schemas for period comparison and risk analysis."""

from pydantic import BaseModel


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
