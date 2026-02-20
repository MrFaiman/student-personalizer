from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Index
from sqlmodel import Field, Relationship, SQLModel


class Teacher(SQLModel, table=True):
    """Teacher record."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)

    # Relationships
    grades: list["Grade"] = Relationship(back_populates="teacher")


class Class(SQLModel, table=True):
    """Class/homeroom."""

    __table_args__ = (
        Index("ix_class_grade_level", "grade_level"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    class_name: str = Field(index=True, unique=True)  # e.g. "י-1"
    grade_level: str  # e.g. "10", "י"

    # Relationships
    students: list["Student"] = Relationship(back_populates="class_")


class Student(SQLModel, table=True):
    """Student master record."""

    __table_args__ = (
        Index("ix_student_class_id", "class_id"),
    )

    student_tz: str = Field(primary_key=True)  # ID Card / Unique ID (ת.ז)
    student_name: str
    class_id: UUID | None = Field(default=None, foreign_key="class.id")

    # Relationships
    class_: Class = Relationship(back_populates="students")
    grades: list["Grade"] = Relationship(back_populates="student")
    attendance_records: list["AttendanceRecord"] = Relationship(back_populates="student")


class Grade(SQLModel, table=True):
    """Individual grade record."""

    __table_args__ = (
        Index("ix_grade_student_period", "student_tz", "period"),
        Index("ix_grade_teacher_id_period", "teacher_id", "period"),
        Index("ix_grade_teacher_name_period", "teacher_name", "period"),
        CheckConstraint("grade >= 0 AND grade <= 100", name="ck_grade_range"),
    )

    id: int | None = Field(default=None, primary_key=True)
    student_tz: str = Field(foreign_key="student.student_tz", index=True)
    subject: str
    teacher_name: str | None = None
    teacher_id: UUID | None = Field(default=None, foreign_key="teacher.id", index=True)
    grade: float
    period: str  # e.g. "Quarter 1", "סמסטר א'"

    # Relationships
    student: Student = Relationship(back_populates="grades")
    teacher: Teacher | None = Relationship(back_populates="grades")


class AttendanceRecord(SQLModel, table=True):
    """Attendance and behavior record."""

    __table_args__ = (
        Index("ix_attendance_student_period", "student_tz", "period"),
        CheckConstraint("lessons_reported >= 0", name="ck_attendance_lessons_reported"),
        CheckConstraint("absence >= 0", name="ck_attendance_absence"),
        CheckConstraint("late >= 0", name="ck_attendance_late"),
    )

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

    # Relationships
    student: Student = Relationship(back_populates="attendance_records")


class UploadedFile(SQLModel, table=True):
    """Track uploaded files saved to disk."""

    __table_args__ = (
        Index("ix_uploadedfile_uploaded_at", "uploaded_at"),
        Index("ix_uploadedfile_checksum", "checksum", unique=True),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    original_filename: str
    stored_path: str  # relative path inside UPLOAD_DIR
    content_type: str
    file_size: int  # bytes
    checksum: str  # SHA-256 hex digest
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    import_log: Optional["ImportLog"] = Relationship(back_populates="uploaded_file")


class ImportLog(SQLModel, table=True):
    """Track file imports."""

    __table_args__ = (
        Index("ix_importlog_created_at", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    batch_id: str = Field(index=True)
    filename: str
    file_type: str  # "grades" or "events"
    rows_imported: int = 0
    rows_failed: int = 0
    errors: str | None = None  # JSON string of errors
    period: str | None = None
    uploaded_file_id: UUID | None = Field(default=None, foreign_key="uploadedfile.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    uploaded_file: UploadedFile | None = Relationship(back_populates="import_log")
