from typing import Literal
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import ImportLog
from ..services.ingestion import ingest_file, ImportResult
from ..schemas.ingestion import ImportResponse, ImportLogResponse


router = APIRouter(prefix="/api/ingest", tags=["ingestion"])


@router.post("/upload", response_model=ImportResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_type: Literal["grades", "events"] | None = Query(
        default=None,
        description="File type (grades or events). Auto-detected if not specified.",
    ),
    period: str = Query(
        default="Default",
        description="Period name to associate with this import (e.g., 'Quarter 1', 'סמסטר א').",
    ),
    session: Session = Depends(get_session),
):
    """
    Upload and ingest an XLSX file.

    The file type can be auto-detected based on column headers, or you can
    explicitly specify it using the file_type parameter.

    - **grades**: Files with student grades (avg_grades.xlsx format)
    - **events**: Files with attendance/behavior events (events.xlsx format)
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)",
        )

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    result: ImportResult = ingest_file(
        session=session,
        file_content=content,
        filename=file.filename,
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
        errors=result.errors[:20],  # Limit errors in response
    )


@router.get("/logs", response_model=list[ImportLogResponse])
async def get_import_logs(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    """Get a list of import logs."""
    statement = (
        select(ImportLog)
        .order_by(ImportLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    logs = session.exec(statement).all()

    return [
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
    ]


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
