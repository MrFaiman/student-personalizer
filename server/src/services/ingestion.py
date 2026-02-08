import json
import re
import uuid
from io import BytesIO
from dataclasses import dataclass, field

import pandas as pd
from sqlmodel import Session, select

from ..models import Class, Student, Grade, AttendanceRecord, ImportLog


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

    # Check for grades-specific columns
    if "ממוצע" in columns or "ת.ז" in columns:
        return "grades"

    # Check for events-specific columns
    if "שיעורים שדווחו" in columns or "חיסור" in columns or "ת.ז. התלמיד" in columns:
        return "events"

    return None


def clean_student_tz(value) -> str:
    """Clean and normalize student TZ (ID)."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def get_or_create_class(session: Session, class_name: str, grade_level: str) -> Class:
    """Get existing class or create new one."""
    statement = select(Class).where(Class.class_name == class_name)
    cls = session.exec(statement).first()

    if cls:
        return cls

    cls = Class(class_name=class_name, grade_level=grade_level)
    session.add(cls)
    session.flush()
    return cls


def get_or_create_student(
    session: Session,
    student_tz: str,
    student_name: str,
    class_name: str,
) -> tuple[Student, bool]:
    """Get existing student or create new one. Returns (student, created)."""
    statement = select(Student).where(Student.student_tz == student_tz)
    student = session.exec(statement).first()

    if student:
        if student.student_name != student_name:
            student.student_name = student_name
        if student.class_name != class_name:
            student.class_name = class_name
        session.add(student)
        return student, False

    student = Student(
        student_tz=student_tz,
        student_name=student_name,
        class_name=class_name,
    )
    session.add(student)
    session.flush()
    return student, True


def parse_subject_teacher_header(header_str: str) -> tuple[str, str | None]:
    """
    Parse "Subject - Teacher" format from column header.
    E.g., "אנגלית- ישראל ישראלי" -> ("אנגלית", "ישראל ישראלי")
    """
    # Remove pandas duplicate suffixes like ".1", ".2"
    clean_header = re.sub(r'\.\d+$', '', str(header_str))

    # Split by hyphen (with optional spaces)
    if '-' in clean_header:
        parts = clean_header.split('-', 1)
        subject = parts[0].strip()
        teacher = parts[1].strip() if len(parts) > 1 else None
        return subject, teacher if teacher else None
    else:
        return clean_header.strip(), None


def load_grades_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse a wide-format grades file where columns 6+ represent "Subject - Teacher".
    Transposes (melts) the data into a long format with columns:
    student_tz, student_name, class_name, grade_level, subject, teacher_name, grade
    """
    # Define metadata columns mapping (Hebrew -> English)
    metadata_map = {
        "מס'": "serial_num",
        "ת.ז": "student_tz",
        "שם התלמיד": "student_name",
        "שכבה": "grade_level",
        "כיתה": "class_num",
    }

    # Rename known columns
    df = df.rename(columns=metadata_map)

    # Build full class_name from grade_level + class_num (e.g., "י" + "3" = "י-3")
    df["class_name"] = df.apply(
        lambda row: f"{row['grade_level']}-{int(row['class_num'])}"
        if pd.notna(row.get('class_num')) and pd.notna(row.get('grade_level'))
        else str(row.get('class_num', '')),
        axis=1
    )

    # Generate student_tz if missing (use serial_num)
    def generate_student_tz(row):
        tz = row.get("student_tz")
        if pd.notna(tz) and str(tz).strip():
            return str(tz).strip()
        serial = row.get("serial_num", 0)
        if pd.notna(serial):
            return f"STU-{int(serial):04d}"
        return f"STU-{row.name:04d}"  # Use row index as fallback

    df["student_tz"] = df.apply(generate_student_tz, axis=1)

    # Identify metadata vs grade columns
    metadata_cols = ["serial_num", "student_tz", "student_name", "grade_level", "class_num", "class_name"]
    existing_meta_cols = [c for c in metadata_cols if c in df.columns]

    # Grade columns: everything except metadata and average (ממוצע)
    grade_cols = [
        c for c in df.columns
        if c not in existing_meta_cols and "ממוצע" not in str(c)
    ]

    # Melt from wide to long format
    df_long = df.melt(
        id_vars=existing_meta_cols,
        value_vars=grade_cols,
        var_name="subject_teacher_str",
        value_name="grade",
    )

    # Parse subject and teacher from header string
    parsed_data = [parse_subject_teacher_header(x) for x in df_long["subject_teacher_str"]]
    df_long["subject"] = [x[0] for x in parsed_data]
    df_long["teacher_name"] = [x[1] for x in parsed_data]

    # Convert grades to numeric, coercing errors to NaN
    df_long["grade"] = pd.to_numeric(df_long["grade"], errors="coerce")

    # Drop rows without a valid grade
    df_long = df_long.dropna(subset=["grade"])

    # Select final columns
    final_cols = [
        "student_tz", "student_name", "class_name", "grade_level",
        "subject", "teacher_name", "grade"
    ]
    available_cols = [c for c in final_cols if c in df_long.columns]

    return df_long[available_cols]


