"""ML prediction schemas."""

from pydantic import BaseModel


class StudentFeatures(BaseModel):
    """Feature vector used for prediction."""

    average_grade: float
    min_grade: float
    max_grade: float
    grade_std: float
    grade_trend_slope: float
    num_subjects: int
    failing_subjects: int
    absence: int
    absence_justified: int
    late: int
    disturbance: int
    total_absences: int
    total_negative_events: int
    total_positive_events: int


class StudentPrediction(BaseModel):
    """Prediction result for a single student."""

    student_tz: str
    student_name: str
    predicted_grade: float
    dropout_risk: float
    risk_level: str
    features: StudentFeatures


class TrainResponse(BaseModel):
    """Training result with metrics."""

    status: str
    samples: int
    grade_model_mae: float
    dropout_model_accuracy: float
    grade_feature_importances: dict[str, float]
    dropout_feature_importances: dict[str, float]


class BatchPredictionResponse(BaseModel):
    """Batch prediction response."""

    predictions: list[StudentPrediction]
    model_trained: bool
    total_students: int


class ModelStatusResponse(BaseModel):
    """Model status information."""

    trained: bool
    trained_at: str | None = None
    samples: int | None = None
    grade_model_mae: float | None = None
    dropout_model_accuracy: float | None = None
