from collections import Counter

import numpy as np

from ..schemas.analytics import (
    GradeHistogramBin,
    TeacherClassDetail,
    TeacherDetailResponse,
    TeacherDetailStats,
    TeacherListItem,
    TeacherStatsResponse,
)

HISTOGRAM_BIN_SIZE = 5
HISTOGRAM_MAX_GRADE = 100


class TeacherDefaultView:
    """Default view presenter for Teacher data."""

    def render_list(self, data: list[dict]) -> list[TeacherListItem]:
        """Render list of teachers."""
        return sorted(
            [
                TeacherListItem(
                    id=str(item["id"]) if item["id"] else None,
                    name=item["name"],
                    student_count=item["student_count"],
                    average_grade=round(item["average_grade"], 1),
                    subjects=sorted(item["subjects"]),
                )
                for item in data
            ],
            key=lambda x: x.name,
        )

    def render_stats(self, data: dict) -> TeacherStatsResponse:
        """Render teacher stats."""
        grades = data["grades"]
        
        if not grades:
            return TeacherStatsResponse(
                teacher_name=data["teacher_name"],
                total_students=data["total_students"],
                average_grade=0.0,
                distribution={"fail": 0, "medium": 0, "good": 0, "excellent": 0},
                subjects=sorted(data["subjects"]),
            )

        grades_arr = np.array(grades)
        distribution = {
            "fail": int(np.sum(grades_arr < 55)),
            "medium": int(np.sum((grades_arr >= 55) & (grades_arr <= 75))),
            "good": int(np.sum((grades_arr > 75) & (grades_arr <= 90))),
            "excellent": int(np.sum(grades_arr > 90)),
        }

        avg_grade = float(np.mean(grades_arr))

        return TeacherStatsResponse(
            teacher_name=data["teacher_name"],
            total_students=data["total_students"],
            average_grade=round(avg_grade, 1),
            distribution=distribution,
            subjects=sorted(data["subjects"]),
        )

    def _build_grade_histogram(self, grades: list) -> list[GradeHistogramBin]:
        """Bin grades into a histogram with fixed-width bins."""
        binned = Counter(
            min(
                int(g.grade // HISTOGRAM_BIN_SIZE) * HISTOGRAM_BIN_SIZE,
                HISTOGRAM_MAX_GRADE - HISTOGRAM_BIN_SIZE,
            )
            for g in grades
        )

        return [
            GradeHistogramBin(grade=b, count=binned[b])
            for b in range(0, HISTOGRAM_MAX_GRADE, HISTOGRAM_BIN_SIZE)
        ]

    def render_detail(self, data: dict) -> TeacherDetailResponse:
        """Render teacher detail."""
        teacher = data["teacher"]
        stats = data["stats"]
        grades = data["grades"]
        classes_data = sorted(data["classes"], key=lambda x: x["name"])
        subjects = sorted({g.subject_name for g in grades if g.subject_name})

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
