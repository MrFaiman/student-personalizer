from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlmodel import Session

from ..auth.current_user import CurrentUser
from ..audit.service import log_event
from ..auth.dependencies import require_permission, require_system_admin
from ..auth.permissions import PermissionKey
from ..constants import (
    AT_RISK_GRADE_THRESHOLD,
    DEFAULT_PAGE_SIZE,
    ENABLE_DEBUG,
    EXCELLENT_GRADE_THRESHOLD,
    GOOD_GRADE_THRESHOLD,
    GRADE_RANGE_MAX,
    GRADE_RANGE_MIN,
    MEDIUM_GRADE_THRESHOLD,
    MFA_ENFORCED_ROLES,
    PERFORMANCE_GOOD_THRESHOLD,
    PERFORMANCE_MEDIUM_THRESHOLD,
)
from ..database import get_session
from ..dependencies import get_preview_mode, set_preview_mode

router = APIRouter(prefix="/api/config", tags=["config"])


class PreviewModeToggle(BaseModel):
    enabled: bool


@router.get("")
async def get_config(_user: CurrentUser = Depends(require_permission(PermissionKey.config_read.value))):
    return {
        "at_risk_grade_threshold": AT_RISK_GRADE_THRESHOLD,
        "medium_grade_threshold": MEDIUM_GRADE_THRESHOLD,
        "good_grade_threshold": GOOD_GRADE_THRESHOLD,
        "excellent_grade_threshold": EXCELLENT_GRADE_THRESHOLD,
        "performance_good_threshold": PERFORMANCE_GOOD_THRESHOLD,
        "performance_medium_threshold": PERFORMANCE_MEDIUM_THRESHOLD,
        "default_page_size": DEFAULT_PAGE_SIZE,
        "grade_range": [GRADE_RANGE_MIN, GRADE_RANGE_MAX],
        "enable_debug": ENABLE_DEBUG,
        "mfa_enforced_roles": sorted(MFA_ENFORCED_ROLES),
        "preview_mode": get_preview_mode(),
    }


@router.get("/preview-mode")
async def get_preview_mode_status(_user: CurrentUser = Depends(require_permission(PermissionKey.config_read.value))):
    return {"preview_mode": get_preview_mode()}


@router.post("/preview-mode", dependencies=[Depends(require_system_admin)])
async def toggle_preview_mode(
    body: PreviewModeToggle,
    request: Request,
    _admin: CurrentUser = Depends(require_system_admin),
    _perm: CurrentUser = Depends(require_permission(PermissionKey.config_write.value)),
    session: Session = Depends(get_session),
):
    set_preview_mode(body.enabled)
    log_event(
        session,
        action="config_change",
        user_id=_admin.user_id,
        user_email=_admin.email,
        success=True,
        detail={"key": "preview_mode", "value": body.enabled, "path": request.url.path},
    )
    return {"preview_mode": get_preview_mode()}
