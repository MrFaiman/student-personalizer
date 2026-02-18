from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


class School(SQLModel, table=True):
    """School / tenant record."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)
    slug: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    """Application user (belongs to a school)."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: str
    role: str = "viewer"  # "admin" / "teacher" / "viewer"
    is_active: bool = True
    school_id: UUID = Field(foreign_key="school.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    school: School = Relationship()


class Teacher(SQLModel, table=True):
    """Teacher record."""

    __table_args__ = (UniqueConstraint("name", "school_id"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    school_id: UUID | None = Field(default=None, foreign_key="school.id", index=True)

    # Relationships
    grades: list["Grade"] = Relationship(back_populates="teacher")


class Class(SQLModel, table=True):
    """Class/homeroom."""

    __table_args__ = (UniqueConstraint("class_name", "school_id"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    class_name: str = Field(index=True)  # e.g. "י-1"
    grade_level: str  # e.g. "10", "י"
    school_id: UUID | None = Field(default=None, foreign_key="school.id", index=True)

    # Relationships
    students: list["Student"] = Relationship(back_populates="class_")


class Student(SQLModel, table=True):
    """Student master record."""

    student_tz: str = Field(primary_key=True)  # ID Card / Unique ID (ת.ז)
    student_name: str
    class_id: UUID | None = Field(default=None, foreign_key="class.id")
    school_id: UUID | None = Field(default=None, foreign_key="school.id", index=True)

    # Relationships
    class_: Class = Relationship(back_populates="students")
    grades: list["Grade"] = Relationship(back_populates="student")
    attendance_records: list["AttendanceRecord"] = Relationship(back_populates="student")


class Grade(SQLModel, table=True):
    """Individual grade record."""

    id: int | None = Field(default=None, primary_key=True)
    student_tz: str = Field(foreign_key="student.student_tz", index=True)
    subject: str
    teacher_name: str | None = None
    teacher_id: UUID | None = Field(default=None, foreign_key="teacher.id", index=True)
    grade: float
    period: str  # e.g. "Quarter 1", "סמסטר א'"
    school_id: UUID | None = Field(default=None, foreign_key="school.id", index=True)

    # Relationships
    student: Student = Relationship(back_populates="grades")
    teacher: Teacher | None = Relationship(back_populates="grades")


class AttendanceRecord(SQLModel, table=True):
    """Attendance and behavior record."""

    id: int | None = Field(default=None, primary_key=True)
    student_tz: str = Field(foreign_key="student.student_tz", index=True)
    lessons_reported: int = 0
    absence: int = 0
    absence_justified: int = 0
    late: int = 0
    disturbance: int = 0
    total_absences: int = 0  # absence - absence_justified (unjustified only)
    attendance: int = 0  # lessons_reported - total_absences
    total_negative_events: int = 0
    total_positive_events: int = 0
    period: str  # e.g. "Quarter 1", "סמסטר א'"
    school_id: UUID | None = Field(default=None, foreign_key="school.id", index=True)

    # Relationships
    student: Student = Relationship(back_populates="attendance_records")


class ImportLog(SQLModel, table=True):
    """Track file imports."""

    id: int | None = Field(default=None, primary_key=True)
    batch_id: str = Field(index=True)
    filename: str
    file_type: str  # "grades" or "events"
    rows_imported: int = 0
    rows_failed: int = 0
    errors: str | None = None  # JSON string of errors
    period: str | None = None
    school_id: UUID | None = Field(default=None, foreign_key="school.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
