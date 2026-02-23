import json
import re
import uuid
from dataclasses import dataclass, field
from io import BytesIO
from uuid import UUID

import pandas as pd
from sqlmodel import Session, select

from ..constants import DEFAULT_PERIOD, MAX_STORED_ERRORS, VALID_MIME_TYPES
from ..models import AttendanceRecord, Class, Grade, ImportLog, Student, Subject, Teacher


def _read_file(file_content: bytes, content_type: str) -> pd.DataFrame:
    """Read CSV or Excel bytes into a DataFrame based on MIME type."""
    mime_format = VALID_MIME_TYPES.get(content_type, "")
    if mime_format == "csv":
        return pd.read_csv(BytesIO(file_content), encoding="utf-8")
    return pd.read_excel(BytesIO(file_content), engine="openpyxl")


def _build_class_name(row) -> str:
    """Build 'grade_level-class_num' string (e.g. 'י-3')."""
    gl = row.get("grade_level")
    cn = row.get("class_num")
    if pd.notna(cn) and pd.notna(gl):
        return f"{gl}-{int(cn)}"
    return str(cn or "")


def _generate_student_tz(row, tz_col: str = "student_tz") -> str:
    """Return cleaned TZ, falling back to name/class combination or row index."""
    tz = row.get(tz_col)
    if pd.notna(tz) and str(tz).strip() and str(tz).strip().lower() != "nan":
        return str(tz).strip()

    # Fallback to student name + class info
    name = str(row.get("student_name", "")).strip()
    grade = str(row.get("grade_level", "")).strip()
    class_num = str(row.get("class_num", "")).strip()

    if name and name.lower() != "nan":
        fallback_str = name
        if grade and grade.lower() != "nan":
            fallback_str += f"_{grade}"
        if class_num and class_num.lower() != "nan":
            fallback_str += f"_{class_num}"
        fallback_str += f"_{row.name}"
        # Generate a consistent positive numeric string of up to 9 digits
        numeric_id = str(abs(hash(fallback_str)))[:9]
        return numeric_id

    serial = row.get("serial_num", 0)
    if pd.notna(serial):
        return f"{int(serial):04d}"
    return f"{row.name:04d}"


@dataclass
class ImportResult:
    """Result of an import operation."""

    batch_id: str
    file_type: str
    rows_imported: int = 0
    rows_failed: int = 0
    errors: list[str] = field(default_factory=list)
    students_created: int = 0
    classes_created: int = 0


def detect_file_type(df: pd.DataFrame) -> str | None:
    """Detect if the file is a grades or events file based on columns."""
    columns = set(df.columns)

    if "ממוצע" in columns or "ת.ז" in columns:
        return "grades"

    if "שיעורים שדווחו" in columns or "חיסור" in columns or "ת.ז. התלמיד" in columns:
        return "events"

    return None


def clean_student_tz(value) -> str:
    """Clean and normalize student TZ (ID)."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def parse_subject_teacher_header(header_str: str) -> tuple[str, str | None]:
    """
    Parse format from column header to extract subject and teacher.
    Supports formats:
    - "{subject}\\n{teacher_name}\\n{teacher_num}"
    """
    clean_header = re.sub(r"\.\d+$", "", str(header_str))

    parts = clean_header.split("\n")
    subject = parts[0].strip()
    
    subject = re.sub(r"\s+[a-zA-Zא-ת]*\d[-a-zA-Zא-ת\d\s]*$", "", subject).strip()
    
    teacher = parts[1].strip() if len(parts) > 1 else None
    return subject, teacher if teacher else None


def load_grades_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse a wide-format grades file where columns 6+ represent "Subject - Teacher".
    Transposes (melts) the data into a long format with columns:
    student_tz, student_name, class_name, grade_level, subject, teacher_name, grade
    """
    metadata_map = {
        "מס'": "serial_num",
        "ת.ז": "student_tz",
        "שם התלמיד": "student_name",
        "שכבה": "grade_level",
        "כיתה": "class_num",
    }

    df = df.rename(columns=metadata_map)

    df["class_name"] = df.apply(_build_class_name, axis=1)
    df["student_tz"] = df.apply(_generate_student_tz, axis=1)

    metadata_cols = ["serial_num", "student_tz", "student_name", "grade_level", "class_num", "class_name"]
    existing_meta_cols = [c for c in metadata_cols if c in df.columns]

    grade_cols = [c for c in df.columns if c not in existing_meta_cols and "ממוצע" not in str(c)]

    df_long = df.melt(
        id_vars=existing_meta_cols,
        value_vars=grade_cols,
        var_name="subject_teacher_str",
        value_name="grade",
    )

    parsed_data = [parse_subject_teacher_header(x) for x in df_long["subject_teacher_str"]]
    df_long["subject"] = [x[0] for x in parsed_data]
    df_long["teacher_name"] = [x[1] for x in parsed_data]

    df_long["grade"] = pd.to_numeric(df_long["grade"], errors="coerce")

    df_long = df_long.dropna(subset=["grade"])

    final_cols = ["student_tz", "student_name", "class_name", "class_num", "grade_level", "subject", "teacher_name", "grade"]
    available_cols = [c for c in final_cols if c in df_long.columns]

    return df_long[available_cols]


