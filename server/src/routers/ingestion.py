import os
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, func, select

from ..constants import DEFAULT_PAGE_SIZE, DEFAULT_PERIOD, MAX_ERRORS_IN_RESPONSE, MAX_PAGE_SIZE, VALID_MIME_TYPES
from ..database import get_session, get_session_context, reset_db
from ..models import AttendanceRecord, Class, Grade, ImportLog, Student
from ..schemas.ingestion import ImportLogListResponse, ImportLogResponse, ImportResponse
from ..services.ingestion import ImportResult, ingest_file

ALLOW_RESET = os.getenv("ALLOW_DB_RESET", "false").lower() in ("1", "true", "yes")

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


@router.post("/reset")
async def reset_database(
    reload_data: bool = Query(
        default=True,
        description="Whether to reload data from CSV files after reset",
    ),
):
    """
    Reset the database by dropping all tables and recreating them.

    Optionally reloads data from CSV files in the data directory.
    Requires ALLOW_DB_RESET=true environment variable.
    """
    if not ALLOW_RESET:
        raise HTTPException(status_code=403, detail="Database reset is disabled. Set ALLOW_DB_RESET=true to enable.")

    reset_db()

    result = {
        "message": "Database reset successfully",
        "tables_cleared": ["class", "student", "grade", "attendancerecord", "importlog"],
        "data_reloaded": False,
        "students_loaded": 0,
        "events_loaded": 0,
    }

    if reload_data:
        with get_session_context() as new_session:
            grades_file = DATA_DIR / "avg_grades.csv"
            if grades_file.exists():
                students_loaded = _load_grades_csv(new_session, grades_file)
                result["students_loaded"] = students_loaded

            events_file = DATA_DIR / "events.csv"
            if events_file.exists():
                events_loaded = _load_events_csv(new_session, events_file)
                result["events_loaded"] = events_loaded

            result["data_reloaded"] = True

    return result


def _load_grades_csv(session: Session, file_path: Path) -> int:
    """Load grades from CSV file."""
    df = pd.read_csv(file_path, encoding="utf-8")

    df = df[df["מס'"].notna() & (df["מס'"] != "")]

    students_created = 0

    for _, row in df.iterrows():
        tz = str(row.get("ת.ז", "")).strip()
        name = str(row.get("שם התלמיד", "")).strip()
        grade_level = str(row.get("שכבה", "")).strip()
        class_num = str(row.get("כיתה", "")).strip()

        if not tz or not name:
            continue

        class_name = f"{grade_level}{class_num}"

        existing_class = session.exec(select(Class).where(Class.class_name == class_name)).first()
        if not existing_class:
            new_class = Class(class_name=class_name, grade_level=grade_level)
            session.add(new_class)
            session.flush()
            existing_class = new_class

        existing_student = session.get(Student, tz)
        if not existing_student:
            student = Student(student_tz=tz, student_name=name, class_id=existing_class.id)
            session.add(student)
            students_created += 1

        avg_col = "ממוצע"
        if avg_col in df.columns:
            avg_value = row[avg_col]
            if pd.notna(avg_value) and avg_value != "":
                try:
                    grade_value = float(avg_value)
                    grade = Grade(
                        student_tz=tz,
                        subject="ממוצע כללי",
                        grade=grade_value,
                        period=DEFAULT_PERIOD,
                    )
                    session.add(grade)
                except (ValueError, TypeError):
                    pass

    session.commit()
    return students_created


def _safe_int(val, default=0):
    """Convert value to int, handling NaN and empty values."""
    if pd.isna(val) or val == "":
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _load_events_csv(session: Session, file_path: Path) -> int:
    """Load attendance events from CSV file."""
    df = pd.read_csv(file_path, encoding="utf-8")

    df = df[df["מס'"].notna() & (df["מס'"] != "")]

    events_created = 0

    for _, row in df.iterrows():
        tz = str(row.get("ת.ז. התלמיד", "")).strip()

        if not tz:
            continue

        student = session.get(Student, tz)
        if not student:
            continue

        lessons_reported = _safe_int(row.get("שיעורים שדווחו", 0))
        absence = _safe_int(row.get("חיסור", 0))
        absence_justified = _safe_int(row.get("חיסור (מוצדק)", 0))
        late = _safe_int(row.get("איחור", 0))
        disturbance = _safe_int(row.get("הפרעה", 0))
        positive = _safe_int(row.get("חיזוק חיובי", 0))
        record = AttendanceRecord(
            student_tz=tz,
            lessons_reported=lessons_reported,
            absence=absence,
            absence_justified=absence_justified,
            late=late,
            disturbance=disturbance,
            total_absences=absence,
            attendance=lessons_reported - absence,
            total_negative_events=absence + late + disturbance,
            total_positive_events=positive,
            period=DEFAULT_PERIOD,
        )
        session.add(record)
        events_created += 1

    session.commit()
    return events_created


