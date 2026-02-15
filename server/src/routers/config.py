from fastapi import APIRouter

from ..constants import (
    AT_RISK_GRADE_THRESHOLD,
    DEFAULT_PAGE_SIZE,
    EXCELLENT_GRADE_THRESHOLD,
    GOOD_GRADE_THRESHOLD,
    GRADE_RANGE_MAX,
    GRADE_RANGE_MIN,
    MEDIUM_GRADE_THRESHOLD,
    PERFORMANCE_GOOD_THRESHOLD,
    PERFORMANCE_MEDIUM_THRESHOLD,
)

router = APIRouter(prefix="/api/config", tags=["config"])


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
    }
