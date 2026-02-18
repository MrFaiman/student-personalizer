import os
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import func, select

from ..auth import get_current_user
from ..constants import DEFAULT_PAGE_SIZE, DEFAULT_PERIOD, MAX_ERRORS_IN_RESPONSE, MAX_PAGE_SIZE, VALID_MIME_TYPES
from ..dependencies import get_ingestion_service
from ..models import ImportLog, User
from ..schemas.ingestion import ImportLogListResponse, ImportLogResponse, ImportResponse
from ..services.ingestion import ImportResult, IngestionService

ALLOW_RESET = os.getenv("ALLOW_DB_RESET", "false").lower() in ("1", "true", "yes")

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])


@router.post("/reset")
async def reset_database(
    user: User = Depends(get_current_user),
    service: IngestionService = Depends(get_ingestion_service),
):
    """
    Reset all data for the requesting user's school.

    Requires admin role and ALLOW_DB_RESET=true environment variable.
    """
    if not ALLOW_RESET:
        raise HTTPException(status_code=403, detail="Database reset is disabled. Set ALLOW_DB_RESET=true to enable.")

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can reset school data.")

    counts = service.reset_school_data()

    return {
        "message": "School data reset successfully",
        "records_deleted": counts,
    }


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
    service: IngestionService = Depends(get_ingestion_service),
):
    """Upload and ingest an Excel or CSV file."""
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

    result: ImportResult = service.ingest_file(
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
    service: IngestionService = Depends(get_ingestion_service),
):
    """Get a paginated list of import logs."""
    total = service.session.exec(
        select(func.count(ImportLog.id)).where(ImportLog.school_id == service.school_id)
    ).one()

    offset = (page - 1) * page_size
    statement = (
        select(ImportLog)
        .where(ImportLog.school_id == service.school_id)
        .order_by(ImportLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = service.session.exec(statement).all()

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
    service: IngestionService = Depends(get_ingestion_service),
):
    """Get details of a specific import by batch ID."""
    statement = select(ImportLog).where(
        ImportLog.batch_id == batch_id,
        ImportLog.school_id == service.school_id,
    )
    log = service.session.exec(statement).first()

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
    service: IngestionService = Depends(get_ingestion_service),
):
    """Delete an import log and all associated data for this school."""
    from sqlmodel import delete

    statement = select(ImportLog).where(
        ImportLog.batch_id == batch_id,
        ImportLog.school_id == service.school_id,
    )
    log = service.session.exec(statement).first()

    if not log:
        raise HTTPException(status_code=404, detail="Import log not found")

    deleted_records = 0
    from ..models import AttendanceRecord, Grade

    if log.file_type == "grades":
        statement = delete(Grade).where(
            Grade.period == log.period,
            Grade.school_id == service.school_id,
        )
        result = service.session.exec(statement)
        deleted_records = result.rowcount
    elif log.file_type == "events":
        statement = delete(AttendanceRecord).where(
            AttendanceRecord.period == log.period,
            AttendanceRecord.school_id == service.school_id,
        )
        result = service.session.exec(statement)
        deleted_records = result.rowcount

    service.session.delete(log)
    service.session.commit()

    return {
        "message": "Import log deleted successfully",
        "batch_id": batch_id,
        "records_deleted": deleted_records,
    }