@router.post("/upload", response_model=ImportResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_type: Literal["grades", "events"] | None = Query(
        default=None,
        description="File type (grades or events). Auto-detected if not specified.",
    ),
    period: str = Query(
        default=DEFAULT_PERIOD,
        description="Period name to associate with this import (e.g., 'Quarter 1', 'סמסטר א').",
    ),
    session: Session = Depends(get_session),
):
    """
    Upload and ingest an Excel or CSV file.

    The file type can be auto-detected based on column headers, or you can
    explicitly specify it using the file_type parameter.

    - **grades**: Files with student grades (avg_grades.xlsx/csv format)
    - **events**: Files with attendance/behavior events (events.xlsx/csv format)
    """
    content_type = file.content_type or ""
    mime_format = VALID_MIME_TYPES.get(content_type)
    if not mime_format:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{content_type}'. Please upload an Excel (.xlsx, .xls) or CSV (.csv) file",
        )

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    result: ImportResult = ingest_file(
        session=session,
        file_content=content,
        filename=file.filename or "upload",
        content_type=content_type,
        file_type=file_type,
        period=period,
    )

    if result.file_type == "unknown":
        raise HTTPException(
            status_code=400,
            detail=result.errors[0] if result.errors else "Could not process file",
        )

    return ImportResponse(
        batch_id=result.batch_id,
        file_type=result.file_type,
        rows_imported=result.rows_imported,
        rows_failed=result.rows_failed,
        students_created=result.students_created,
        classes_created=result.classes_created,
        errors=result.errors[:MAX_ERRORS_IN_RESPONSE],
    )


@router.get("/logs", response_model=ImportLogListResponse)
async def get_import_logs(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    session: Session = Depends(get_session),
):
    """Get a paginated list of import logs."""
    total = session.exec(select(func.count(ImportLog.id))).one()

    offset = (page - 1) * page_size
    statement = select(ImportLog).order_by(ImportLog.created_at.desc()).offset(offset).limit(page_size)
    logs = session.exec(statement).all()

    return ImportLogListResponse(
        items=[
            ImportLogResponse(
                id=log.id,
                batch_id=log.batch_id,
                filename=log.filename,
                file_type=log.file_type,
                rows_imported=log.rows_imported,
                rows_failed=log.rows_failed,
                period=log.period,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/logs/{batch_id}", response_model=ImportLogResponse)
async def get_import_log(
    batch_id: str,
    session: Session = Depends(get_session),
):
    """Get details of a specific import by batch ID."""
    statement = select(ImportLog).where(ImportLog.batch_id == batch_id)
    log = session.exec(statement).first()

    if not log:
        raise HTTPException(status_code=404, detail="Import log not found")

    return ImportLogResponse(
        id=log.id,
        batch_id=log.batch_id,
        filename=log.filename,
        file_type=log.file_type,
        rows_imported=log.rows_imported,
        rows_failed=log.rows_failed,
        period=log.period,
        created_at=log.created_at.isoformat(),
    )


@router.delete("/logs/{batch_id}")
async def delete_import_log(
    batch_id: str,
    session: Session = Depends(get_session),
):
    """
    Delete an import log and all associated data.

    This will remove:
    - The import log entry
    - All grades/attendance records imported in this batch (identified by period and file type)

    Note: This does NOT delete students or classes, only the data from this specific import.
    """
    from sqlmodel import delete

    statement = select(ImportLog).where(ImportLog.batch_id == batch_id)
    log = session.exec(statement).first()

    if not log:
        raise HTTPException(status_code=404, detail="Import log not found")

    deleted_records = 0
    if log.file_type == "grades":
        statement = delete(Grade).where(Grade.period == log.period)
        result = session.exec(statement)
        deleted_records = result.rowcount
    elif log.file_type == "events":
        statement = delete(AttendanceRecord).where(AttendanceRecord.period == log.period)
        result = session.exec(statement)
        deleted_records = result.rowcount

    session.delete(log)
    session.commit()

    return {
        "message": "Import log deleted successfully",
        "batch_id": batch_id,
        "records_deleted": deleted_records,
    }
