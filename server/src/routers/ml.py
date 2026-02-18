"""ML prediction routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..dependencies import get_ml_service
from ..schemas.ml import BatchPredictionResponse, ModelStatusResponse, StudentPrediction, TrainResponse
from ..services.ml import MLService

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.post("/train", response_model=TrainResponse)
async def train_model(
    period: str | None = Query(default=None, description="Period filter for training data"),
    service: MLService = Depends(get_ml_service),
):
    """Train the ML models on current student data."""
    try:
        result = service.train(period=period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/predict/{student_tz}", response_model=StudentPrediction)
async def predict_student(
    student_tz: str,
    period: str | None = Query(default=None, description="Period filter"),
    service: MLService = Depends(get_ml_service),
):
    """Get grade prediction and dropout risk for a single student."""
    try:
        result = service.predict_student(student_tz=student_tz, period=period)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.get("/predict", response_model=BatchPredictionResponse)
async def predict_all(
    period: str | None = Query(default=None, description="Period filter"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    service: MLService = Depends(get_ml_service),
):
    """Get predictions for all students."""
    try:
        result = service.predict_all(period=period, page=page, page_size=page_size)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/status", response_model=ModelStatusResponse)
async def model_status(service: MLService = Depends(get_ml_service)):
    """Get current model status and metadata."""
    return service.get_status()
