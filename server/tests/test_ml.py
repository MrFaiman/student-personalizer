"""Tests for the ML prediction service and API endpoints."""

import json
import os
import uuid

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-32chars!!")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

import src.services.ml as ml_mod
from src.auth.current_user import CurrentUser
from src.auth.models import UserRole
from src.auth.schemas import CreateUserRequest
from src.auth.service import AuthService
from src.database import get_session
from src.main import app
from src.models import AttendanceRecord, Grade
from src.services.ml import FEATURE_COLUMNS, MLService

_ADMIN_USER = CurrentUser(
    user_id=uuid.uuid4(),
    email="admin@test.local",
    display_name="Test Admin",
    role=UserRole.system_admin,
    is_active=True,
    must_change_password=False,
    mfa_enabled=False,
    mfa_verified=False,
    identity_provider="local",
    external_id=None,
    school_id=100,
    school_name=None,
    session_jti="test-jti",
)


@pytest.fixture(autouse=True)
def isolate_ml_artifacts(tmp_path, monkeypatch):
    """Use per-test artifact paths so checked-in model files do not leak into tests."""
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(ml_mod, "MODELS_DIR", models_dir)
    ml_mod._prediction_cache.clear()


@pytest.fixture(scope="module", autouse=True)
def seed_q2_period(seeded_engine):
    """Add a second period so training can learn future outcomes (Q1 -> Q2)."""
    with Session(seeded_engine) as s:
        existing_q2 = s.exec(select(Grade).where(Grade.school_id == 100, Grade.period == "Q2")).first()
        if existing_q2 is not None:
            return

        deltas = {
            "S001": -8,
            "S002": 6,
            "S003": -2,
            "S004": 2,
            "S005": -3,
            "S006": 1,
            "S007": 1,
            "S008": 4,
        }
        q1_grades = s.exec(select(Grade).where(Grade.school_id == 100, Grade.period == "Q1")).all()
        for g in q1_grades:
            adjusted_grade = float(max(0, min(100, g.grade + deltas.get(g.student_tz, 0))))
            s.add(
                Grade(
                    student_tz=g.student_tz,
                    school_id=g.school_id,
                    subject_name=g.subject_name,
                    subject_id=g.subject_id,
                    teacher_name=g.teacher_name,
                    teacher_id=g.teacher_id,
                    grade=adjusted_grade,
                    period="Q2",
                    year=g.year or "",
                )
            )

        q1_attendance = s.exec(select(AttendanceRecord).where(AttendanceRecord.school_id == 100, AttendanceRecord.period == "Q1")).all()
        for a in q1_attendance:
            abs_delta = 2 if a.student_tz in {"S003", "S005", "S008"} else 0
            neg_delta = 3 if a.student_tz in {"S003", "S008"} else 0
            pos_delta = -2 if a.student_tz in {"S003", "S008"} else 1
            s.add(
                AttendanceRecord(
                    student_tz=a.student_tz,
                    school_id=a.school_id,
                    lessons_reported=a.lessons_reported,
                    absence=max(0, a.absence + abs_delta),
                    absence_justified=max(0, a.absence_justified),
                    late=max(0, a.late + (1 if a.student_tz in {"S003", "S008"} else 0)),
                    disturbance=max(0, a.disturbance + (1 if a.student_tz in {"S003", "S008"} else 0)),
                    total_absences=max(0, a.total_absences + abs_delta),
                    attendance=max(0, a.attendance - abs_delta),
                    total_negative_events=max(0, a.total_negative_events + neg_delta),
                    total_positive_events=max(0, a.total_positive_events + pos_delta),
                    period="Q2",
                    year=a.year or "",
                )
            )
        s.commit()


