"""ML prediction routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..database import get_session
from ..schemas.ml import BatchPredictionResponse, ModelStatusResponse, StudentPrediction, TrainResponse
from ..services.ml import MLService

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.post("/train", response_model=TrainResponse)
async def train_model(
    period: str | None = Query(default=None, description="Period filter for training data"),
    session: Session = Depends(get_session),
):
    """Train the ML models on current student data."""
    service = MLService(session)
    try:
        result = service.train(period=period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/predict/{student_tz}", response_model=StudentPrediction)
async def predict_student(
    student_tz: str,
    period: str | None = Query(default=None, description="Period filter"),
    session: Session = Depends(get_session),
):
    """Get grade prediction and dropout risk for a single student."""
    service = MLService(session)
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
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_session),
):
    """Get predictions for all students."""
    service = MLService(session)
    try:
        result = service.predict_all(period=period, page=page, page_size=page_size)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/status", response_model=ModelStatusResponse)
async def model_status(session: Session = Depends(get_session)):
    """Get current model status and metadata."""
    service = MLService(session)
    return service.get_status()
