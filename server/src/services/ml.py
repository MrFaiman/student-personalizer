"""ML prediction service for student grade prediction and dropout risk."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    mean_absolute_error,
    median_absolute_error,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score
from sqlmodel import Session, select

from ..auth.current_user import CurrentUser
from ..constants import (
    AT_RISK_GRADE_THRESHOLD,
    CROSS_VALIDATION_FOLDS,
    DEFAULT_PAGE_SIZE,
    HIGH_RISK_THRESHOLD,
    MEDIUM_RISK_THRESHOLD,
    MIN_TRAINING_SAMPLES,
)
from ..models import AttendanceRecord, Grade, Student
from ..services.ml_privacy import FEATURE_COLUMNS, assert_no_pii

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
GRADE_MODEL_FILENAME = "grade_predictor.joblib"
DROPOUT_MODEL_FILENAME = "dropout_classifier.joblib"
META_FILENAME = "model_meta.json"
RANDOM_STATE = 42

_prediction_cache: dict[tuple[str | None, str | None, int], list[dict]] = {}


def _year_sort_value(year: str | None) -> int:
    if not year:
        return 0
    digits = re.findall(r"\d+", str(year))
    return int(digits[0]) if digits else 0


def _period_sort_value(period: str | None) -> tuple[int, str]:
    if not period:
        return 10_000, ""
    normalized = str(period).strip().lower()
    quarter_match = re.search(r"(?:q|quarter)\s*(\d+)", normalized)
    if quarter_match:
        return int(quarter_match.group(1)), normalized
    sem_hebrew_map = {"א": 1, "ב": 2, "ג": 3, "ד": 4}
    for sem_letter, rank in sem_hebrew_map.items():
        if sem_letter in normalized:
            return rank, normalized
    digits = re.findall(r"\d+", normalized)
    if digits:
        return int(digits[0]), normalized
    return 10_000, normalized


def _to_period_key(year: str | None, period: str | None) -> tuple[int, int, str]:
    period_rank, period_label = _period_sort_value(period)
    return (_year_sort_value(year), period_rank, period_label)


def _risk_level_from_score(dropout_risk: float) -> str:
    if dropout_risk > HIGH_RISK_THRESHOLD:
        return "high"
    if dropout_risk > MEDIUM_RISK_THRESHOLD:
        return "medium"
    return "low"


class MLService:
    """ML service for training and predicting student outcomes."""

    def __init__(self, session: Session):
        self.session = session

    def _require_school_id(self, current_user: CurrentUser) -> int:
        if current_user.school_id is None:
            raise ValueError("School scope required")
        return current_user.school_id

    def _get_model_paths(self, school_id: int) -> tuple[Path, Path, Path]:
        school_dir = MODELS_DIR / f"school_{school_id}"
        return school_dir / GRADE_MODEL_FILENAME, school_dir / DROPOUT_MODEL_FILENAME, school_dir / META_FILENAME

    def _build_period_feature_dataframe(self, *, current_user: CurrentUser, period: str | None = None) -> pd.DataFrame:
        """Build a period-aware feature dataframe with one row per student-period."""
        school_id = self._require_school_id(current_user)
        students = self.session.exec(select(Student).where(Student.school_id == school_id)).all()
        student_map = {s.student_tz: s.student_name for s in students}

        if not students:
            return pd.DataFrame(columns=["student_tz", "student_name", "year", "period"] + FEATURE_COLUMNS)

        grade_query = select(Grade).where(Grade.school_id == school_id)
        grades = self.session.exec(grade_query).all()

        if not grades:
            return pd.DataFrame(columns=["student_tz", "student_name", "year", "period"] + FEATURE_COLUMNS)

        att_query = select(AttendanceRecord).where(AttendanceRecord.school_id == school_id)
        attendance = self.session.exec(att_query).all()

        g_data = [
            {
                "student_tz": g.student_tz,
                "year": g.year or "",
                "period": g.period,
                "grade": float(g.grade),
            }
            for g in grades
        ]
        gdf = pd.DataFrame(g_data)
        g_stats = (
            gdf.groupby(["student_tz", "year", "period"])["grade"]
            .agg(
                average_grade="mean",
                min_grade="min",
                max_grade="max",
                grade_std="std",
                num_subjects="count",
            )
            .reset_index()
        )
        failing = (
            gdf[gdf["grade"] < AT_RISK_GRADE_THRESHOLD]
            .groupby(["student_tz", "year", "period"])
            .size()
            .reset_index(name="failing_subjects")
        )
        g_stats = pd.merge(g_stats, failing, on=["student_tz", "year", "period"], how="left").fillna({"failing_subjects": 0})

        if attendance:
            a_data = [
                {
                    "student_tz": a.student_tz,
                    "year": a.year or "",
                    "period": a.period,
                    "absence": a.absence,
                    "absence_justified": a.absence_justified,
                    "late": a.late,
                    "disturbance": a.disturbance,
                    "total_absences": a.total_absences,
                    "total_negative_events": a.total_negative_events,
                    "total_positive_events": a.total_positive_events,
                }
                for a in attendance
            ]
            adf = pd.DataFrame(a_data)
            a_stats = adf.groupby(["student_tz", "year", "period"]).sum().reset_index()
        else:
            a_stats = pd.DataFrame(
                columns=[
                    "student_tz",
                    "year",
                    "period",
                    "absence",
                    "absence_justified",
                    "late",
                    "disturbance",
                    "total_absences",
                    "total_negative_events",
                    "total_positive_events",
                ]
            )

        feature_df = pd.merge(g_stats, a_stats, on=["student_tz", "year", "period"], how="left")
        feature_df["student_name"] = feature_df["student_tz"].map(student_map)
        feature_df = feature_df.dropna(subset=["student_name", "average_grade"])

        fill_values = {
            "grade_std": 0.0,
            "failing_subjects": 0,
            "absence": 0,
            "absence_justified": 0,
            "late": 0,
            "disturbance": 0,
            "total_absences": 0,
            "total_negative_events": 0,
            "total_positive_events": 0,
        }
        feature_df = feature_df.fillna(value=fill_values)

        # Grade trend is computed across periods in explicit chronological order.
        feature_df["_period_key"] = feature_df.apply(lambda row: _to_period_key(row["year"], row["period"]), axis=1)
        feature_df = feature_df.sort_values(["student_tz", "_period_key"], kind="stable")
        feature_df["grade_trend_slope"] = 0.0

        for _, idxs in feature_df.groupby("student_tz").groups.items():
            ordered_idx = list(idxs)
            grades_for_student = feature_df.loc[ordered_idx, "average_grade"].to_numpy(dtype=float)
            slopes: list[float] = []
            for i in range(len(grades_for_student)):
                if i < 1:
                    slopes.append(0.0)
                    continue
                x = np.arange(i + 1, dtype=float)
                y = grades_for_student[: i + 1]
                slopes.append(float(np.polyfit(x, y, 1)[0]))
            feature_df.loc[ordered_idx, "grade_trend_slope"] = slopes

        if period:
            feature_df = feature_df[feature_df["period"] == period].copy()

        feature_df["average_grade"] = feature_df["average_grade"].round(2)
        feature_df["grade_std"] = feature_df["grade_std"].round(2)
        feature_df["grade_trend_slope"] = feature_df["grade_trend_slope"].round(4)
        feature_df = feature_df.drop(columns=["_period_key"])

        return feature_df[["student_tz", "student_name", "year", "period"] + FEATURE_COLUMNS]

    def _build_feature_dataframe(self, *, current_user: CurrentUser, period: str | None = None) -> pd.DataFrame:
        """
        Build features for prediction.

        - If period is provided: return that period snapshot.
        - If period is not provided: return latest available period per student.
        """
        period_df = self._build_period_feature_dataframe(current_user=current_user, period=period)
        if period_df.empty:
            return pd.DataFrame(columns=["student_tz", "student_name", "year", "period"] + FEATURE_COLUMNS)
        if period:
            return period_df

        ranked = period_df.copy()
        ranked["_period_key"] = ranked.apply(lambda row: _to_period_key(row["year"], row["period"]), axis=1)
        ranked = ranked.sort_values(["student_tz", "_period_key"], kind="stable")
        latest = ranked.groupby("student_tz", as_index=False).tail(1).drop(columns=["_period_key"])
        return latest.reset_index(drop=True)

    def _build_training_dataframe(self, *, current_user: CurrentUser, period: str | None = None) -> pd.DataFrame:
        """
        Build supervised training rows where each row predicts a future period outcome.

        Features come from period T, targets are derived from period T+1.
        """
        snapshots = self._build_period_feature_dataframe(current_user=current_user)
        if snapshots.empty:
            return pd.DataFrame()

        rows: list[dict] = []
        snapshots = snapshots.copy()
        snapshots["_period_key"] = snapshots.apply(lambda row: _to_period_key(row["year"], row["period"]), axis=1)
        snapshots = snapshots.sort_values(["student_tz", "_period_key"], kind="stable")

        for _, group in snapshots.groupby("student_tz"):
            ordered = group.reset_index(drop=True)
            for i in range(len(ordered) - 1):
                current = ordered.iloc[i]
                nxt = ordered.iloc[i + 1]
                if period and current["period"] != period:
                    continue

                row: dict[str, object] = {
                    "student_tz": current["student_tz"],
                    "feature_year": current["year"],
                    "feature_period": current["period"],
                    "target_year": nxt["year"],
                    "target_period": nxt["period"],
                    "target_next_average_grade": float(nxt["average_grade"]),
                    "target_next_total_absences": float(nxt["total_absences"]),
                    "target_next_total_negative_events": float(nxt["total_negative_events"]),
                }
                for col in FEATURE_COLUMNS:
                    row[col] = _convert_value(current[col])
                rows.append(row)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        median_next_absences = float(df["target_next_total_absences"].median())
        median_next_negative = float(df["target_next_total_negative_events"].median())
        df["target_next_dropout"] = (
            (df["target_next_average_grade"] < AT_RISK_GRADE_THRESHOLD)
            | (df["target_next_total_absences"] > median_next_absences)
            | (df["target_next_total_negative_events"] > median_next_negative)
        ).astype(int)
        return df

    def _assert_no_target_leakage(self, *, feature_columns: list[str], target_columns: list[str]) -> None:
        overlap = sorted(set(feature_columns).intersection(target_columns))
        if overlap:
            raise ValueError(f"Target leakage detected. Features overlap with targets: {overlap}")

    def _fit_dropout_model(self, X: np.ndarray, y: np.ndarray):
        model = RandomForestClassifier(
            n_estimators=200,
            min_samples_split=2,
            min_samples_leaf=2,
            max_features="sqrt",
            max_depth=8,
            class_weight="balanced",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        )
        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            model.fit(X, y)
            return model

        class_counts = np.bincount(y.astype(int))
        non_zero_class_counts = class_counts[class_counts > 0]
        min_class_count = int(non_zero_class_counts.min()) if len(non_zero_class_counts) else 1
        cv_folds = min(CROSS_VALIDATION_FOLDS, len(y), min_class_count)
        if cv_folds >= 2:
            calibrated = CalibratedClassifierCV(estimator=model, method="sigmoid", cv=cv_folds)
            calibrated.fit(X, y)
            return calibrated

        model.fit(X, y)
        return model

    def _positive_class_proba(self, model, X: np.ndarray) -> np.ndarray:
        proba = model.predict_proba(X)
        if proba.shape[1] == 1:
            return np.zeros(len(X))
        classes = getattr(model, "classes_", None)
        if classes is None:
            return proba[:, 1]
        class_list = list(classes)
        if 1 in class_list:
            idx = class_list.index(1)
            return proba[:, idx]
        return np.zeros(len(X))

    def _extract_dropout_importances(self, model) -> np.ndarray:
        if hasattr(model, "feature_importances_"):
            return np.asarray(model.feature_importances_, dtype=float)

        if isinstance(model, CalibratedClassifierCV):
            fold_importances: list[np.ndarray] = []
            for calibrated_model in model.calibrated_classifiers_:
                estimator = getattr(calibrated_model, "estimator", None) or getattr(calibrated_model, "base_estimator", None)
                if estimator is not None and hasattr(estimator, "feature_importances_"):
                    fold_importances.append(np.asarray(estimator.feature_importances_, dtype=float))
            if fold_importances:
                return np.mean(np.vstack(fold_importances), axis=0)

        return np.zeros(len(FEATURE_COLUMNS), dtype=float)

    def _evaluate_models(self, *, X: np.ndarray, y_grade: np.ndarray, y_dropout: np.ndarray, feature_period_keys: list[tuple[int, int, str]]) -> dict:
        metrics: dict[str, object] = {
            "grade_model_mae": None,
            "grade_model_median_ae": None,
            "dropout_model_accuracy": None,
            "dropout_model_roc_auc": None,
            "dropout_model_pr_auc": None,
            "dropout_precision_high_risk": None,
            "dropout_recall_high_risk": None,
            "dropout_confusion_matrix": None,
            "evaluation_strategy": "cross_validation",
            "cv_folds_grade": 1,
            "cv_folds_dropout": 1,
        }

        unique_periods = sorted(set(feature_period_keys))
        if len(unique_periods) >= 2:
            validation_period = unique_periods[-1]
            is_validation = np.array([k == validation_period for k in feature_period_keys], dtype=bool)
            is_training = ~is_validation
            if int(is_training.sum()) >= 2 and int(is_validation.sum()) >= 1:
                X_train, X_val = X[is_training], X[is_validation]
                y_grade_train, y_grade_val = y_grade[is_training], y_grade[is_validation]
                y_drop_train, y_drop_val = y_dropout[is_training], y_dropout[is_validation]

                grade_eval_model = RandomForestRegressor(
                    n_estimators=300,
                    min_samples_split=2,
                    min_samples_leaf=1,
                    max_features=None,
                    max_depth=None,
                    n_jobs=-1,
                    random_state=RANDOM_STATE,
                )
                grade_eval_model.fit(X_train, y_grade_train)
                grade_val_pred = grade_eval_model.predict(X_val)
                metrics["grade_model_mae"] = round(float(mean_absolute_error(y_grade_val, grade_val_pred)), 2)
                metrics["grade_model_median_ae"] = round(float(median_absolute_error(y_grade_val, grade_val_pred)), 2)
                metrics["evaluation_strategy"] = "temporal_holdout"

                dropout_eval_model = self._fit_dropout_model(X_train, y_drop_train)
                drop_val_proba = self._positive_class_proba(dropout_eval_model, X_val)
                drop_val_pred = (drop_val_proba >= 0.5).astype(int)
                drop_val_high = (drop_val_proba >= HIGH_RISK_THRESHOLD).astype(int)
                metrics["dropout_model_accuracy"] = round(float(accuracy_score(y_drop_val, drop_val_pred)), 4)
                metrics["dropout_precision_high_risk"] = round(
                    float(precision_score(y_drop_val, drop_val_high, zero_division=0)),
                    4,
                )
                metrics["dropout_recall_high_risk"] = round(
                    float(recall_score(y_drop_val, drop_val_high, zero_division=0)),
                    4,
                )
                metrics["dropout_confusion_matrix"] = confusion_matrix(y_drop_val, drop_val_pred, labels=[0, 1]).tolist()
                if len(np.unique(y_drop_val)) >= 2:
                    metrics["dropout_model_roc_auc"] = round(float(roc_auc_score(y_drop_val, drop_val_proba)), 4)
                    metrics["dropout_model_pr_auc"] = round(float(average_precision_score(y_drop_val, drop_val_proba)), 4)
                return metrics

        # Cross-validation fallback.
        grade_cv_folds = min(CROSS_VALIDATION_FOLDS, len(y_grade))
        metrics["cv_folds_grade"] = grade_cv_folds
        if grade_cv_folds >= 2:
            kfold = KFold(n_splits=grade_cv_folds, shuffle=True, random_state=RANDOM_STATE)
            grade_model = RandomForestRegressor(
                n_estimators=300,
                min_samples_split=2,
                min_samples_leaf=1,
                max_features=None,
                max_depth=None,
                n_jobs=-1,
                random_state=RANDOM_STATE,
            )
            grade_mae_cv = cross_val_score(grade_model, X, y_grade, cv=kfold, scoring="neg_mean_absolute_error")
            grade_medae_cv = cross_val_score(grade_model, X, y_grade, cv=kfold, scoring="neg_median_absolute_error")
            metrics["grade_model_mae"] = round(float(-grade_mae_cv.mean()), 2)
            metrics["grade_model_median_ae"] = round(float(-grade_medae_cv.mean()), 2)
        else:
            grade_model = RandomForestRegressor(n_estimators=300, n_jobs=-1, random_state=RANDOM_STATE)
            grade_model.fit(X, y_grade)
            grade_pred = grade_model.predict(X)
            metrics["grade_model_mae"] = round(float(mean_absolute_error(y_grade, grade_pred)), 2)
            metrics["grade_model_median_ae"] = round(float(median_absolute_error(y_grade, grade_pred)), 2)

        unique_classes = np.unique(y_dropout)
        class_counts = np.bincount(y_dropout.astype(int))
        non_zero_class_counts = class_counts[class_counts > 0]
        min_class_count = int(non_zero_class_counts.min()) if len(non_zero_class_counts) else 1
        dropout_cv_folds = min(CROSS_VALIDATION_FOLDS, len(y_dropout), min_class_count)
        metrics["cv_folds_dropout"] = dropout_cv_folds

        dropout_eval_model = self._fit_dropout_model(X, y_dropout)
        full_proba = self._positive_class_proba(dropout_eval_model, X)
        full_pred = (full_proba >= 0.5).astype(int)
        full_pred_high = (full_proba >= HIGH_RISK_THRESHOLD).astype(int)
        metrics["dropout_model_accuracy"] = round(float(accuracy_score(y_dropout, full_pred)), 4)
        metrics["dropout_precision_high_risk"] = round(float(precision_score(y_dropout, full_pred_high, zero_division=0)), 4)
        metrics["dropout_recall_high_risk"] = round(float(recall_score(y_dropout, full_pred_high, zero_division=0)), 4)
        metrics["dropout_confusion_matrix"] = confusion_matrix(y_dropout, full_pred, labels=[0, 1]).tolist()
        if len(unique_classes) >= 2:
            metrics["dropout_model_roc_auc"] = round(float(roc_auc_score(y_dropout, full_proba)), 4)
            metrics["dropout_model_pr_auc"] = round(float(average_precision_score(y_dropout, full_proba)), 4)
        if dropout_cv_folds >= 2 and len(unique_classes) >= 2:
            skf = StratifiedKFold(n_splits=dropout_cv_folds, shuffle=True, random_state=RANDOM_STATE)
            dropout_base = RandomForestClassifier(
                n_estimators=200,
                min_samples_leaf=2,
                max_features="sqrt",
                max_depth=8,
                class_weight="balanced",
                n_jobs=-1,
                random_state=RANDOM_STATE,
            )
            acc_cv = cross_val_score(dropout_base, X, y_dropout, cv=skf, scoring="accuracy")
            metrics["dropout_model_accuracy"] = round(float(acc_cv.mean()), 4)
        return metrics

    def train(self, *, current_user: CurrentUser, period: str | None = None) -> dict:
        """Train both models and save to disk. Returns training metrics."""
        import joblib

        school_id = self._require_school_id(current_user)
        _prediction_cache.clear()

        df = self._build_training_dataframe(current_user=current_user, period=period)
        if len(df) < MIN_TRAINING_SAMPLES:
            raise ValueError(
                f"Not enough data to train: only {len(df)} sequential period samples found. Need at least {MIN_TRAINING_SAMPLES}."
            )

        assert_no_pii(FEATURE_COLUMNS)
        self._assert_no_target_leakage(
            feature_columns=FEATURE_COLUMNS,
            target_columns=["target_next_average_grade", "target_next_dropout"],
        )

        X = df[FEATURE_COLUMNS].values
        y_grade = df["target_next_average_grade"].values
        y_dropout = df["target_next_dropout"].astype(int).values
        feature_period_keys = [_to_period_key(y, p) for y, p in zip(df["feature_year"], df["feature_period"], strict=False)]

        eval_metrics = self._evaluate_models(X=X, y_grade=y_grade, y_dropout=y_dropout, feature_period_keys=feature_period_keys)

        grade_model = RandomForestRegressor(
            n_estimators=300,
            min_samples_split=2,
            min_samples_leaf=1,
            max_features=None,
            max_depth=None,
            n_jobs=-1,
            random_state=RANDOM_STATE,
        )
        grade_model.fit(X, y_grade)

        dropout_model = self._fit_dropout_model(X, y_dropout)

        grade_importances = {
            name: round(float(imp), 4)
            for name, imp in zip(FEATURE_COLUMNS, np.asarray(grade_model.feature_importances_, dtype=float), strict=False)
        }
        dropout_importance_values = self._extract_dropout_importances(dropout_model)
        dropout_importances = {
            name: round(float(imp), 4)
            for name, imp in zip(FEATURE_COLUMNS, dropout_importance_values, strict=False)
        }

        grade_path, dropout_path, meta_path = self._get_model_paths(school_id)
        grade_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(grade_model, grade_path)
        joblib.dump(dropout_model, dropout_path)

        class_counts = np.bincount(y_dropout.astype(int))
        class_distribution = {str(i): int(c) for i, c in enumerate(class_counts) if c > 0}
        meta = {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "school_id": school_id,
            "period_filter": period,
            "samples": len(df),
            "feature_columns": FEATURE_COLUMNS,
            "feature_periods": sorted({f"{r['feature_year']}::{r['feature_period']}" for _, r in df.iterrows()}),
            "grade_model_mae": eval_metrics["grade_model_mae"],
            "grade_model_median_ae": eval_metrics["grade_model_median_ae"],
            "dropout_model_accuracy": eval_metrics["dropout_model_accuracy"],
            "dropout_model_roc_auc": eval_metrics["dropout_model_roc_auc"],
            "dropout_model_pr_auc": eval_metrics["dropout_model_pr_auc"],
            "dropout_precision_high_risk": eval_metrics["dropout_precision_high_risk"],
            "dropout_recall_high_risk": eval_metrics["dropout_recall_high_risk"],
            "dropout_confusion_matrix": eval_metrics["dropout_confusion_matrix"],
            "grade_feature_importances": grade_importances,
            "dropout_feature_importances": dropout_importances,
            "class_distribution": class_distribution,
            "cv_folds_grade": eval_metrics["cv_folds_grade"],
            "cv_folds_dropout": eval_metrics["cv_folds_dropout"],
            "evaluation_strategy": eval_metrics["evaluation_strategy"],
            "high_risk_threshold": HIGH_RISK_THRESHOLD,
            "medium_risk_threshold": MEDIUM_RISK_THRESHOLD,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        return {
            "status": "trained",
            "samples": len(df),
            "grade_model_mae": eval_metrics["grade_model_mae"],
            "grade_model_median_ae": eval_metrics["grade_model_median_ae"],
            "dropout_model_accuracy": eval_metrics["dropout_model_accuracy"],
            "dropout_model_roc_auc": eval_metrics["dropout_model_roc_auc"],
            "dropout_model_pr_auc": eval_metrics["dropout_model_pr_auc"],
            "dropout_precision_high_risk": eval_metrics["dropout_precision_high_risk"],
            "dropout_recall_high_risk": eval_metrics["dropout_recall_high_risk"],
            "dropout_confusion_matrix": eval_metrics["dropout_confusion_matrix"],
            "grade_feature_importances": grade_importances,
            "dropout_feature_importances": dropout_importances,
            "class_distribution": class_distribution,
            "cv_folds_grade": eval_metrics["cv_folds_grade"],
            "cv_folds_dropout": eval_metrics["cv_folds_dropout"],
            "evaluation_strategy": eval_metrics["evaluation_strategy"],
            "high_risk_threshold": HIGH_RISK_THRESHOLD,
            "medium_risk_threshold": MEDIUM_RISK_THRESHOLD,
        }

    def _load_models(self, *, school_id: int) -> tuple:
        """Load trained models from disk for one school."""
        import joblib

        grade_path, dropout_path, _ = self._get_model_paths(school_id)
        if not grade_path.exists() or not dropout_path.exists():
            raise FileNotFoundError("Models not trained yet. Call POST /api/ml/train first.")
        grade_model = joblib.load(grade_path)
        dropout_model = joblib.load(dropout_path)
        return grade_model, dropout_model

    def predict_student(self, *, current_user: CurrentUser, student_tz: str, period: str | None = None) -> dict:
        """Predict grade and dropout risk for a single student."""
        school_id = self._require_school_id(current_user)
        grade_model, dropout_model = self._load_models(school_id=school_id)

        df = self._build_feature_dataframe(current_user=current_user, period=period)
        student_row = df[df["student_tz"] == student_tz]
        if student_row.empty:
            raise ValueError(f"Student '{student_tz}' not found or has no grade data.")

        row = student_row.iloc[0]
        X = row[FEATURE_COLUMNS].values.reshape(1, -1)
        predicted_grade = round(float(grade_model.predict(X)[0]), 2)
        dropout_risk = round(float(self._positive_class_proba(dropout_model, X)[0]), 4)
        risk_level = _risk_level_from_score(dropout_risk)
        features = {col: _convert_value(row[col]) for col in FEATURE_COLUMNS}

        return {
            "student_tz": student_tz,
            "student_name": row["student_name"],
            "predicted_grade": predicted_grade,
            "dropout_risk": dropout_risk,
            "risk_level": risk_level,
            "features": features,
        }

    def _get_model_trained_at(self, *, school_id: int) -> str | None:
        """Get the trained_at timestamp from model metadata for cache keying."""
        _, _, meta_path = self._get_model_paths(school_id)
        if not meta_path.exists():
            return None
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        return meta.get("trained_at")

    def _compute_all_predictions(self, *, current_user: CurrentUser, period: str | None = None) -> list[dict]:
        """Compute predictions for all students (cached by period + model version + school)."""
        school_id = self._require_school_id(current_user)
        trained_at = self._get_model_trained_at(school_id=school_id)
        cache_key = (period, trained_at, school_id)
        if cache_key in _prediction_cache:
            return _prediction_cache[cache_key]

        grade_model, dropout_model = self._load_models(school_id=school_id)
        df = self._build_feature_dataframe(current_user=current_user, period=period)
        if df.empty:
            _prediction_cache[cache_key] = []
            return []

        X = df[FEATURE_COLUMNS].values
        predicted_grades = grade_model.predict(X)
        dropout_probas = self._positive_class_proba(dropout_model, X)

        all_predictions = []
        for i, (_, row) in enumerate(df.iterrows()):
            dropout_risk = round(float(dropout_probas[i]), 4)
            risk_level = _risk_level_from_score(dropout_risk)
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

    def predict_all(
        self,
        *,
        current_user: CurrentUser,
        period: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> dict:
        """Predict for all students with sorting and pagination."""
        all_predictions = self._compute_all_predictions(current_user=current_user, period=period)

        total = len(all_predictions)
        high_risk_count = sum(1 for p in all_predictions if p["risk_level"] == "high")
        medium_risk_count = sum(1 for p in all_predictions if p["risk_level"] == "medium")

        if sort_by and sort_by in ("student_name", "predicted_grade", "dropout_risk", "risk_level"):
            reverse = sort_order == "desc"
            all_predictions.sort(key=lambda p: (p.get(sort_by) is None, p.get(sort_by, "")), reverse=reverse)

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

    def get_status(self, *, current_user: CurrentUser | None = None) -> dict:
        """Get model status and metadata."""
        school_id = current_user.school_id if current_user else None
        if school_id is None:
            return {"trained": False}
        _, _, meta_path = self._get_model_paths(school_id)
        if not meta_path.exists():
            return {"trained": False}

        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

        return {
            "trained": True,
            "trained_at": meta.get("trained_at"),
            "samples": meta.get("samples"),
            "grade_model_mae": meta.get("grade_model_mae"),
            "grade_model_median_ae": meta.get("grade_model_median_ae"),
            "dropout_model_accuracy": meta.get("dropout_model_accuracy"),
            "dropout_model_roc_auc": meta.get("dropout_model_roc_auc"),
            "dropout_model_pr_auc": meta.get("dropout_model_pr_auc"),
            "dropout_precision_high_risk": meta.get("dropout_precision_high_risk"),
            "dropout_recall_high_risk": meta.get("dropout_recall_high_risk"),
            "evaluation_strategy": meta.get("evaluation_strategy"),
            "cv_folds_grade": meta.get("cv_folds_grade"),
            "cv_folds_dropout": meta.get("cv_folds_dropout"),
        }


def _convert_value(val):
    """Convert numpy types to Python native types."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    return val