class TestBuildFeatures:
    """Tests for _build_feature_dataframe."""

    def test_returns_dataframe_with_all_feature_columns(self, seeded_session):
        service = MLService(seeded_session)
        df = service._build_feature_dataframe(current_user=_ADMIN_USER, period="Q1")

        assert len(df) == 8
        for col in FEATURE_COLUMNS:
            assert col in df.columns, f"Missing feature column: {col}"

    def test_trend_slope_declining_student(self, seeded_session):
        """Alice should show a negative period-over-period slope at Q2."""
        service = MLService(seeded_session)
        df = service._build_feature_dataframe(current_user=_ADMIN_USER, period="Q2")
        alice = df[df["student_tz"] == "S001"].iloc[0]
        assert alice["grade_trend_slope"] < 0

    def test_trend_slope_improving_student(self, seeded_session):
        """Bob should show a positive period-over-period slope at Q2."""
        service = MLService(seeded_session)
        df = service._build_feature_dataframe(current_user=_ADMIN_USER, period="Q2")
        bob = df[df["student_tz"] == "S002"].iloc[0]
        assert bob["grade_trend_slope"] > 0

    def test_trend_slope_distinguishes_same_average(self, seeded_session):
        """Declining Alice vs improving Bob: Q2 slopes have opposite signs."""
        service = MLService(seeded_session)
        df = service._build_feature_dataframe(current_user=_ADMIN_USER, period="Q2")
        alice_slope = df[df["student_tz"] == "S001"].iloc[0]["grade_trend_slope"]
        bob_slope = df[df["student_tz"] == "S002"].iloc[0]["grade_trend_slope"]
        assert alice_slope < 0 < bob_slope

    def test_empty_for_missing_period(self, seeded_session):
        service = MLService(seeded_session)
        df = service._build_feature_dataframe(current_user=_ADMIN_USER, period="NonExistent")
        assert df.empty

    def test_grade_stats_correct(self, seeded_session):
        """Verify average, min, max, failing count for Carol [40,42,38,45,41]."""
        service = MLService(seeded_session)
        df = service._build_feature_dataframe(current_user=_ADMIN_USER, period="Q1")
        carol = df[df["student_tz"] == "S003"].iloc[0]

        assert carol["average_grade"] == pytest.approx(41.2, abs=0.1)
        assert carol["min_grade"] == 38.0
        assert carol["max_grade"] == 45.0
        assert carol["failing_subjects"] == 5  # all below 55
        assert carol["num_subjects"] == 5


class TestTrain:
    """Tests for training the model."""

    def test_train_returns_metrics(self, seeded_session):
        service = MLService(seeded_session)
        result = service.train(current_user=_ADMIN_USER, period="Q1")

        assert result["status"] == "trained"
        assert result["samples"] == 8
        assert result["grade_model_mae"] >= 0
        assert 0 <= result["dropout_model_accuracy"] <= 1
        assert result["evaluation_strategy"] in ("temporal_holdout", "cross_validation")
        assert set(result["grade_feature_importances"].keys()) == set(FEATURE_COLUMNS)
        assert set(result["dropout_feature_importances"].keys()) == set(FEATURE_COLUMNS)

    def test_train_saves_model_files(self, seeded_session):
        service = MLService(seeded_session)
        service.train(current_user=_ADMIN_USER, period="Q1")
        grade_path, dropout_path, meta_path = service._get_model_paths(_ADMIN_USER.school_id or 100)

        assert grade_path.exists()
        assert dropout_path.exists()
        assert meta_path.exists()

        with open(meta_path) as f:
            meta = json.load(f)
        assert "trained_at" in meta
        assert meta["samples"] == 8
        assert meta["evaluation_strategy"] in ("temporal_holdout", "cross_validation")
        assert meta["school_id"] == 100

    def test_school_scoped_artifact_paths(self, seeded_session):
        service = MLService(seeded_session)
        service.train(current_user=_ADMIN_USER, period="Q1")
        school_100_paths = service._get_model_paths(100)
        school_101_paths = service._get_model_paths(101)
        assert school_100_paths != school_101_paths
        assert school_100_paths[0].exists()
        assert school_100_paths[1].exists()

    def test_train_fails_with_insufficient_data(self, empty_session):
        """Training with 0 students should raise ValueError."""
        service = MLService(empty_session)
        with pytest.raises(ValueError, match="Not enough data"):
            service.train(current_user=_ADMIN_USER, period="Q1")

    def test_leakage_guard_raises_for_overlapping_target(self, seeded_session):
        service = MLService(seeded_session)
        with pytest.raises(ValueError, match="Target leakage detected"):
            service._assert_no_target_leakage(
                feature_columns=["average_grade", "late"],
                target_columns=["target_next_average_grade", "average_grade"],
            )


