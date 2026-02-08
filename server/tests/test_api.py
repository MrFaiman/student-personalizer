"""
End-to-end API tests with pytest.

Run with: pytest tests/test_api.py -v
Requires server running: uv run src/main.py
"""

from pathlib import Path

import httpx
import pytest

BASE_URL = "http://localhost:3000"
DATA_DIR = Path(__file__).parent.parent.parent / "data"
PERIOD = "Test-Q1"


@pytest.fixture(scope="module")
def client():
    """HTTP client fixture."""
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        yield client


@pytest.fixture(scope="module", autouse=True)
def check_server(client):
    """Ensure server is running before tests."""
    try:
        response = client.get("/health")
        assert response.status_code == 200
    except httpx.ConnectError:
        pytest.skip("Server not running. Start with: uv run uvicorn src.main:app --reload")


class TestHealthCheck:
    """Basic health check tests."""

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestIngestion:
    """File ingestion tests."""

    def test_upload_grades_file(self, client):
        """Test uploading grades XLSX file."""
        grades_file = DATA_DIR / "avg_grades.xlsx"
        if not grades_file.exists():
            pytest.skip(f"Grades file not found: {grades_file}")

        with open(grades_file, "rb") as f:
            response = client.post(
                "/api/ingest/upload",
                files={"file": ("avg_grades.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                params={"file_type": "grades", "period": PERIOD},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "grades"
        assert data["rows_imported"] > 0
        print(f"Grades imported: {data['rows_imported']} rows, {data['students_created']} students")

    def test_upload_events_file(self, client):
        """Test uploading events/attendance XLSX file."""
        events_file = DATA_DIR / "events.xlsx"
        if not events_file.exists():
            pytest.skip(f"Events file not found: {events_file}")

        with open(events_file, "rb") as f:
            response = client.post(
                "/api/ingest/upload",
                files={"file": ("events.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                params={"file_type": "events", "period": PERIOD},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "events"
        assert data["rows_imported"] > 0
        print(f"Events imported: {data['rows_imported']} rows")

    def test_get_import_logs(self, client):
        """Test fetching import logs."""
        response = client.get("/api/ingest/logs")
        assert response.status_code == 200
        logs = response.json()
        assert isinstance(logs, list)
        print(f"Import logs: {len(logs)} entries")


class TestStudents:
    """Student endpoints tests."""

    def test_list_students(self, client):
        """Test listing students."""
        response = client.get("/api/students", params={"period": PERIOD})
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        print(f"Students listed: {len(data['items'])} of {data['total']}")

    def test_list_classes(self, client):
        """Test listing classes."""
        response = client.get("/api/students/classes", params={"period": PERIOD})
        assert response.status_code == 200
        classes = response.json()
        assert isinstance(classes, list)
        print(f"Classes: {len(classes)}")

    def test_dashboard_stats(self, client):
        """Test dashboard statistics."""
        response = client.get("/api/students/dashboard", params={"period": PERIOD})
        assert response.status_code == 200
        data = response.json()
        assert "total_students" in data
        assert "average_grade" in data
        assert "at_risk_count" in data
        print(f"Dashboard: {data['total_students']} students, avg: {data['average_grade']}, at-risk: {data['at_risk_count']}")


class TestAnalytics:
    """Analytics endpoints tests."""

    def test_kpis(self, client):
        """Test layer KPIs endpoint."""
        response = client.get("/api/analytics/kpis", params={"period": PERIOD})
        assert response.status_code == 200
        data = response.json()
        assert "layer_average" in data
        assert "avg_absences" in data
        assert "at_risk_students" in data
        assert "total_students" in data
        print(f"KPIs: avg={data['layer_average']}, at_risk={data['at_risk_students']}, total={data['total_students']}")

    def test_class_comparison(self, client):
        """Test class comparison endpoint."""
        response = client.get("/api/analytics/class-comparison", params={"period": PERIOD})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "class_name" in data[0]
            assert "grade" in data[0]
        print(f"Class comparison: {len(data)} classes")

    def test_metadata(self, client):
        """Test metadata endpoint."""
        response = client.get("/api/analytics/metadata")
        assert response.status_code == 200
        data = response.json()
        assert "periods" in data
        assert "grade_levels" in data
        assert "teachers" in data
        print(f"Metadata: {len(data['periods'])} periods, {len(data['grade_levels'])} levels, {len(data['teachers'])} teachers")

    def test_teachers_list(self, client):
        """Test teachers list endpoint."""
        response = client.get("/api/analytics/teachers", params={"period": PERIOD})
        assert response.status_code == 200
        teachers = response.json()
        assert isinstance(teachers, list)
        print(f"Teachers: {len(teachers)}")


class TestAnalyticsWithData:
    """Analytics tests that require existing data."""

    @pytest.fixture
    def first_class(self, client):
        """Get first available class."""
        response = client.get("/api/students/classes", params={"period": PERIOD})
        classes = response.json()
        if not classes:
            pytest.skip("No classes available")
        return classes[0]["class_name"]

    @pytest.fixture
    def first_teacher(self, client):
        """Get first available teacher."""
        response = client.get("/api/analytics/teachers", params={"period": PERIOD})
        teachers = response.json()
        if not teachers:
            pytest.skip("No teachers available")
        return teachers[0]

    @pytest.fixture
    def first_student(self, client):
        """Get first available student."""
        response = client.get("/api/students", params={"period": PERIOD, "page_size": 1})
        data = response.json()
        if not data["items"]:
            pytest.skip("No students available")
        return data["items"][0]["student_tz"]

    def test_class_heatmap(self, client, first_class):
        """Test class heatmap endpoint."""
        response = client.get(f"/api/analytics/class/{first_class}/heatmap", params={"period": PERIOD})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "student_name" in data[0]
        print(f"Heatmap for {first_class}: {len(data)} students")

    def test_class_rankings(self, client, first_class):
        """Test class rankings endpoint."""
        response = client.get(f"/api/analytics/class/{first_class}/rankings", params={"period": PERIOD})
        assert response.status_code == 200
        data = response.json()
        assert "top" in data
        assert "bottom" in data
        print(f"Rankings for {first_class}: top={len(data['top'])}, bottom={len(data['bottom'])}")

    def test_teacher_stats(self, client, first_teacher):
        """Test teacher stats endpoint."""
        response = client.get(f"/api/analytics/teacher/{first_teacher}/stats", params={"period": PERIOD})
        assert response.status_code == 200
        data = response.json()
        assert "distribution" in data
        assert "total_students" in data
        assert "average_grade" in data
        print(f"Teacher {first_teacher}: {data['total_students']} students, avg={data['average_grade']}")

    def test_student_radar(self, client, first_student):
        """Test student radar endpoint."""
        response = client.get(f"/api/analytics/student/{first_student}/radar", params={"period": PERIOD})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "subject" in data[0]
            assert "grade" in data[0]
        print(f"Radar for {first_student}: {len(data)} subjects")

    def test_get_student_details(self, client, first_student):
        """Test getting specific student details."""
        response = client.get(f"/api/students/{first_student}", params={"period": PERIOD})
        assert response.status_code == 200
        data = response.json()
        assert data["student_tz"] == first_student
        assert "average_grade" in data
        assert "is_at_risk" in data
        print(f"Student {data['student_name']}: avg={data['average_grade']}, at_risk={data['is_at_risk']}")

    def test_get_student_grades(self, client, first_student):
        """Test getting student grades."""
        response = client.get(f"/api/students/{first_student}/grades", params={"period": PERIOD})
        assert response.status_code == 200
        grades = response.json()
        assert isinstance(grades, list)
        print(f"Student grades: {len(grades)} records")

    def test_get_student_attendance(self, client, first_student):
        """Test getting student attendance."""
        response = client.get(f"/api/students/{first_student}/attendance", params={"period": PERIOD})
        assert response.status_code == 200
        attendance = response.json()
        assert isinstance(attendance, list)
        print(f"Student attendance: {len(attendance)} records")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
