"""Student-related schemas."""

from uuid import UUID

from pydantic import BaseModel


class StudentResponse(BaseModel):
    """Response model for student data."""

    student_tz: str
    student_name: str
    class_id: UUID | None
    class_name: str
    grade_level: str | None


class StudentDetailResponse(StudentResponse):
    """Detailed student response with aggregated data."""

    average_grade: float | None
    total_absences: int
    total_negative_events: int
    total_positive_events: int
    is_at_risk: bool
    performance_score: float | None = None


class GradeResponse(BaseModel):
    """Response model for grade data."""

    id: int
    subject: str
    teacher_name: str | None
    grade: float
    period: str


class AttendanceResponse(BaseModel):
    """Response model for attendance data."""

    id: int
    lessons_reported: int
    absence: int
    absence_justified: int
    late: int
    disturbance: int
    total_absences: int
    attendance: int
    total_negative_events: int
    total_positive_events: int
    period: str


class StudentListResponse(BaseModel):
    """Paginated list of students."""

    items: list[StudentDetailResponse]
    total: int
    page: int
    page_size: int


class ClassResponse(BaseModel):
    """Response model for class data."""

    id: UUID
    class_name: str
    grade_level: str
    student_count: int
    average_grade: float | None
    at_risk_count: int


class DashboardStats(BaseModel):
    """Dashboard KPI statistics."""

    total_students: int
    average_grade: float | None
    at_risk_count: int
    total_classes: int
    classes: list[ClassResponse]
