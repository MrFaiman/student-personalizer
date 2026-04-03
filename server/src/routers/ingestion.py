import hashlib
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, func, select

from ..audit.service import log_event
from ..auth.current_user import CurrentUser
from ..auth.dependencies import get_current_user, require_permission, require_school_scope
from ..auth.permissions import PermissionKey
from ..constants import DEFAULT_PAGE_SIZE, DEFAULT_PERIOD, DEFAULT_YEAR, MAX_ERRORS_IN_RESPONSE, MAX_PAGE_SIZE, UPLOAD_DIR
from ..database import get_session
from ..dependencies import require_write_access
from ..integrations.virustotal import scan_file
from ..models import AttendanceRecord, Grade, ImportLog, UploadedFile
from ..schemas.ingestion import ImportLogListResponse, ImportLogResponse, ImportResponse
from ..services.ingestion import ImportResult, IngestionService
from ..utils.file_validation import sanitize_filename, validate_upload

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])

_upload_path = Path(UPLOAD_DIR)
_upload_path.mkdir(parents=True, exist_ok=True)


@router.post(
    "/upload",
    response_model=ImportResponse,
    dependencies=[
        Depends(require_write_access),
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.ingestion_upload.value)),
    ],
)
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
    year: str = Query(
        default=DEFAULT_YEAR,
        description="Academic year to associate with this import (e.g., '2024-2025').",
    ),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Upload and ingest an Excel or CSV file.

    The file type can be auto-detected based on column headers, or you can
    explicitly specify it using the file_type parameter.

    - **grades**: Files with student grades (avg_grades.xlsx/csv format)
    - **events**: Files with attendance/behavior events (events.xlsx/csv format)
    """
    content = await validate_upload(file)
    if file.filename:
        file.filename = sanitize_filename(file.filename)
    content_type = file.content_type or ""

    # Check for duplicate upload (before external scanning to reduce API usage).
    checksum = hashlib.sha256(content).hexdigest()
    existing = session.exec(
        select(UploadedFile).where(UploadedFile.checksum == checksum)
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"This file has already been uploaded as '{existing.original_filename}' on {existing.uploaded_at.isoformat()}",
        )

    # Optional VirusTotal scan gate (fail-open on VT outage/timeout).
    vt_detail: dict | None = None
    try:
        vt = await scan_file(content, filename=file.filename or "upload")
        vt_detail = {"verdict": vt.verdict, "analysis_id": vt.analysis_id, "stats": vt.stats, "reason": vt.reason}
        if vt.should_block:
            log_event(
                session,
                action="upload",
                user_id=current_user.user_id,
                user_email=current_user.email,
                success=False,
                detail={"school_id": current_user.school_id, "filename": file.filename, "reason": "virustotal_block", "vt": vt_detail},
            )
            raise HTTPException(status_code=400, detail="File failed malware scan")
    except HTTPException:
        raise
    except Exception as exc:
        vt_detail = {"verdict": "skipped", "reason": f"virustotal_error:{type(exc).__name__}"}

    # Save the uploaded file to disk and create a tracking record
    uploaded = UploadedFile(
        original_filename=file.filename or "upload",
        stored_path="",  # set after we know the id
        content_type=content_type,
        file_size=len(content),
        checksum=checksum,
        school_id=None,
    )
    suffix = Path(uploaded.original_filename).suffix
    stored_name = f"{uploaded.id}{suffix}"
    uploaded.stored_path = stored_name

    dest = _upload_path / stored_name
    dest.write_bytes(content)

    session.add(uploaded)
    session.flush()

    # Persist school scope on the uploaded file record as well (helps scoping logs later).
    # Strict tenant isolation: resolved scope is always the active school from JWT.
    resolved_school_id = current_user.school_id
    uploaded.school_id = resolved_school_id
    session.add(uploaded)
    session.flush()

    ingestion_service = IngestionService(session)

    # Resolve school scope for import (active school only).
    resolved_school_id = current_user.school_id

    result: ImportResult = ingestion_service.ingest_file(
        file_content=content,
        filename=file.filename or "upload",
        content_type=content_type,
        file_type=file_type,
        period=period,
        year=year,
        school_id=resolved_school_id,
        uploaded_file_id=uploaded.id,
    )

    if result.file_type == "unknown":
        log_event(
            session,
            action="upload",
            user_id=current_user.user_id,
            user_email=current_user.email,
            success=False,
            detail={"school_id": resolved_school_id, "filename": file.filename, "reason": "unknown file type", "vt": vt_detail},
        )
        raise HTTPException(
            status_code=400,
            detail=result.errors[0] if result.errors else "Could not process file",
        )

    log_event(
        session,
        action="upload",
        user_id=current_user.user_id,
        user_email=current_user.email,
        success=True,
        detail={
            "school_id": resolved_school_id,
            "filename": file.filename,
            "file_type": result.file_type,
            "batch_id": result.batch_id,
            "vt": vt_detail,
        },
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


@router.get(
    "/logs",
    response_model=ImportLogListResponse,
    dependencies=[
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.ingestion_logs_read.value)),
    ],
)
async def get_import_logs(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    sort_by: str | None = Query(default=None, description="Column to sort by: filename, file_type, year, period, rows_imported, created_at"),
    sort_order: str = Query(default="desc", description="Sort direction: asc or desc"),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a paginated list of import logs."""
    total = session.exec(select(func.count(ImportLog.id)).where(ImportLog.school_id == current_user.school_id)).one()

    sort_columns = {
        "filename": ImportLog.filename,
        "file_type": ImportLog.file_type,
        "year": ImportLog.year,
        "period": ImportLog.period,
        "rows_imported": ImportLog.rows_imported,
        "created_at": ImportLog.created_at,
    }
    sort_col = sort_columns.get(sort_by, ImportLog.created_at)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()

    offset = (page - 1) * page_size
    statement = (
        select(ImportLog)
        .where(ImportLog.school_id == current_user.school_id)
        .order_by(order)
        .offset(offset)
        .limit(page_size)
    )
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
                year=log.year or None,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/logs/{batch_id}",
    response_model=ImportLogResponse,
    dependencies=[
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.ingestion_logs_read.value)),
    ],
)
async def get_import_log(
    batch_id: str,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get details of a specific import by batch ID."""
    statement = select(ImportLog).where(ImportLog.batch_id == batch_id)
    log = session.exec(statement).first()

    if not log:
        raise HTTPException(status_code=404, detail="Import log not found")
    if log.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Not allowed for this school")

    return ImportLogResponse(
        id=log.id,
        batch_id=log.batch_id,
        filename=log.filename,
        file_type=log.file_type,
        rows_imported=log.rows_imported,
        rows_failed=log.rows_failed,
        period=log.period,
        year=log.year or None,
        created_at=log.created_at.isoformat(),
    )


@router.delete(
    "/logs/{batch_id}",
    dependencies=[
        Depends(require_write_access),
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.ingestion_delete.value)),
    ],
)
async def delete_import_log(
    batch_id: str,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
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

    # Tenant isolation: only allow deleting within active school scope.
    if current_user.school_id is None or log.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Not allowed for this school")

    # Capture the uploaded file record before deleting the log
    uploaded_file = log.uploaded_file

    deleted_records = 0
    year_value = log.year if log.year else ""
    if log.file_type == "grades":
        statement = delete(Grade).where(Grade.period == log.period).where(Grade.year == year_value)
        result = session.exec(statement)
        deleted_records = result.rowcount
    elif log.file_type == "events":
        statement = delete(AttendanceRecord).where(AttendanceRecord.period == log.period).where(AttendanceRecord.year == year_value)
        result = session.exec(statement)
        deleted_records = result.rowcount

    session.delete(log)

    if uploaded_file:
        physical_path = _upload_path / uploaded_file.stored_path
        if physical_path.is_file():
            physical_path.unlink()
        session.delete(uploaded_file)

    session.commit()

    log_event(
        session,
        action="delete_import",
        user_id=current_user.user_id,
        user_email=current_user.email,
        success=True,
        detail={"school_id": current_user.school_id, "batch_id": batch_id, "records_deleted": deleted_records},
    )
    return {
        "message": "Import log deleted successfully",
        "batch_id": batch_id,
        "records_deleted": deleted_records,
    }
