import hashlib
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, func, select

from ..constants import DEFAULT_PAGE_SIZE, DEFAULT_PERIOD, MAX_ERRORS_IN_RESPONSE, MAX_PAGE_SIZE, UPLOAD_DIR, VALID_MIME_TYPES
from ..database import get_session
from ..models import AttendanceRecord, Grade, ImportLog, UploadedFile
from ..schemas.ingestion import ImportLogListResponse, ImportLogResponse, ImportResponse
from ..services.ingestion import ImportResult, IngestionService

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])

_upload_path = Path(UPLOAD_DIR)
_upload_path.mkdir(parents=True, exist_ok=True)


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

    # Check for duplicate upload
    checksum = hashlib.sha256(content).hexdigest()
    existing = session.exec(
        select(UploadedFile).where(UploadedFile.checksum == checksum)
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"This file has already been uploaded as '{existing.original_filename}' on {existing.uploaded_at.isoformat()}",
        )

    # Save the uploaded file to disk and create a tracking record
    uploaded = UploadedFile(
        original_filename=file.filename or "upload",
        stored_path="",  # set after we know the id
        content_type=content_type,
        file_size=len(content),
        checksum=checksum,
    )
    suffix = Path(uploaded.original_filename).suffix
    stored_name = f"{uploaded.id}{suffix}"
    uploaded.stored_path = stored_name

    dest = _upload_path / stored_name
    dest.write_bytes(content)

    session.add(uploaded)
    session.flush()

    ingestion_service = IngestionService(session)
    result: ImportResult = ingestion_service.ingest_file(
        file_content=content,
        filename=file.filename or "upload",
        content_type=content_type,
        file_type=file_type,
        period=period,
        uploaded_file_id=uploaded.id,
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
    - The physical file from disk and its UploadedFile tracking record

    Note: This does NOT delete students or classes, only the data from this specific import.
    """
    from sqlmodel import delete

    statement = select(ImportLog).where(ImportLog.batch_id == batch_id)
    log = session.exec(statement).first()

    if not log:
        raise HTTPException(status_code=404, detail="Import log not found")

    # Capture the uploaded file record before deleting the log
    uploaded_file = log.uploaded_file

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

    if uploaded_file:
        physical_path = _upload_path / uploaded_file.stored_path
        if physical_path.is_file():
            physical_path.unlink()
        session.delete(uploaded_file)

    session.commit()

    return {
        "message": "Import log deleted successfully",
        "batch_id": batch_id,
        "records_deleted": deleted_records,
    }
