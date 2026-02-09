"""Tests for the ML prediction service and API endpoints."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.database import get_session
from src.main import app
from src.models import AttendanceRecord, Class, Grade, Student
from src.services.ml import FEATURE_COLUMNS, MLService

# Student profiles used for seeding: (tz, name, grades, absence, late, dist, neg, pos)
PROFILES = [
    ("S001", "Alice", [90, 85, 80, 60, 50], 2, 1, 0, 3, 5),   # declining
    ("S002", "Bob", [60, 65, 70, 72, 73], 1, 0, 0, 1, 8),     # improving
    ("S003", "Carol", [40, 42, 38, 45, 41], 8, 3, 2, 13, 0),   # at-risk
    ("S004", "Dave", [88, 90, 92, 91, 93], 0, 0, 0, 0, 10),    # excellent
    ("S005", "Eve", [55, 50, 48, 52, 45], 5, 2, 1, 8, 1),      # borderline
    ("S006", "Frank", [70, 72, 68, 74, 71], 3, 1, 0, 4, 3),    # stable mid
    ("S007", "Grace", [95, 93, 96, 94, 97], 0, 0, 0, 0, 12),   # top
    ("S008", "Hank", [30, 35, 25, 40, 28], 10, 4, 3, 17, 0),   # dropout risk
]


def _create_engine():
    """Create an in-memory SQLite engine with StaticPool for connection sharing."""
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _seed_db(engine):
    """Populate the DB with test students, grades, and attendance."""
    with Session(engine) as s:
        s.add(Class(class_name="Test-10A", grade_level="10"))
        s.flush()

        for tz, name, grades, absence, late, dist, neg, pos in PROFILES:
            s.add(Student(student_tz=tz, student_name=name, class_name="Test-10A"))
            s.flush()

            for i, g in enumerate(grades):
                s.add(Grade(student_tz=tz, subject=f"Subj{i}", grade=float(g), period="Q1"))

            s.add(AttendanceRecord(
                student_tz=tz,
                absence=absence,
                absence_justified=1,
                late=late,
                disturbance=dist,
                total_absences=absence + 1,
                total_negative_events=neg,
                total_positive_events=pos,
                period="Q1",
            ))

        s.commit()


@pytest.fixture(scope="module")
def seeded_engine():
    """In-memory SQLite engine with 8 seeded students."""
    eng = _create_engine()
    SQLModel.metadata.create_all(eng)
    _seed_db(eng)
    return eng


@pytest.fixture()
def seeded_session(seeded_engine):
    """Session bound to the seeded engine."""
    with Session(seeded_engine) as s:
        yield s


@pytest.fixture()
def empty_session():
    """Session bound to an empty DB (tables exist, no rows)."""
    eng = _create_engine()
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        yield s


@pytest.fixture(autouse=True)
def _patch_model_paths(monkeypatch, tmp_path):
    """Redirect model storage to a temp dir for every test."""
    import src.services.ml as ml_mod
    monkeypatch.setattr(ml_mod, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(ml_mod, "GRADE_MODEL_PATH", tmp_path / "grade_predictor.joblib")
    monkeypatch.setattr(ml_mod, "DROPOUT_MODEL_PATH", tmp_path / "dropout_classifier.joblib")
    monkeypatch.setattr(ml_mod, "META_PATH", tmp_path / "model_meta.json")


# ---------------------------------------------------------------------------
# Unit tests: feature engineering
# ---------------------------------------------------------------------------

class TestBuildFeatures:
    """Tests for _build_feature_dataframe."""

    def test_returns_dataframe_with_all_feature_columns(self, seeded_session):
        service = MLService(seeded_session)
        df = service._build_feature_dataframe(period="Q1")

        assert len(df) == 8
        for col in FEATURE_COLUMNS:
            assert col in df.columns, f"Missing feature column: {col}"

    def test_trend_slope_declining_student(self, seeded_session):
        """Alice [90,85,80,60,50] should have a negative slope."""
        service = MLService(seeded_session)
        df = service._build_feature_dataframe(period="Q1")
        alice = df[df["student_tz"] == "S001"].iloc[0]
        assert alice["grade_trend_slope"] < 0

    def test_trend_slope_improving_student(self, seeded_session):
        """Bob [60,65,70,72,73] should have a positive slope."""
        service = MLService(seeded_session)
        df = service._build_feature_dataframe(period="Q1")
        bob = df[df["student_tz"] == "S002"].iloc[0]
        assert bob["grade_trend_slope"] > 0

    def test_trend_slope_distinguishes_same_average(self, seeded_session):
        """Declining Alice vs improving Bob: slopes have opposite signs despite similar averages."""
        service = MLService(seeded_session)
        df = service._build_feature_dataframe(period="Q1")
        alice_slope = df[df["student_tz"] == "S001"].iloc[0]["grade_trend_slope"]
        bob_slope = df[df["student_tz"] == "S002"].iloc[0]["grade_trend_slope"]
        assert alice_slope < 0 < bob_slope

    def test_empty_for_missing_period(self, seeded_session):
        service = MLService(seeded_session)
        df = service._build_feature_dataframe(period="NonExistent")
        assert df.empty

    def test_grade_stats_correct(self, seeded_session):
        """Verify average, min, max, failing count for Carol [40,42,38,45,41]."""
        service = MLService(seeded_session)
        df = service._build_feature_dataframe(period="Q1")
        carol = df[df["student_tz"] == "S003"].iloc[0]

        assert carol["average_grade"] == pytest.approx(41.2, abs=0.1)
        assert carol["min_grade"] == 38.0
        assert carol["max_grade"] == 45.0
        assert carol["failing_subjects"] == 5  # all below 55
        assert carol["num_subjects"] == 5


# ---------------------------------------------------------------------------
# Unit tests: training
# ---------------------------------------------------------------------------

class TestTrain:
    """Tests for training the model."""

    def test_train_returns_metrics(self, seeded_session):
        service = MLService(seeded_session)
        result = service.train(period="Q1")

        assert result["status"] == "trained"
        assert result["samples"] == 8
        assert result["grade_model_mae"] >= 0
        assert 0 <= result["dropout_model_accuracy"] <= 1
        assert set(result["grade_feature_importances"].keys()) == set(FEATURE_COLUMNS)
        assert set(result["dropout_feature_importances"].keys()) == set(FEATURE_COLUMNS)

    def test_train_saves_model_files(self, seeded_session):
        import src.services.ml as ml_mod

        service = MLService(seeded_session)
        service.train(period="Q1")

        assert ml_mod.GRADE_MODEL_PATH.exists()
        assert ml_mod.DROPOUT_MODEL_PATH.exists()
        assert ml_mod.META_PATH.exists()

        with open(ml_mod.META_PATH) as f:
            meta = json.load(f)
        assert "trained_at" in meta
        assert meta["samples"] == 8

    def test_train_fails_with_insufficient_data(self, empty_session):
        """Training with 0 students should raise ValueError."""
        service = MLService(empty_session)
        with pytest.raises(ValueError, match="Not enough data"):
            service.train(period="Q1")


# ---------------------------------------------------------------------------
# Unit tests: prediction
# ---------------------------------------------------------------------------

class TestPredict:
    """Tests for prediction methods."""

    @pytest.fixture(autouse=True)
    def _train_first(self, seeded_session):
        """Train models before each prediction test."""
        MLService(seeded_session).train(period="Q1")

    def test_predict_student_returns_expected_shape(self, seeded_session):
        service = MLService(seeded_session)
        result = service.predict_student(student_tz="S001", period="Q1")

        assert result["student_tz"] == "S001"
        assert result["student_name"] == "Alice"
        assert 0 <= result["predicted_grade"] <= 100
        assert 0 <= result["dropout_risk"] <= 1
        assert result["risk_level"] in ("low", "medium", "high")
        assert set(result["features"].keys()) == set(FEATURE_COLUMNS)

    def test_predict_unknown_student_raises(self, seeded_session):
        service = MLService(seeded_session)
        with pytest.raises(ValueError, match="not found"):
            service.predict_student(student_tz="UNKNOWN", period="Q1")

    def test_predict_all_returns_all_students(self, seeded_session):
        service = MLService(seeded_session)
        result = service.predict_all(period="Q1")

        assert result["model_trained"] is True
        assert result["total_students"] == 8
        assert len(result["predictions"]) == 8

        tzs = {p["student_tz"] for p in result["predictions"]}
        assert tzs == {"S001", "S002", "S003", "S004", "S005", "S006", "S007", "S008"}

    def test_predict_all_empty_period(self, seeded_session):
        service = MLService(seeded_session)
        result = service.predict_all(period="NonExistent")
        assert result["total_students"] == 0
        assert result["predictions"] == []

    def test_predict_before_training_raises(self, seeded_session):
        """Remove model files and verify FileNotFoundError."""
        import src.services.ml as ml_mod
        ml_mod.GRADE_MODEL_PATH.unlink(missing_ok=True)
        ml_mod.DROPOUT_MODEL_PATH.unlink(missing_ok=True)

        service = MLService(seeded_session)
        with pytest.raises(FileNotFoundError, match="not trained"):
            service.predict_student(student_tz="S001", period="Q1")


# ---------------------------------------------------------------------------
# Unit tests: status
# ---------------------------------------------------------------------------

class TestGetStatus:
    """Tests for model status."""

    def test_status_untrained(self, seeded_session):
        service = MLService(seeded_session)
        status = service.get_status()
        assert status["trained"] is False

    def test_status_after_training(self, seeded_session):
        service = MLService(seeded_session)
        service.train(period="Q1")
        status = service.get_status()

        assert status["trained"] is True
        assert status["trained_at"] is not None
        assert status["samples"] == 8
        assert status["grade_model_mae"] >= 0
        assert 0 <= status["dropout_model_accuracy"] <= 1


# ---------------------------------------------------------------------------
# API endpoint integration tests (TestClient, no running server needed)
# ---------------------------------------------------------------------------

class TestMLEndpoints:
    """Integration tests for the ML API router via TestClient."""

    @pytest.fixture()
    def client(self, seeded_engine):
        """TestClient with dependency override pointing to the seeded DB."""
        def override_session():
            with Session(seeded_engine) as s:
                yield s

        app.dependency_overrides[get_session] = override_session
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

    def test_status_untrained(self, client):
        resp = client.get("/api/ml/status")
        assert resp.status_code == 200
        assert resp.json()["trained"] is False

    def test_train_endpoint(self, client):
        resp = client.post("/api/ml/train", params={"period": "Q1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "trained"
        assert data["samples"] == 8
        assert "grade_feature_importances" in data
        assert "grade_trend_slope" in data["grade_feature_importances"]

    def test_predict_single_after_train(self, client):
        client.post("/api/ml/train", params={"period": "Q1"})

        resp = client.get("/api/ml/predict/S004", params={"period": "Q1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["student_tz"] == "S004"
        assert data["risk_level"] in ("low", "medium", "high")
        assert "features" in data
        assert "grade_trend_slope" in data["features"]

    def test_predict_unknown_student_404(self, client):
        client.post("/api/ml/train", params={"period": "Q1"})
        resp = client.get("/api/ml/predict/UNKNOWN", params={"period": "Q1"})
        assert resp.status_code == 404

    def test_predict_before_train_400(self, client):
        resp = client.get("/api/ml/predict/S001", params={"period": "Q1"})
        assert resp.status_code == 400

    def test_batch_predict_after_train(self, client):
        client.post("/api/ml/train", params={"period": "Q1"})

        resp = client.get("/api/ml/predict", params={"period": "Q1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_trained"] is True
        assert data["total_students"] == 8
        assert len(data["predictions"]) == 8

    def test_status_after_train(self, client):
        client.post("/api/ml/train", params={"period": "Q1"})

        resp = client.get("/api/ml/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trained"] is True
        assert data["samples"] == 8

    def test_train_insufficient_data_400(self):
        """With empty DB, training should return 400."""
        empty_eng = _create_engine()
        SQLModel.metadata.create_all(empty_eng)

        def override_empty():
            with Session(empty_eng) as s:
                yield s

        app.dependency_overrides[get_session] = override_empty
        with TestClient(app) as c:
            resp = c.post("/api/ml/train", params={"period": "Q1"})
        app.dependency_overrides.clear()

        assert resp.status_code == 400
        assert "Not enough data" in resp.json()["detail"]
