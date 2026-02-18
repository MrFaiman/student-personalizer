from collections import Counter

from ..schemas.analytics import (
    GradeHistogramBin,
    TeacherClassDetail,
    TeacherDetailResponse,
    TeacherDetailStats,
    TeacherListItem,
    TeacherStatsResponse,
)
from .base import BaseView

HISTOGRAM_BIN_SIZE = 5
HISTOGRAM_MAX_GRADE = 100


class TeacherDefaultView(BaseView):
    """Default view presenter for Teacher data."""

    def render_list(self, data: list[dict]) -> list[TeacherListItem]:
        """Render list of teachers."""
        result = []
        for item in data:
            result.append(
                TeacherListItem(
                    id=str(item["id"]) if item["id"] else None,
                    name=item["name"],
                    student_count=item["student_count"],
                    average_grade=round(item["average_grade"], 1),
                    subjects=sorted(item["subjects"]),
                )
            )

        result.sort(key=lambda x: x.name)
        return result

    def render_stats(self, data: dict) -> TeacherStatsResponse:
        """Render teacher stats."""
        grades = data["grades"]

        distribution = {"fail": 0, "medium": 0, "good": 0, "excellent": 0}
        for grade in grades:
            if grade < 55:
                distribution["fail"] += 1
            elif grade <= 75:
                distribution["medium"] += 1
            elif grade <= 90:
                distribution["good"] += 1
            else:
                distribution["excellent"] += 1

        avg_grade = sum(grades) / len(grades) if grades else 0

        return TeacherStatsResponse(
            teacher_name=data["teacher_name"],
            total_students=data["total_students"],
            average_grade=round(avg_grade, 1),
            distribution=distribution,
            subjects=sorted(data["subjects"]),
        )

    def _build_grade_histogram(self, grades: list) -> list[GradeHistogramBin]:
        """Bin grades into a histogram with fixed-width bins."""
        binned = Counter()
        for g in grades:
            bin_start = min(
                int(g.grade // HISTOGRAM_BIN_SIZE) * HISTOGRAM_BIN_SIZE,
                HISTOGRAM_MAX_GRADE - HISTOGRAM_BIN_SIZE,
            )
            binned[bin_start] += 1

        return [
            GradeHistogramBin(grade=b, count=binned.get(b, 0))
            for b in range(0, HISTOGRAM_MAX_GRADE, HISTOGRAM_BIN_SIZE)
        ]

    def render_detail(self, data: dict) -> TeacherDetailResponse:
        """Render teacher detail."""
        teacher = data["teacher"]
        stats = data["stats"]
        grades = data["grades"]
        classes_data = sorted(data["classes"], key=lambda x: x["name"])
        subjects = sorted({g.subject for g in grades})

        return TeacherDetailResponse(
            id=str(teacher.id),
            name=teacher.name,
            stats=TeacherDetailStats(
                student_count=stats["student_count"],
                average_grade=stats["average_grade"],
                at_risk_count=stats["at_risk_count"],
                classes_count=stats["classes_count"],
            ),
            subjects=subjects,
            classes=[
                TeacherClassDetail(
                    id=c["id"],
                    name=c["name"],
                    student_count=c["student_count"],
                    average_grade=c["average_grade"],
                    at_risk_count=c["at_risk_count"],
                )
                for c in classes_data
            ],
            grade_histogram=self._build_grade_histogram(grades),
        )
