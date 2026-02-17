from ..schemas.analytics import TeacherListItem, TeacherStatsResponse, TeacherDetailResponse


class TeacherDefaultView:
    """Default view presenter for Teacher data."""

    def render_list(self, data: list[dict]) -> list[TeacherListItem]:
        """Render list of teachers with summary stats."""
        result = []
        for item in data:
            result.append(
                TeacherListItem(
                    id=item["id"],
                    name=item["name"],
                    student_count=item["student_count"],
                    average_grade=round(item["average_grade"], 1),
                    subjects=item["subjects"],
                )
            )
        
        result.sort(key=lambda x: x.name)
        return result

    def render_stats(self, data: dict) -> TeacherStatsResponse:
        """Render teacher stats response."""
        return TeacherStatsResponse(
            teacher_name=data["teacher_name"],
            total_students=data["total_students"],
            average_grade=round(data["average_grade"], 1),
            distribution=data["distribution"],
            subjects=data["subjects"],
        )

    def render_detail(self, data: dict) -> TeacherDetailResponse:
        """Render teacher detail response."""
        teacher = data["teacher"]
        stats = data["stats"]
        
        return TeacherDetailResponse(
            id=teacher.id,
            name=teacher.name,
            email=teacher.email,
            stats={
                "student_count": stats["student_count"],
                "average_grade": round(stats["average_grade"], 1),
                "at_risk_count": stats["at_risk_count"],
                "classes_count": stats["classes_count"],
            },
            subjects=sorted(data["subjects"]),
            classes=[
                {
                    "id": c["id"],
                    "name": c["name"],
                    "student_count": c["student_count"],
                    "average_grade": round(c["average_grade"], 1),
                    "at_risk_count": c["at_risk_count"],
                }
                for c in data["classes"]
            ]
        )