def ingest_grades_file(
    session: Session,
    file_content: bytes,
    filename: str,
    period: str = "Default",
) -> ImportResult:
    """
    Ingest a grades XLSX file.

    Expected format: Wide format with columns:
    - מס' (row number)
    - ת.ז (student TZ)
    - שם התלמיד (student name)
    - שכבה (grade level)
    - כיתה (class name)
    - ממוצע (average - ignored)
    - Remaining columns: "Subject - Teacher" format with grade values
    """
    batch_id = str(uuid.uuid4())
    result = ImportResult(batch_id=batch_id, file_type="grades")

    try:
        df = pd.read_excel(BytesIO(file_content), engine="openpyxl")
    except Exception as e:
        result.errors.append(f"Failed to read Excel file: {str(e)}")
        return result

    # Transform to long format with subject/teacher parsing
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

            if not student_name or not class_name or not subject:
                continue

            # Get or create class (once per class)
            if class_name not in classes_created:
                get_or_create_class(session, class_name, grade_level)
                classes_created.add(class_name)
                result.classes_created += 1

            # Get or create student (once per student)
            if student_tz not in students_processed:
                _, created = get_or_create_student(
                    session, student_tz, student_name, class_name
                )
                if created:
                    result.students_created += 1
                students_processed.add(student_tz)

            # Create grade record
            grade_record = Grade(
                student_tz=student_tz,
                subject=subject,
                teacher_name=teacher_name if pd.notna(teacher_name) else None,
                grade=float(grade_value),
                period=period,
            )
            session.add(grade_record)
            grades_imported += 1

        except Exception as e:
            result.errors.append(f"Row error: {str(e)}")
            result.rows_failed += 1

    result.rows_imported = grades_imported

    # Log the import
    import_log = ImportLog(
        batch_id=batch_id,
        filename=filename,
        file_type="grades",
        rows_imported=result.rows_imported,
        rows_failed=result.rows_failed,
        errors=json.dumps(result.errors[:100]) if result.errors else None,
        period=period,
    )
    session.add(import_log)
    session.commit()

    return result


