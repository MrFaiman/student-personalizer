import pytest

from src.services.analytics import AnalyticsService
from src.services.teachers import TeacherService


class TestDashboardAnalytics:

    def test_layer_kpis(self, seeded_session):
        service = AnalyticsService(seeded_session)
        kpis = service.get_layer_kpis(period="Q1")
        
        assert "layer_average" in kpis
        assert "avg_absences" in kpis
        assert "at_risk_count" in kpis
        assert kpis["total_students"] == 8

    def test_class_comparison(self, seeded_session):
        service = AnalyticsService(seeded_session)
        results = service.get_class_comparison(period="Q1")
        
        assert len(results) == 2 # Test-10A, Test-10B
        assert results[0]["student_count"] == 4
        assert results[1]["student_count"] == 4

    def test_teacher_stats(self, seeded_session):
        """Test teacher statistics using TeacherService (raw data)."""
        service = TeacherService(seeded_session)

        stats = service.get_teacher_stats(teacher_name="Teacher-1", period="Q1")

        assert stats["teacher_name"] == "Teacher-1"
        assert stats["total_students"] == 8 # All 8 students have Subject-1/Teacher-1
        assert "grades" in stats
        assert isinstance(stats["grades"], list)
        assert len(stats["grades"]) > 0
        assert isinstance(stats["subjects"], set)

    def test_student_radar(self, seeded_session):
        service = AnalyticsService(seeded_session)
        # S001 has subjects Subj0..Subj4
        radar = service.get_student_radar("S001", period="Q1")
        assert len(radar) == 5
        assert radar["Subject-1"] == pytest.approx(90.0)

    def test_period_comparison(self, seeded_session):
        # We only seeded Q1, so comparing Q1 vs Q1 should have identical grade lists
        service = AnalyticsService(seeded_session)
        comp = service.get_period_comparison(
            period_a="Q1",
            period_b="Q1",
            comparison_type="class"
        )
        assert len(comp["data"]) == 2
        assert "grades_a" in comp["data"][0]
        assert "grades_b" in comp["data"][0]
        assert comp["data"][0]["grades_a"] == comp["data"][0]["grades_b"]

    def test_red_student_segmentation(self, seeded_session):
        service = AnalyticsService(seeded_session)
        seg = service.get_red_student_segmentation(period="Q1")
        
        assert seg["total_red_students"] > 0
        assert "by_class" in seg
        assert "by_subject" in seg

    def test_get_red_student_list(self, seeded_session):
        service = AnalyticsService(seeded_session)
        red_list = service.get_red_student_list(period="Q1")
        
        assert red_list["total"] > 0
        assert len(red_list["students"]) > 0
        first = red_list["students"][0]
        assert "student_name" in first
        assert "average_grade" in first
        assert first["average_grade"] < 55 # Threshold from constants