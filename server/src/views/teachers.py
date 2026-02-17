from ..schemas.analytics import (
    TeacherDetailResponse,
    TeacherDetailStats,
    TeacherClassDetail,
    TeacherListItem,
    TeacherStatsResponse,
)


class TeacherDefaultView:
    """Default view presenter for Teacher data."""

    def render_list(self, data: list[dict]) -> list[TeacherListItem]:
        """Render list of teachers with pre-calculated summary stats."""
        result = []
        for item in data:
            result.append(
                TeacherListItem(
                    id=str(item["id"]) if item["id"] else None,
                    name=item["name"],
                    student_count=item["student_count"],
                    average_grade=item["average_grade"],
                    subjects=item["subjects"],
                )
            )

        result.sort(key=lambda x: x.name)
        return result

    def render_stats(self, data: dict) -> TeacherStatsResponse:
        """Render teacher stats response from pre-calculated data."""
        return TeacherStatsResponse(
            teacher_name=data["teacher_name"],
            total_students=data["total_students"],
            average_grade=data["average_grade"],
            distribution=data["distribution"],
            subjects=data["subjects"],
        )

    def render_detail(self, data: dict) -> TeacherDetailResponse:
        """Render teacher detail response from pre-calculated data."""
        teacher = data["teacher"]
        stats = data["stats"]

        return TeacherDetailResponse(
            id=str(teacher.id),
            name=teacher.name,
            stats=TeacherDetailStats(
                student_count=stats["student_count"],
                average_grade=stats["average_grade"],
                at_risk_count=stats["at_risk_count"],
                classes_count=stats["classes_count"],
            ),
            subjects=data["subjects"],
            classes=[
                TeacherClassDetail(
                    id=c["id"],
                    name=c["name"],
                    student_count=c["student_count"],
                    average_grade=c["average_grade"],
                    at_risk_count=c["at_risk_count"],
                )
                for c in data["classes"]
            ],
        )
