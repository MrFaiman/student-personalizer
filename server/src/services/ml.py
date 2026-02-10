"""ML prediction service for student grade prediction and dropout risk."""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sqlmodel import Session, select

from ..models import AttendanceRecord, Grade, Student

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
GRADE_MODEL_PATH = MODELS_DIR / "grade_predictor.joblib"
DROPOUT_MODEL_PATH = MODELS_DIR / "dropout_classifier.joblib"
META_PATH = MODELS_DIR / "model_meta.json"

_prediction_cache: dict[tuple[str | None, str | None], list[dict]] = {}


FEATURE_COLUMNS = [
    "average_grade",
    "min_grade",
    "max_grade",
    "grade_std",
    "grade_trend_slope",
    "num_subjects",
    "failing_subjects",
    "absence",
    "absence_justified",
    "late",
    "disturbance",
    "total_absences",
    "total_negative_events",
    "total_positive_events",
]


class MLService:
    """ML service for training and predicting student outcomes."""

    def __init__(self, session: Session):
        self.session = session

    def _build_feature_dataframe(self, period: str | None = None) -> pd.DataFrame:
        """Extract feature vectors for all students from the database."""
        students = self.session.exec(select(Student)).all()
        rows = []

        for student in students:
            grade_query = select(Grade).where(Grade.student_tz == student.student_tz)
            if period:
                grade_query = grade_query.where(Grade.period == period)
            grade_query = grade_query.order_by(Grade.id)
            grades = self.session.exec(grade_query).all()

            if not grades:
                continue

            grade_values = [g.grade for g in grades]
            avg_grade = np.mean(grade_values)
            min_grade = np.min(grade_values)
            max_grade = np.max(grade_values)
            grade_std = float(np.std(grade_values)) if len(grade_values) > 1 else 0.0
            num_subjects = len(grade_values)
            failing_subjects = sum(1 for g in grade_values if g < 55)

            # Trend slope: linear fit of grades over their temporal index.
            # Positive slope = improving, negative = declining. 0.0 if single grade.
            if len(grade_values) >= 2:
                x = np.arange(len(grade_values), dtype=float)
                grade_trend_slope = float(np.polyfit(x, grade_values, 1)[0])
            else:
                grade_trend_slope = 0.0

            att_query = select(AttendanceRecord).where(AttendanceRecord.student_tz == student.student_tz)
            if period:
                att_query = att_query.where(AttendanceRecord.period == period)
            attendance = self.session.exec(att_query).all()

            absence = sum(a.absence for a in attendance)
            absence_justified = sum(a.absence_justified for a in attendance)
            late = sum(a.late for a in attendance)
            disturbance = sum(a.disturbance for a in attendance)
            total_absences = sum(a.total_absences for a in attendance)
            total_negative = sum(a.total_negative_events for a in attendance)
            total_positive = sum(a.total_positive_events for a in attendance)

            rows.append(
                {
                    "student_tz": student.student_tz,
                    "student_name": student.student_name,
                    "average_grade": round(float(avg_grade), 2),
                    "min_grade": float(min_grade),
                    "max_grade": float(max_grade),
                    "grade_std": round(grade_std, 2),
                    "grade_trend_slope": round(grade_trend_slope, 4),
                    "num_subjects": num_subjects,
                    "failing_subjects": failing_subjects,
                    "absence": absence,
                    "absence_justified": absence_justified,
                    "late": late,
                    "disturbance": disturbance,
                    "total_absences": total_absences,
                    "total_negative_events": total_negative,
                    "total_positive_events": total_positive,
                }
            )

        return pd.DataFrame(rows)

    def train(self, period: str | None = None) -> dict:
        """Train both models and save to disk. Returns training metrics."""
        import joblib

        _prediction_cache.clear()

        df = self._build_feature_dataframe(period=period)

        if len(df) < 5:
            raise ValueError(f"Not enough data to train: only {len(df)} students with grades found. Need at least 5.")

        X = df[FEATURE_COLUMNS].values
        y_grade = df["average_grade"].values

        # Dropout label: average < 55 AND (high absences OR high negative events)
        median_negative = df["total_negative_events"].median()
        median_absences = df["total_absences"].median()
        y_dropout = (
            ((df["average_grade"] < 55) & ((df["total_negative_events"] > median_negative) | (df["total_absences"] > median_absences)))
            .astype(int)
            .values
        )

        # Train grade predictor
        grade_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        grade_model.fit(X, y_grade)
        grade_cv = cross_val_score(grade_model, X, y_grade, cv=min(5, len(df)), scoring="neg_mean_absolute_error")
        grade_mae = round(float(-grade_cv.mean()), 2)

        # Train dropout classifier
        dropout_model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        dropout_model.fit(X, y_dropout)
        dropout_cv = cross_val_score(dropout_model, X, y_dropout, cv=min(5, len(df)), scoring="accuracy")
        dropout_accuracy = round(float(dropout_cv.mean()), 4)

        # Save models
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(grade_model, GRADE_MODEL_PATH)
        joblib.dump(dropout_model, DROPOUT_MODEL_PATH)

        # Feature importances
        grade_importances = {name: round(float(imp), 4) for name, imp in zip(FEATURE_COLUMNS, grade_model.feature_importances_)}
        dropout_importances = {name: round(float(imp), 4) for name, imp in zip(FEATURE_COLUMNS, dropout_model.feature_importances_)}

        meta = {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "samples": len(df),
            "grade_model_mae": grade_mae,
            "dropout_model_accuracy": dropout_accuracy,
            "grade_feature_importances": grade_importances,
            "dropout_feature_importances": dropout_importances,
        }
        with open(META_PATH, "w") as f:
            json.dump(meta, f, indent=2)

        return {
            "status": "trained",
            "samples": len(df),
            "grade_model_mae": grade_mae,
            "dropout_model_accuracy": dropout_accuracy,
            "grade_feature_importances": grade_importances,
            "dropout_feature_importances": dropout_importances,
        }

    def _load_models(self) -> tuple:
        """Load trained models from disk."""
        import joblib

        if not GRADE_MODEL_PATH.exists() or not DROPOUT_MODEL_PATH.exists():
            raise FileNotFoundError("Models not trained yet. Call POST /api/ml/train first.")

        grade_model = joblib.load(GRADE_MODEL_PATH)
        dropout_model = joblib.load(DROPOUT_MODEL_PATH)
        return grade_model, dropout_model

    def predict_student(self, student_tz: str, period: str | None = None) -> dict:
        """Predict grade and dropout risk for a single student."""
        grade_model, dropout_model = self._load_models()

        df = self._build_feature_dataframe(period=period)
        student_row = df[df["student_tz"] == student_tz]

        if student_row.empty:
            raise ValueError(f"Student '{student_tz}' not found or has no grade data.")

        row = student_row.iloc[0]
        X = row[FEATURE_COLUMNS].values.reshape(1, -1)

        predicted_grade = round(float(grade_model.predict(X)[0]), 2)
        # Handle case when model was trained with only one class
        proba = dropout_model.predict_proba(X)
        if proba.shape[1] == 1:
            dropout_proba = 0.0
        else:
            dropout_proba = float(proba[0][1])
        dropout_risk = round(dropout_proba, 4)

        if dropout_risk > 0.7:
            risk_level = "high"
        elif dropout_risk > 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"

        features = {col: _convert_value(row[col]) for col in FEATURE_COLUMNS}

        return {
            "student_tz": student_tz,
            "student_name": row["student_name"],
            "predicted_grade": predicted_grade,
            "dropout_risk": dropout_risk,
            "risk_level": risk_level,
            "features": features,
        }

    def _get_model_trained_at(self) -> str | None:
        """Get the trained_at timestamp from model metadata for cache keying."""
        if not META_PATH.exists():
            return None
        with open(META_PATH) as f:
            meta = json.load(f)
        return meta.get("trained_at")

    def _compute_all_predictions(self, period: str | None = None) -> list[dict]:
        """Compute predictions for all students (cached by period + model version)."""
        trained_at = self._get_model_trained_at()
        cache_key = (period, trained_at)

        if cache_key in _prediction_cache:
            return _prediction_cache[cache_key]

        grade_model, dropout_model = self._load_models()
        df = self._build_feature_dataframe(period=period)
        if df.empty:
            _prediction_cache[cache_key] = []
            return []

        X = df[FEATURE_COLUMNS].values
        predicted_grades = grade_model.predict(X)
        proba = dropout_model.predict_proba(X)
        if proba.shape[1] == 1:
            dropout_probas = np.zeros(len(X))
        else:
            dropout_probas = proba[:, 1]

        all_predictions = []
        for i, row in df.iterrows():
            dropout_risk = round(float(dropout_probas[i]), 4)
            if dropout_risk > 0.7:
                risk_level = "high"
            elif dropout_risk > 0.3:
                risk_level = "medium"
            else:
                risk_level = "low"

            features = {col: _convert_value(row[col]) for col in FEATURE_COLUMNS}

            all_predictions.append(
                {
                    "student_tz": row["student_tz"],
                    "student_name": row["student_name"],
                    "predicted_grade": round(float(predicted_grades[i]), 2),
                    "dropout_risk": dropout_risk,
                    "risk_level": risk_level,
                    "features": features,
                }
            )

        all_predictions.sort(key=lambda p: p["dropout_risk"], reverse=True)
        _prediction_cache[cache_key] = all_predictions
        return all_predictions

    def predict_all(self, period: str | None = None, page: int = 1, page_size: int = 20) -> dict:
        """Predict for all students with pagination."""
        all_predictions = self._compute_all_predictions(period=period)

        total = len(all_predictions)
        high_risk_count = sum(1 for p in all_predictions if p["risk_level"] == "high")
        medium_risk_count = sum(1 for p in all_predictions if p["risk_level"] == "medium")

        start = (page - 1) * page_size
        end = start + page_size
        paginated = all_predictions[start:end]

        return {
            "predictions": paginated,
            "model_trained": True,
            "total_students": total,
            "total": total,
            "page": page,
            "page_size": page_size,
            "high_risk_count": high_risk_count,
            "medium_risk_count": medium_risk_count,
        }

    def get_status(self) -> dict:
        """Get model status and metadata."""
        if not META_PATH.exists():
            return {"trained": False}

        with open(META_PATH) as f:
            meta = json.load(f)

        return {
            "trained": True,
            "trained_at": meta.get("trained_at"),
            "samples": meta.get("samples"),
            "grade_model_mae": meta.get("grade_model_mae"),
            "dropout_model_accuracy": meta.get("dropout_model_accuracy"),
        }


def _convert_value(val):
    """Convert numpy types to Python native types."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    return val
