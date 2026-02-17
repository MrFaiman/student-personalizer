from ..schemas.analytics import StudentRankItem, TopBottomResponse
from ..schemas.student import ClassResponse


class ClassDefaultView:
    """Default view presenter for Class data."""

    def render_list(self, data: list[dict]) -> list[ClassResponse]:
        """Render list of classes with pre-calculated stats."""
        result = []
        for item in data:
            cls = item["class"]
            result.append(
                ClassResponse(
                    id=cls.id,
                    class_name=cls.class_name,
                    grade_level=cls.grade_level,
                    student_count=item["student_count"],
                    average_grade=item["average_grade"],
                    at_risk_count=item["at_risk_count"],
                )
            )

        result.sort(key=lambda x: x.class_name)
        return result

    def render_heatmap(self, data: dict) -> dict:
        """Render heatmap JSON (already formatted by service)."""
        return data

    def render_rankings(self, data: dict) -> TopBottomResponse:
        """Render Top/Bottom students."""
        sorted_students = data["sorted_students"]
        top_n = data["top_n"]
        bottom_n = data["bottom_n"]

        items = [
            StudentRankItem(
                student_name=s["student_name"],
                student_tz=s["student_tz"],
                average=s["average"],
            )
            for s in sorted_students
        ]

        return TopBottomResponse(
            top=items[:top_n],
            bottom=items[-bottom_n:] if len(items) >= bottom_n else items,
        )