class TestPredict:
    """Tests for prediction methods."""

    @pytest.fixture(autouse=True)
    def _train_first(self, seeded_session):
        """Train models before each prediction test."""
        MLService(seeded_session).train(current_user=_ADMIN_USER, period="Q1")

    def test_predict_student_returns_expected_shape(self, seeded_session):
        service = MLService(seeded_session)
        result = service.predict_student(current_user=_ADMIN_USER, student_tz="S001", period="Q1")

        assert result["student_tz"] == "S001"
        assert result["student_name"] == "Alice"
        assert 0 <= result["predicted_grade"] <= 100
        assert 0 <= result["dropout_risk"] <= 1
        assert result["risk_level"] in ("low", "medium", "high")
        assert set(result["features"].keys()) == set(FEATURE_COLUMNS)

    def test_predict_unknown_student_raises(self, seeded_session):
        service = MLService(seeded_session)
        with pytest.raises(ValueError, match="not found"):
            service.predict_student(current_user=_ADMIN_USER, student_tz="UNKNOWN", period="Q1")

    def test_predict_all_returns_all_students(self, seeded_session):
        service = MLService(seeded_session)
        result = service.predict_all(current_user=_ADMIN_USER, period="Q1")

        assert result["model_trained"] is True
        assert result["total_students"] == 8
        assert len(result["predictions"]) == 8

        tzs = {p["student_tz"] for p in result["predictions"]}
        assert tzs == {"S001", "S002", "S003", "S004", "S005", "S006", "S007", "S008"}

    def test_predict_all_empty_period(self, seeded_session):
        service = MLService(seeded_session)
        result = service.predict_all(current_user=_ADMIN_USER, period="NonExistent")
        assert result["total_students"] == 0
        assert result["predictions"] == []

    def test_predict_before_training_raises(self, seeded_session):
        """Remove model files and verify FileNotFoundError."""
        service = MLService(seeded_session)
        grade_path, dropout_path, _ = service._get_model_paths(_ADMIN_USER.school_id or 100)
        grade_path.unlink(missing_ok=True)
        dropout_path.unlink(missing_ok=True)

        with pytest.raises(FileNotFoundError, match="not trained"):
            service.predict_student(current_user=_ADMIN_USER, student_tz="S001", period="Q1")

    def test_calibrated_probabilities_and_threshold_boundaries(self, seeded_session):
        service = MLService(seeded_session)
        service.train(current_user=_ADMIN_USER, period="Q1")
        _, dropout_model = service._load_models(school_id=_ADMIN_USER.school_id or 100)
        assert hasattr(dropout_model, "predict_proba")
        assert ml_mod._risk_level_from_score(0.7) == "medium"
        assert ml_mod._risk_level_from_score(0.3) == "low"
        assert ml_mod._risk_level_from_score(0.71) == "high"


class TestGetStatus:
    """Tests for model status."""

    def test_status_untrained(self, seeded_session):
        service = MLService(seeded_session)
        status = service.get_status(current_user=_ADMIN_USER)
        assert status["trained"] is False

    def test_status_after_training(self, seeded_session):
        service = MLService(seeded_session)
        service.train(current_user=_ADMIN_USER, period="Q1")
        status = service.get_status(current_user=_ADMIN_USER)

        assert status["trained"] is True
        assert status["trained_at"] is not None
        assert status["samples"] == 8
        assert status["grade_model_mae"] >= 0
        assert 0 <= status["dropout_model_accuracy"] <= 1
        assert status.get("evaluation_strategy") in ("temporal_holdout", "cross_validation")


