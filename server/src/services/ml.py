"""ML prediction service for student grade prediction and dropout risk."""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sqlmodel import Session, select

from ..constants import (
    AT_RISK_GRADE_THRESHOLD,
    CROSS_VALIDATION_FOLDS,
    DEFAULT_PAGE_SIZE,
    HIGH_RISK_THRESHOLD,
    MEDIUM_RISK_THRESHOLD,
    MIN_TRAINING_SAMPLES,
)
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
        student_map = {s.student_tz: s.student_name for s in students}

        if not students:
             return pd.DataFrame(columns=FEATURE_COLUMNS + ["student_tz", "student_name"])

        grade_query = select(Grade).order_by(Grade.id)
        if period:
            grade_query = grade_query.where(Grade.period == period)
        grades = self.session.exec(grade_query).all()

        att_query = select(AttendanceRecord)
        if period:
            att_query = att_query.where(AttendanceRecord.period == period)
        attendance = self.session.exec(att_query).all()

        if grades:
            g_data = [{"student_tz": g.student_tz, "grade": g.grade, "id": g.id} for g in grades]
            gdf = pd.DataFrame(g_data)

            g_stats = gdf.groupby("student_tz")["grade"].agg(
                average_grade="mean",
                min_grade="min",
                max_grade="max",
                grade_std="std",
                num_subjects="count"
            ).reset_index()

            failing = gdf[gdf["grade"] < AT_RISK_GRADE_THRESHOLD].groupby("student_tz").size().reset_index(name="failing_subjects")
            g_stats = pd.merge(g_stats, failing, on="student_tz", how="left").fillna({"failing_subjects": 0})

            def calc_slope(x):
                if len(x) < 2:
                    return 0.0
                indices = np.arange(len(x))
                return np.polyfit(indices, x, 1)[0]

            slopes = gdf.groupby("student_tz")["grade"].apply(calc_slope).reset_index(name="grade_trend_slope")
            g_stats = pd.merge(g_stats, slopes, on="student_tz", how="left")
            
        else:
            g_stats = pd.DataFrame(columns=["student_tz", "average_grade", "min_grade", "max_grade", "grade_std", "num_subjects", "failing_subjects", "grade_trend_slope"])

        if attendance:
            a_data = [
                {
                    "student_tz": a.student_tz,
                    "absence": a.absence,
                    "absence_justified": a.absence_justified,
                    "late": a.late,
                    "disturbance": a.disturbance,
                    "total_absences": a.total_absences,
                    "total_negative_events": a.total_negative_events,
                    "total_positive_events": a.total_positive_events
                }
                for a in attendance
            ]
            adf = pd.DataFrame(a_data)
            
            a_stats = adf.groupby("student_tz").sum().reset_index()
        else:
            a_stats = pd.DataFrame(columns=["student_tz", "absence", "absence_justified", "late", "disturbance", "total_absences", "total_negative_events", "total_positive_events"])
            
        feature_df = pd.DataFrame.from_dict({"student_tz": list(student_map.keys()), "student_name": list(student_map.values())})
        
        if not g_stats.empty:
            feature_df = pd.merge(feature_df, g_stats, on="student_tz", how="left")
        else:
            for col in ["average_grade", "min_grade", "max_grade", "grade_std", "num_subjects", "failing_subjects", "grade_trend_slope"]:
                feature_df[col] = np.nan
            
        if not a_stats.empty:
            feature_df = pd.merge(feature_df, a_stats, on="student_tz", how="left")
        else:
             for col in ["absence", "absence_justified", "late", "disturbance", "total_absences", "total_negative_events", "total_positive_events"]:
                feature_df[col] = 0

        feature_df = feature_df.dropna(subset=["average_grade"])

        values = {
            "grade_std": 0.0,
            "failing_subjects": 0,
            "grade_trend_slope": 0.0,
            "absence": 0,
            "absence_justified": 0,
            "late": 0,
            "disturbance": 0, 
            "total_absences": 0,
            "total_negative_events": 0, 
            "total_positive_events": 0
        }
        feature_df = feature_df.fillna(value=values)
        feature_df["average_grade"] = feature_df["average_grade"].round(2)
        feature_df["grade_std"] = feature_df["grade_std"].round(2)
        feature_df["grade_trend_slope"] = feature_df["grade_trend_slope"].round(4)

        return feature_df

    def train(self, period: str | None = None) -> dict:
        """Train both models and save to disk. Returns training metrics."""
        import joblib

        _prediction_cache.clear()

        df = self._build_feature_dataframe(period=period)

        if len(df) < MIN_TRAINING_SAMPLES:
            raise ValueError(f"Not enough data to train: only {len(df)} students with grades found. Need at least {MIN_TRAINING_SAMPLES}.")

        X = df[FEATURE_COLUMNS].values
        y_grade = df["average_grade"].values

        median_negative = df["total_negative_events"].median()
        median_absences = df["total_absences"].median()
        y_dropout = (
            ((df["average_grade"] < AT_RISK_GRADE_THRESHOLD) & ((df["total_negative_events"] > median_negative) | (df["total_absences"] > median_absences)))
            .astype(int)
            .values
        )

        grade_model = RandomForestRegressor(
            n_estimators=300,
            min_samples_split=2,
            min_samples_leaf=1,
            max_features=None,
            max_depth=None,
            n_jobs=-1,
        )
        grade_model.fit(X, y_grade)
        grade_cv = cross_val_score(grade_model, X, y_grade, cv=min(CROSS_VALIDATION_FOLDS, len(df)), scoring="neg_mean_absolute_error")
        grade_mae = round(float(-grade_cv.mean()), 2)

        dropout_model = RandomForestClassifier(
            n_estimators=100,
            min_samples_split=2,
            min_samples_leaf=2,
            max_features="sqrt",
            max_depth=5,
            n_jobs=-1,
        )
        dropout_model.fit(X, y_dropout)
        dropout_cv = cross_val_score(dropout_model, X, y_dropout, cv=min(CROSS_VALIDATION_FOLDS, len(df)), scoring="accuracy")
        dropout_accuracy = round(float(dropout_cv.mean()), 4)

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(grade_model, GRADE_MODEL_PATH)
        joblib.dump(dropout_model, DROPOUT_MODEL_PATH)

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
        proba = dropout_model.predict_proba(X)
        if proba.shape[1] == 1:
            dropout_proba = 0.0
        else:
            dropout_proba = float(proba[0][1])
        dropout_risk = round(dropout_proba, 4)

        if dropout_risk > HIGH_RISK_THRESHOLD:
            risk_level = "high"
        elif dropout_risk > MEDIUM_RISK_THRESHOLD:
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
            if dropout_risk > HIGH_RISK_THRESHOLD:
                risk_level = "high"
            elif dropout_risk > MEDIUM_RISK_THRESHOLD:
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

    def predict_all(self, period: str | None = None, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
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
