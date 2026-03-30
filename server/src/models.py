from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, Index
from sqlmodel import Field, Relationship, SQLModel

from .crypto.encrypted_type import EncryptedString


class Teacher(SQLModel, table=True):
    """Teacher record."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)

    # Relationships
    grades: list["Grade"] = Relationship(back_populates="teacher")


class Subject(SQLModel, table=True):
    """Subject record."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)

    # Relationships
    grades: list["Grade"] = Relationship(back_populates="subject")


class Class(SQLModel, table=True):
    """Class/homeroom."""

    __table_args__ = (
        Index("ix_class_grade_level", "grade_level"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    class_name: str = Field(index=True, unique=True)  # e.g. "י-1"
    grade_level: str  # e.g. "10", "י"
    class_num: int | None = None  # extracted from "י-1" -> 1

    # Relationships
    students: list["Student"] = Relationship(back_populates="class_")


class Student(SQLModel, table=True):
    """Student master record."""

    __table_args__ = (
        Index("ix_student_class_id", "class_id"),
        Index("ix_student_tz_hash", "student_tz_hash"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    student_tz: str = Field(index=True, unique=True)
    student_tz_hash: str = Field(default="")
    student_name: str = Field(sa_column=Column("student_name", EncryptedString, nullable=False))
    class_id: UUID | None = Field(default=None, foreign_key="class.id")

    # Relationships
    class_: Class = Relationship(back_populates="students")
    grades: list["Grade"] = Relationship(back_populates="student")
    attendance_records: list["AttendanceRecord"] = Relationship(back_populates="student")


class Grade(SQLModel, table=True):
    """Individual grade record."""

    __table_args__ = (
        Index("ix_grade_student_period_year", "student_tz", "period", "year"),
        Index("ix_grade_teacher_id_period_year", "teacher_id", "period", "year"),
        Index("ix_grade_teacher_name_period_year", "teacher_name", "period", "year"),
        Index("ix_grade_subject_name_period_year", "subject_name", "period", "year"),
        Index("ix_grade_subject_id_period_year", "subject_id", "period", "year"),
        Index("ix_grade_year", "year"),
        CheckConstraint("grade >= 0 AND grade <= 100", name="ck_grade_range"),
    )

    id: int | None = Field(default=None, primary_key=True)
    student_tz: str = Field(foreign_key="student.student_tz", index=True)
    subject_name: str
    subject_id: UUID | None = Field(default=None, foreign_key="subject.id", index=True)
    teacher_name: str | None = None
    teacher_id: UUID | None = Field(default=None, foreign_key="teacher.id", index=True)
    grade: float
    period: str  # e.g. "Quarter 1", "סמסטר א'"
    year: str = Field(default="")

    # Relationships
    student: Student = Relationship(back_populates="grades")
    teacher: Teacher | None = Relationship(back_populates="grades")
    subject: Subject | None = Relationship(back_populates="grades")


class AttendanceRecord(SQLModel, table=True):
    """Attendance and behavior record."""

    __table_args__ = (
        Index("ix_attendance_student_period_year", "student_tz", "period", "year"),
        Index("ix_attendance_year", "year"),
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
    year: str = Field(default="")

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


class OpenDayImport(SQLModel, table=True):
    """Track open day file imports."""

    __table_args__ = (
        Index("ix_opendayimport_import_date", "import_date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    batch_id: str = Field(index=True, unique=True)
    filename: str
    rows_imported: int = 0
    rows_failed: int = 0
    import_date: datetime = Field(default_factory=datetime.utcnow)

    registrations: list["OpenDayRegistration"] = Relationship(back_populates="import_log")


class OpenDayRegistration(SQLModel, table=True):
    """Registration submitted during an open day event."""

    __table_args__ = (
        Index("ix_opendayreg_import_id", "import_id"),
        Index("ix_opendayreg_next_grade", "next_grade"),
        Index("ix_opendayreg_interested_track", "interested_track"),
    )

    id: int | None = Field(default=None, primary_key=True)
    import_id: int | None = Field(default=None, foreign_key="opendayimport.id", index=True)
    submitted_at: datetime | None = None

    # PII fields - encrypted via EncryptedString TypeDecorator
    first_name: str = Field(sa_column=Column("first_name", EncryptedString, nullable=False))
    last_name: str = Field(sa_column=Column("last_name", EncryptedString, nullable=False))
    student_id: str | None = Field(default=None)
    parent_name: str | None = Field(sa_column=Column("parent_name", EncryptedString, nullable=True))
    phone: str | None = Field(sa_column=Column("phone", EncryptedString, nullable=True))
    email: str | None = Field(sa_column=Column("email", EncryptedString, nullable=True))

    current_school: str | None = None
    next_grade: str | None = None
    interested_track: str | None = None
    referral_source: str | None = None
    additional_notes: str | None = None
    import_date: datetime = Field(default_factory=datetime.utcnow)

    import_log: OpenDayImport | None = Relationship(back_populates="registrations")


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
    year: str = Field(default="")
    uploaded_file_id: UUID | None = Field(default=None, foreign_key="uploadedfile.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    uploaded_file: UploadedFile | None = Relationship(back_populates="import_log")