class TestMLEndpoints:
    """Integration tests for the ML API router via TestClient."""

    @pytest.fixture()
    def client(self, seeded_engine):
        """TestClient with dependency overrides: seeded DB."""
        def override_session():
            with Session(seeded_engine) as s:
                yield s

        app.dependency_overrides[get_session] = override_session
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

    @pytest.fixture()
    def auth_headers(self, seeded_engine, client):
        """Create an admin user and return Authorization headers."""
        with Session(seeded_engine) as s:
            svc = AuthService(s)
            # Ensure an admin user exists
            try:
                svc.create_user(
                    CreateUserRequest(
                        email="ml_admin@test.com",
                        password="MlAdmin@1234!",
                        display_name="ML Admin",
                        role=UserRole.system_admin,
                        school_id=100,
                        school_name="Test School",
                    )
                )
            except Exception:
                # user may already exist if fixture is reused
                pass
            svc.ensure_rbac_seed()

        resp = client.post("/api/auth/login", json={"email": "ml_admin@test.com", "password": "MlAdmin@1234!"})
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_status_untrained(self, client, auth_headers):
        resp = client.get("/api/ml/status", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["trained"] is False

    def test_train_endpoint(self, client, auth_headers):
        resp = client.post("/api/ml/train", params={"period": "Q1"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "trained"
        assert data["samples"] == 8
        assert "grade_feature_importances" in data
        assert "grade_trend_slope" in data["grade_feature_importances"]

    def test_predict_single_after_train(self, client, auth_headers):
        client.post("/api/ml/train", params={"period": "Q1"}, headers=auth_headers)

        resp = client.get("/api/ml/predict/S004", params={"period": "Q1"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["student_tz"] == "S004"
        assert data["risk_level"] in ("low", "medium", "high")
        assert "features" in data
        assert "grade_trend_slope" in data["features"]

    def test_predict_unknown_student_404(self, client, auth_headers):
        client.post("/api/ml/train", params={"period": "Q1"}, headers=auth_headers)
        resp = client.get("/api/ml/predict/UNKNOWN", params={"period": "Q1"}, headers=auth_headers)
        assert resp.status_code == 404

    def test_predict_before_train_400(self, client, auth_headers):
        resp = client.get("/api/ml/predict/S001", params={"period": "Q1"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_batch_predict_after_train(self, client, auth_headers):
        client.post("/api/ml/train", params={"period": "Q1"}, headers=auth_headers)

        resp = client.get("/api/ml/predict", params={"period": "Q1"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_trained"] is True
        assert data["total_students"] == 8
        assert len(data["predictions"]) == 8

    def test_status_after_train(self, client, auth_headers):
        client.post("/api/ml/train", params={"period": "Q1"}, headers=auth_headers)

        resp = client.get("/api/ml/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["trained"] is True
        assert data["samples"] == 8

    def test_train_insufficient_data_400(self):
        """With empty DB, training should return 400."""
        """With empty DB, training should return 400."""
        from sqlalchemy.pool import StaticPool
        empty_eng = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(empty_eng)

        def override_empty():
            with Session(empty_eng) as s:
                yield s

        app.dependency_overrides[get_session] = override_empty
        with TestClient(app) as c:
            # create admin user and get token
            with Session(empty_eng) as s:
                svc = AuthService(s)
                svc.create_user(
                    CreateUserRequest(
                        email="ml_empty_admin@test.com",
                        password="MlEmptyAdmin@1234!",
                        display_name="ML Admin",
                        role=UserRole.system_admin,
                        school_id=100,
                        school_name="Test School",
                    )
                )
                svc.ensure_rbac_seed()
            login = c.post("/api/auth/login", json={"email": "ml_empty_admin@test.com", "password": "MlEmptyAdmin@1234!"})
            token = login.json()["access_token"]
            resp = c.post("/api/ml/train", params={"period": "Q1"}, headers={"Authorization": f"Bearer {token}"})
        app.dependency_overrides.clear()

        assert resp.status_code == 400
        assert "Not enough data" in resp.json()["detail"]