def load_attendance_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse an attendance/events XLSX file.
    Maps Hebrew columns to English and calculates totals.
    """
    # Complete column mapping (Hebrew -> English)
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

    # Apply renaming
    df = df.rename(columns=column_map)

    # Build full class_name from grade_level + class_num (e.g., "י" + "3" = "י-3")
    df["class_name"] = df.apply(
        lambda row: f"{row['grade_level']}-{int(row['class_num'])}"
        if pd.notna(row.get('class_num')) and pd.notna(row.get('grade_level'))
        else str(row.get('class_num', '')),
        axis=1
    )

    # Generate student_tz if missing (use serial_num)
    def generate_student_tz(row):
        tz = row.get("student_tz_orig")
        if pd.notna(tz) and str(tz).strip():
            return str(tz).strip()
        serial = row.get("serial_num", 0)
        if pd.notna(serial):
            return f"STU-{int(serial):04d}"
        return f"STU-{row.name:04d}"  # Use row index as fallback

    df["student_tz"] = df.apply(generate_student_tz, axis=1)

    # Define column lists for logic
    negative_cols = [
        "absence", "absence_justified", "late", "late_justified",
        "disturbance", "skipped_class", "skipped_class_justified",
        "uniform_issue", "no_homework", "no_equipment",
        "no_classwork", "phone_usage", "private_lesson_absence_justified",
    ]

    positive_cols = [
        "positive_reinforcement", "positive_reinforcement_class",
        "private_lesson_presence",
    ]

    # Numeric conversion & cleaning
    all_event_cols = negative_cols + positive_cols + ["lessons_reported"]

    for col in all_event_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            df[col] = 0

    # Business logic calculations
    df["total_absences"] = (
        df["absence"]
        + df["absence_justified"]
        + df["skipped_class"]
        + df["skipped_class_justified"]
    )

    df["total_negative_events"] = df[negative_cols].sum(axis=1)
    df["total_positive_events"] = df[positive_cols].sum(axis=1)

    return df


def ingest_events_file(
    session: Session,
    file_content: bytes,
    filename: str,
    period: str = "Default",
) -> ImportResult:
    """
    Ingest an events/attendance XLSX file.

    Expected columns (Hebrew):
    - מס' (row number)
    - ת.ז. התלמיד (student TZ)
    - שם התלמיד (student name)
    - שכבה (grade level)
    - כיתה (class name)
    - Plus various attendance/behavior columns
    """
    batch_id = str(uuid.uuid4())
    result = ImportResult(batch_id=batch_id, file_type="events")

    try:
        df = pd.read_excel(BytesIO(file_content), engine="openpyxl")
    except Exception as e:
        result.errors.append(f"Failed to read Excel file: {str(e)}")
        return result

    # Transform dataframe with column mapping and calculations
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

            # Get or create class
            if class_name not in classes_created:
                get_or_create_class(session, class_name, grade_level)
                classes_created.add(class_name)
                result.classes_created += 1

            # Get or create student
            _, created = get_or_create_student(
                session, student_tz, student_name, class_name
            )
            if created:
                result.students_created += 1

            # Create attendance record using pre-calculated values
            attendance_record = AttendanceRecord(
                student_tz=student_tz,
                absence=int(row.get("absence", 0)),
                absence_justified=int(row.get("absence_justified", 0)),
                late=int(row.get("late", 0)) + int(row.get("late_justified", 0)),
                disturbance=int(row.get("disturbance", 0)),
                total_absences=int(row.get("total_absences", 0)),
                total_negative_events=int(row.get("total_negative_events", 0)),
                total_positive_events=int(row.get("total_positive_events", 0)),
                period=period,
            )
            session.add(attendance_record)
            result.rows_imported += 1

        except Exception as e:
            result.errors.append(f"Row {idx + 2}: {str(e)}")
            result.rows_failed += 1

    # Log the import
    import_log = ImportLog(
        batch_id=batch_id,
        filename=filename,
        file_type="events",
        rows_imported=result.rows_imported,
        rows_failed=result.rows_failed,
        errors=json.dumps(result.errors[:100]) if result.errors else None,
        period=period,
    )
    session.add(import_log)
    session.commit()

    return result


def ingest_file(
    session: Session,
    file_content: bytes,
    filename: str,
    file_type: str | None = None,
    period: str = "Default",
) -> ImportResult:
    """
    Ingest an XLSX file, auto-detecting type if not specified.

    Args:
        session: Database session
        file_content: Raw file bytes
        filename: Original filename
        file_type: "grades" or "events", or None for auto-detect
        period: Period name to associate with this import

    Returns:
        ImportResult with details of the import
    """
    try:
        df = pd.read_excel(BytesIO(file_content), engine="openpyxl")
    except Exception as e:
        return ImportResult(
            batch_id=str(uuid.uuid4()),
            file_type="unknown",
            errors=[f"Failed to read Excel file: {str(e)}"],
        )

    if file_type is None:
        file_type = detect_file_type(df)

    if file_type == "grades":
        return ingest_grades_file(session, file_content, filename, period)
    elif file_type == "events":
        return ingest_events_file(session, file_content, filename, period)
    else:
        return ImportResult(
            batch_id=str(uuid.uuid4()),
            file_type="unknown",
            errors=["Could not detect file type. Expected grades or events file."],
        )
