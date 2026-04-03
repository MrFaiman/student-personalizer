from collections import Counter

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, func, select

from ..audit.service import log_event
from ..auth.current_user import CurrentUser
from ..auth.dependencies import get_current_user, require_permission, require_school_scope
from ..auth.permissions import PermissionKey
from ..constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, VALID_MIME_TYPES
from ..database import get_session
from ..dependencies import require_write_access
from ..integrations.virustotal import scan_file
from ..models import OpenDayImport, OpenDayRegistration
from ..schemas.open_day import (
    OpenDayImportItem,
    OpenDayImportListResponse,
    OpenDayRegistrationItem,
    OpenDayRegistrationListResponse,
    OpenDayStats,
    OpenDayUploadResponse,
)
from ..services.open_day import OpenDayService
from ..utils.file_validation import sanitize_filename, validate_upload

router = APIRouter(prefix="/api/open-day", tags=["open-day"])


@router.post(
    "/upload",
    response_model=OpenDayUploadResponse,
    dependencies=[
        Depends(require_write_access),
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.ingestion_upload.value)),
    ],
)
async def upload_open_day_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Upload a CSV or Excel open-day registration file."""
    if file.filename:
        file.filename = sanitize_filename(file.filename)

    mime = (file.content_type or "").lower().split(";")[0].strip()
    mime_format = VALID_MIME_TYPES.get(mime)
    if not mime_format and mime == "application/octet-stream":
        # Some browsers/clients send octet-stream; infer from filename extension.
        name = (file.filename or "").lower()
        if name.endswith(".csv"):
            mime_format = "csv"
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            mime_format = "excel"

    if not mime_format:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel (.xlsx) or CSV (.csv) file.",
        )

    content = await validate_upload(file)

    try:
        # Optional VirusTotal scan gate (fail-open on VT outage/timeout).
        vt_detail: dict | None = None
        try:
            vt = await scan_file(content, filename=file.filename or "upload")
            vt_detail = {"verdict": vt.verdict, "analysis_id": vt.analysis_id, "stats": vt.stats, "reason": vt.reason}
            if vt.should_block:
                log_event(
                    session,
                    action="open_day_upload",
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

        service = OpenDayService(session)
        result = service.process_upload(mime_format, content, file.filename or "upload", school_id=current_user.school_id)
        log_event(
            session,
            action="open_day_upload",
            user_id=current_user.user_id,
            user_email=current_user.email,
            success=True,
            detail={"school_id": current_user.school_id, "filename": file.filename, "content_type": mime, "vt": vt_detail},
        )
        return result
    except Exception as exc:
        log_event(
            session,
            action="open_day_upload",
            user_id=current_user.user_id,
            user_email=current_user.email,
            success=False,
            detail={"school_id": current_user.school_id, "filename": file.filename, "error": str(exc)},
        )
        raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}")


@router.get(
    "/registrations",
    response_model=OpenDayRegistrationListResponse,
    dependencies=[
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.ingestion_logs_read.value)),
    ],
)
async def list_registrations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    search: str | None = Query(default=None),
    track: str | None = Query(default=None),
    grade: str | None = Query(default=None),
    import_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List open day registrations with optional search and filters."""
    query = select(OpenDayRegistration).where(OpenDayRegistration.school_id == current_user.school_id)

    if search:
        term = f"%{search}%"
        query = query.where(
            (OpenDayRegistration.first_name.ilike(term))  # type: ignore[union-attr]
            | (OpenDayRegistration.last_name.ilike(term))
            | (OpenDayRegistration.student_id.ilike(term))
        )
    if track:
        query = query.where(OpenDayRegistration.interested_track == track)
    if grade:
        query = query.where(OpenDayRegistration.next_grade == grade)
    if import_id:
        query = query.where(OpenDayRegistration.import_id == import_id)

    total = session.exec(select(func.count()).select_from(query.subquery())).one()

    items = session.exec(
        query.order_by(OpenDayRegistration.last_name, OpenDayRegistration.first_name).offset((page - 1) * page_size).limit(page_size)
    ).all()

    return OpenDayRegistrationListResponse(
        items=[
            OpenDayRegistrationItem(
                id=r.id,  # type: ignore[arg-type]
                import_id=r.import_id,
                submitted_at=r.submitted_at,
                first_name=r.first_name,
                last_name=r.last_name,
                student_id=r.student_id,
                parent_name=r.parent_name,
                phone=r.phone,
                email=r.email,
                current_school=r.current_school,
                next_grade=r.next_grade,
                interested_track=r.interested_track,
                referral_source=r.referral_source,
                additional_notes=r.additional_notes,
                import_date=r.import_date,
            )
            for r in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/stats",
    response_model=OpenDayStats,
    dependencies=[
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.ingestion_logs_read.value)),
    ],
)
async def get_stats(
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return aggregate stats for open day registrations."""
    from collections import defaultdict

    rows = session.exec(
        select(
            OpenDayRegistration.interested_track,
            OpenDayRegistration.next_grade,
            OpenDayRegistration.referral_source,
            OpenDayRegistration.current_school,
            OpenDayRegistration.submitted_at,
        )
        .where(OpenDayRegistration.school_id == current_user.school_id)
    ).all()

    by_track: Counter = Counter()
    by_grade: Counter = Counter()
    by_referral: Counter = Counter()
    by_school: Counter = Counter()
    by_date: Counter = Counter()
    track_by_grade: dict[str, Counter] = defaultdict(Counter)

    for track, grade, referral, school, submitted_at in rows:
        if track:
            by_track[track] += 1
        if grade:
            by_grade[grade] += 1
        if referral:
            by_referral[referral] += 1
        if school:
            by_school[school] += 1
        if submitted_at:
            by_date[submitted_at.date().isoformat()] += 1
        if grade and track:
            track_by_grade[grade][track] += 1

    return OpenDayStats(
        total=len(rows),
        by_track=dict(by_track.most_common()),
        by_grade=dict(by_grade.most_common()),
        by_referral=dict(by_referral.most_common()),
        by_school=dict(by_school.most_common(10)),
        by_date=dict(sorted(by_date.items())),
        track_by_grade={grade: dict(tracks) for grade, tracks in track_by_grade.items()},
    )


@router.get(
    "/imports",
    response_model=OpenDayImportListResponse,
    dependencies=[
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.ingestion_logs_read.value)),
    ],
)
async def list_imports(
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all open day file imports (upload history)."""
    imports = session.exec(
        select(OpenDayImport)
        .where(OpenDayImport.school_id == current_user.school_id)
        .order_by(OpenDayImport.import_date.desc())  # type: ignore[union-attr]
    ).all()
    total = len(imports)
    return OpenDayImportListResponse(
        items=[
            OpenDayImportItem(
                id=imp.id,  # type: ignore[arg-type]
                batch_id=imp.batch_id,
                filename=imp.filename,
                rows_imported=imp.rows_imported,
                rows_failed=imp.rows_failed,
                import_date=imp.import_date,
            )
            for imp in imports
        ],
        total=total,
    )


@router.delete(
    "/reset",
    dependencies=[
        Depends(require_write_access),
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.ingestion_delete.value)),
    ],
)
async def reset_all(
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Delete all open day registrations and imports."""
    from sqlmodel import delete

    session.exec(delete(OpenDayRegistration).where(OpenDayRegistration.school_id == current_user.school_id))  # type: ignore[arg-type]
    session.exec(delete(OpenDayImport).where(OpenDayImport.school_id == current_user.school_id))  # type: ignore[arg-type]
    session.commit()
    log_event(
        session,
        action="open_day_reset",
        user_id=current_user.user_id,
        user_email=current_user.email,
        success=True,
        detail={"school_id": current_user.school_id},
    )
    return {"message": "All open day data deleted"}


@router.delete(
    "/imports/{import_id}",
    dependencies=[
        Depends(require_write_access),
        Depends(require_school_scope),
        Depends(require_permission(PermissionKey.ingestion_delete.value)),
    ],
)
async def delete_import(
    import_id: int,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Delete an import and all its registrations."""
    from sqlmodel import delete

    imp = session.get(OpenDayImport, import_id)
    if not imp:
        raise HTTPException(status_code=404, detail="Import not found.")
    if imp.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Not allowed for this school")

    session.exec(delete(OpenDayRegistration).where(OpenDayRegistration.import_id == import_id))  # type: ignore[arg-type]
    session.delete(imp)
    session.commit()
    log_event(
        session,
        action="open_day_delete_import",
        user_id=current_user.user_id,
        user_email=current_user.email,
        success=True,
        detail={"school_id": current_user.school_id, "import_id": import_id, "batch_id": imp.batch_id},
    )

    return {"message": "Deleted successfully", "import_id": import_id}