def load_attendance_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse an attendance/events XLSX file.
    Maps Hebrew columns to English and calculates totals.
    """
    column_map = {
        "מס'": "serial_num",
        "ת.ז. התלמיד": "student_tz_orig",
        "ת.ז": "student_tz_orig",  # Alternative column name
        "שם התלמיד": "student_name",
        "שכבה": "grade_level",
        "כיתה": "class_num",
        "שיעורים שדווחו": "lessons_reported",
        # Negative / Attendance Events
        "חיסור": "absence",
        "חיסור (מוצדק)": "absence_justified",
        "חיסור מוצדק": "absence_justified",  # Alternative
        "איחור": "late",
        "איחור (מוצדק)": "late_justified",
        "איחור מוצדק": "late_justified",  # Alternative
        "הפרעה": "disturbance",
        "אי כניסה לשיעור": "skipped_class",
        "אי כניסה לשיעור (מוצדק)": "skipped_class_justified",
        "אי כניסה לשיעור מוצדק": "skipped_class_justified",  # Alternative
        "תלבושת": "uniform_issue",
        "אי הכנת ש.ב": "no_homework",
        "אי הבאת ציוד": "no_equipment",
        "אי ביצוע מטלות בכיתה": "no_classwork",
        'שימוש בנייד בשטח ביה"ס': "phone_usage",
        "היעדרות בפרטני (מוצדק)": "private_lesson_absence_justified",
        "היעדרות בפרטני מוצדק": "private_lesson_absence_justified",  # Alternative
        # Positive / Other Events
        "חיזוק חיובי": "positive_reinforcement",
        "חיזוק חיובי כיתתי": "positive_reinforcement_class",
        "נוכחות בפרטני": "private_lesson_presence",
    }

    df = df.rename(columns=column_map)

    df["class_name"] = df.apply(_build_class_name, axis=1)
    df["student_tz"] = df.apply(lambda row: _generate_student_tz(row, tz_col="student_tz_orig"), axis=1)

    negative_cols = [
        "absence",
        "absence_justified",
        "late",
        "late_justified",
        "disturbance",
        "skipped_class",
        "skipped_class_justified",
        "uniform_issue",
        "no_homework",
        "no_equipment",
        "no_classwork",
        "phone_usage",
        "private_lesson_absence_justified",
    ]

    positive_cols = [
        "positive_reinforcement",
        "positive_reinforcement_class",
        "private_lesson_presence",
    ]

    all_event_cols = negative_cols + positive_cols + ["lessons_reported"]

    for col in all_event_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            df[col] = 0

    df["total_absences"] = df["absence"]
    df["attendance"] = df["lessons_reported"] - df["total_absences"]

    df["total_negative_events"] = df[negative_cols].sum(axis=1)
    df["total_positive_events"] = df[positive_cols].sum(axis=1)

    return df


class IngestionService:
    """Core service for data ingestion."""

    def __init__(self, session: Session):
        self.session = session

    def _get_or_create(self, model_class, **kwargs):
        """Generic helper to get an existing record or create a new one."""
        statement = select(model_class).filter_by(**kwargs)
        instance = self.session.exec(statement).first()
        if instance:
            return instance, False

        instance = model_class(**kwargs)
        self.session.add(instance)
        self.session.flush()
        return instance, True

    def get_or_create_class(self, class_name: str, grade_level: str, class_num: int | None = None) -> Class:
        """Get existing class or create new one."""
        cls, _ = self._get_or_create(Class, class_name=class_name, grade_level=grade_level, class_num=class_num)
        return cls

    def get_or_create_student(
        self,
        student_tz: str,
        student_name: str,
        class_name: str,
    ) -> tuple[Student, bool]:
        """Get existing student or create new one. Returns (student, created)."""
        cls = self.session.exec(select(Class).where(Class.class_name == class_name)).first()
        class_id = cls.id if cls else None

        statement = select(Student).where(Student.student_tz == student_tz)
        student = self.session.exec(statement).first()

        if student:
            if student.student_name != student_name:
                student.student_name = student_name
            if student.class_id != class_id:
                student.class_id = class_id
            self.session.add(student)
            return student, False

        student = Student(
            student_tz=student_tz,
            student_name=student_name,
            class_id=class_id,
        )
        self.session.add(student)
        self.session.flush()
        return student, True

    def get_or_create_teacher(self, teacher_name: str) -> Teacher:
        """Get existing teacher or create new one."""
        teacher, _ = self._get_or_create(Teacher, name=teacher_name)
        return teacher

    def get_or_create_subject(self, subject_name: str) -> Subject:
        """Get existing subject or create new one."""
        subject, _ = self._get_or_create(Subject, name=subject_name)
        return subject

    def ingest_grades_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        period: str = DEFAULT_PERIOD,
        uploaded_file_id: UUID | None = None,
    ) -> ImportResult:
        """
        Ingest a grades XLSX file.
        """
        batch_id = str(uuid.uuid4())
        result = ImportResult(batch_id=batch_id, file_type="grades")

        try:
            df = _read_file(file_content, content_type)
        except Exception as e:
            result.errors.append(f"Failed to read file: {str(e)}")
            return result

        try:
            df_long = load_grades_dataframe(df)
        except Exception as e:
            result.errors.append(f"Failed to parse grades file: {str(e)}")
            return result

        if df_long.empty:
            result.errors.append("No valid grade data found in file")
            return result

        classes_created: set[str] = set()
        students_processed: set[str] = set()
        teachers_cache: dict[str, Teacher] = {}
        subjects_cache: dict[str, Subject] = {}
        grades_imported = 0

        for idx, row in df_long.iterrows():
            try:
                student_tz = clean_student_tz(row.get("student_tz", ""))
                if not student_tz:
                    continue

                student_name = str(row.get("student_name", "")).strip()
                class_name = str(row.get("class_name", "")).strip()
                grade_level = str(row.get("grade_level", "")).strip()
                subject = str(row.get("subject", "")).strip()
                teacher_name = row.get("teacher_name")
                grade_value = row.get("grade")

                if class_name.lower() == "nan" or grade_level.lower() == "nan" or student_name.lower() == "nan" or subject.lower() == "nan":
                    result.errors.append(f"Row {idx + 2}: Missing required metadata (name/class/grade/subject is NaN)")
                    result.rows_failed += 1
                    continue

                print(student_name, class_name, grade_level, subject, teacher_name, grade_value)

                if not student_name or not class_name or not subject:
                    result.errors.append(f"Row {idx + 2}: Missing required metadata (name/class/subject is empty)")
                    result.rows_failed += 1
                    continue

                if class_name not in classes_created:
                    c_num_str = row.get("class_num")
                    try:
                        c_num = int(c_num_str) if pd.notna(c_num_str) and str(c_num_str).lower() != "nan" else None
                    except (ValueError, TypeError):
                        c_num = None
                    self.get_or_create_class(class_name, grade_level, c_num)
                    classes_created.add(class_name)
                    result.classes_created += 1

                if student_tz not in students_processed:
                    _, created = self.get_or_create_student(student_tz, student_name, class_name)
                    if created:
                        result.students_created += 1
                    students_processed.add(student_tz)

                teacher_id = None
                clean_teacher = teacher_name if pd.notna(teacher_name) else None
                if clean_teacher:
                    if clean_teacher not in teachers_cache:
                        teachers_cache[clean_teacher] = self.get_or_create_teacher(clean_teacher)
                    teacher_id = teachers_cache[clean_teacher].id

                if subject not in subjects_cache:
                    subjects_cache[subject] = self.get_or_create_subject(subject)
                subject_id = subjects_cache[subject].id

                grade_record = Grade(
                    student_tz=student_tz,
                    subject_name=subject,
                    subject_id=subject_id,
                    teacher_name=clean_teacher,
                    teacher_id=teacher_id,
                    grade=float(grade_value),
                    period=period,
                )
                self.session.add(grade_record)
                grades_imported += 1

            except Exception as e:
                result.errors.append(f"Row error: {str(e)}")
                result.rows_failed += 1

        result.rows_imported = grades_imported

        import_log = ImportLog(
            batch_id=batch_id,
            filename=filename,
            file_type="grades",
            rows_imported=result.rows_imported,
            rows_failed=result.rows_failed,
            errors=json.dumps(result.errors[:MAX_STORED_ERRORS]) if result.errors else None,
            period=period,
            uploaded_file_id=uploaded_file_id,
        )
        self.session.add(import_log)
        self.session.commit()

        return result

    def ingest_events_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        period: str = DEFAULT_PERIOD,
        uploaded_file_id: UUID | None = None,
    ) -> ImportResult:
        """
        Ingest an events/attendance XLSX file.
        """
        batch_id = str(uuid.uuid4())
        result = ImportResult(batch_id=batch_id, file_type="events")

        try:
            df = _read_file(file_content, content_type)
        except Exception as e:
            result.errors.append(f"Failed to read file: {str(e)}")
            return result

        try:
            df = load_attendance_dataframe(df)
        except Exception as e:
            result.errors.append(f"Failed to parse attendance file: {str(e)}")
            return result

        classes_created: set[str] = set()

        for idx, row in df.iterrows():
            try:
                student_tz = clean_student_tz(row.get("student_tz", ""))
                if not student_tz:
                    result.errors.append(f"Row {idx + 2}: Missing student TZ")
                    result.rows_failed += 1
                    continue

                student_name = str(row.get("student_name", "")).strip()
                grade_level = str(row.get("grade_level", "")).strip()
                class_name = str(row.get("class_name", "")).strip()

                if not student_name:
                    result.errors.append(f"Row {idx + 2}: Missing student name")
                    result.rows_failed += 1
                    continue

                if not class_name:
                    result.errors.append(f"Row {idx + 2}: Missing class name")
                    result.rows_failed += 1
                    continue

                if class_name not in classes_created:
                    c_num_str = row.get("class_num")
                    try:
                        c_num = int(c_num_str) if pd.notna(c_num_str) and str(c_num_str).lower() != "nan" else None
                    except (ValueError, TypeError):
                        c_num = None
                    self.get_or_create_class(class_name, grade_level, c_num)
                    classes_created.add(class_name)
                    result.classes_created += 1

                _, created = self.get_or_create_student(student_tz, student_name, class_name)
                if created:
                    result.students_created += 1

                attendance_record = AttendanceRecord(
                    student_tz=student_tz,
                    lessons_reported=int(row.get("lessons_reported", 0)),
                    absence=int(row.get("absence", 0)),
                    absence_justified=int(row.get("absence_justified", 0)),
                    late=int(row.get("late", 0)) + int(row.get("late_justified", 0)),
                    disturbance=int(row.get("disturbance", 0)),
                    total_absences=int(row.get("total_absences", 0)),
                    attendance=int(row.get("attendance", 0)),
                    total_negative_events=int(row.get("total_negative_events", 0)),
                    total_positive_events=int(row.get("total_positive_events", 0)),
                    period=period,
                )
                self.session.add(attendance_record)
                result.rows_imported += 1

            except Exception as e:
                result.errors.append(f"Row {idx + 2}: {str(e)}")
                result.rows_failed += 1

        import_log = ImportLog(
            batch_id=batch_id,
            filename=filename,
            file_type="events",
            rows_imported=result.rows_imported,
            rows_failed=result.rows_failed,
            errors=json.dumps(result.errors[:MAX_STORED_ERRORS]) if result.errors else None,
            period=period,
            uploaded_file_id=uploaded_file_id,
        )
        self.session.add(import_log)
        self.session.commit()

        return result

    def ingest_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        file_type: str | None = None,
        period: str = DEFAULT_PERIOD,
        uploaded_file_id: UUID | None = None,
    ) -> ImportResult:
        """
        Ingest an XLSX/CSV file, auto-detecting type if not specified.
        """
        try:
            df = _read_file(file_content, content_type)
        except Exception as e:
            return ImportResult(
                batch_id=str(uuid.uuid4()),
                file_type="unknown",
                errors=[f"Failed to read file: {str(e)}"],
            )

        if file_type is None:
            file_type = detect_file_type(df)

        if file_type == "grades":
            return self.ingest_grades_file(file_content, filename, content_type, period, uploaded_file_id)
        elif file_type == "events":
            return self.ingest_events_file(file_content, filename, content_type, period, uploaded_file_id)
        else:
            return ImportResult(
                batch_id=str(uuid.uuid4()),
                file_type="unknown",
                errors=["Could not detect file type. Expected grades or events file."],
            )
