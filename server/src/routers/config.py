from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..auth.current_user import CurrentUser
from ..auth.dependencies import require_system_admin
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
from ..dependencies import get_preview_mode, set_preview_mode

router = APIRouter(prefix="/api/config", tags=["config"])


class PreviewModeToggle(BaseModel):
    enabled: bool


@router.get("")
async def get_config():
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
async def get_preview_mode_status():
    return {"preview_mode": get_preview_mode()}


@router.post("/preview-mode", dependencies=[Depends(require_system_admin)])
async def toggle_preview_mode(body: PreviewModeToggle, _admin: CurrentUser = Depends(require_system_admin)):
    set_preview_mode(body.enabled)
    return {"preview_mode": get_preview_mode()}
