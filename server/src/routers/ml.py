"""ML prediction routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..audit.service import log_event
from ..auth.current_user import CurrentUser
from ..auth.dependencies import get_current_user, require_permission, require_school_scope
from ..auth.permissions import PermissionKey
from ..constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..database import get_session
from ..schemas.ml import BatchPredictionResponse, ModelStatusResponse, StudentPrediction, TrainResponse
from ..services.ml import MLService

router = APIRouter(prefix="/api/ml", tags=["ml"], dependencies=[Depends(require_school_scope)])


@router.post("/train", response_model=TrainResponse)
async def train_model(
    period: str | None = Query(default=None, description="Period filter for training data"),
    current_user: CurrentUser = Depends(require_permission(PermissionKey.ml_train.value)),
    session: Session = Depends(get_session),
):
    """Train the ML models on current student data."""
    service = MLService(session)
    try:
        result = service.train(current_user=current_user, period=period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    log_event(session, action="ml_train", user_id=current_user.user_id, user_email=current_user.email, success=True, detail={"period": period})
    return result


@router.get("/predict/{student_tz}", response_model=StudentPrediction)
async def predict_student(
    student_tz: str,
    period: str | None = Query(default=None, description="Period filter"),
    current_user: CurrentUser = Depends(require_permission(PermissionKey.students_read.value)),
    session: Session = Depends(get_session),
):
    """Get grade prediction and dropout risk for a single student."""
    service = MLService(session)
    try:
        result = service.predict_student(current_user=current_user, student_tz=student_tz, period=period)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    log_event(session, action="ml_predict", user_id=current_user.user_id, user_email=current_user.email, success=True, detail={"student_tz": student_tz, "period": period})
    return result


@router.get("/predict", response_model=BatchPredictionResponse)
async def predict_all(
    period: str | None = Query(default=None, description="Period filter"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    sort_by: str | None = Query(default=None, description="Column to sort by: student_name, predicted_grade, dropout_risk, risk_level"),
    sort_order: str = Query(default="asc", description="Sort direction: asc or desc"),
    current_user: CurrentUser = Depends(require_permission(PermissionKey.students_read.value)),
    session: Session = Depends(get_session),
):
    """Get predictions for all students."""
    service = MLService(session)
    try:
        result = service.predict_all(
            current_user=current_user,
            period=period,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    log_event(session, action="ml_predict_batch", user_id=current_user.user_id, user_email=current_user.email, success=True, detail={"period": period, "page": page})
    return result


@router.get("/status", response_model=ModelStatusResponse)
async def model_status(
    session: Session = Depends(get_session),
    _current_user: CurrentUser = Depends(get_current_user),
):
    """Get current model status and metadata."""
    service = MLService(session)
    return service.get_status()
