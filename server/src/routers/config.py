from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..constants import (
    ADMIN_PASSWORD,
    AT_RISK_GRADE_THRESHOLD,
    DEFAULT_PAGE_SIZE,
    ENABLE_DEBUG,
    EXCELLENT_GRADE_THRESHOLD,
    GOOD_GRADE_THRESHOLD,
    GRADE_RANGE_MAX,
    GRADE_RANGE_MIN,
    MEDIUM_GRADE_THRESHOLD,
    PERFORMANCE_GOOD_THRESHOLD,
    PERFORMANCE_MEDIUM_THRESHOLD,
)
from ..dependencies import get_preview_mode, set_preview_mode

router = APIRouter(prefix="/api/config", tags=["config"])


class PreviewModeToggle(BaseModel):
    password: str
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
        "preview_mode": get_preview_mode(),
    }


@router.get("/preview-mode")
async def get_preview_mode_status():
    return {"preview_mode": get_preview_mode()}


@router.post("/preview-mode")
async def toggle_preview_mode(body: PreviewModeToggle):
    if not ADMIN_PASSWORD or body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin password.")
    set_preview_mode(body.enabled)
    return {"preview_mode": get_preview_mode()}
