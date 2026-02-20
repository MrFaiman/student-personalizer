from ..schemas.analytics import StudentRankItem, TopBottomResponse
from ..schemas.student import ClassResponse


class ClassDefaultView:
    """Default view presenter for Class data."""

    def render_list(self, data: list[dict]) -> list[ClassResponse]:
        """Render list of classes with rounding and sorting."""
        return sorted(
            [
                ClassResponse(
                    id=item["class"].id,
                    class_name=item["class"].class_name,
                    grade_level=item["class"].grade_level,
                    student_count=item["student_count"],
                    average_grade=round(item["average_grade"], 1) if item["average_grade"] is not None else None,
                    at_risk_count=item["at_risk_count"],
                )
                for item in data
            ],
            key=lambda x: x.class_name,
        )

    def render_heatmap(self, data: dict) -> dict:
        """Render heatmap: sort subjects/students, round averages, fill missing."""
        subjects = sorted(data["subjects"])

        student_rows = sorted(
            [
                {
                    "student_name": row["student_name"],
                    "student_tz": row["student_tz"],
                    "grades": {subj: dict(row["grades"]).get(subj) for subj in subjects},
                    "average": round(row["average"], 1),
                }
                for row in data["students"]
            ],
            key=lambda x: x["student_name"],
        )

        return {
            "subjects": subjects,
            "students": student_rows,
        }

    def render_rankings(self, data: dict) -> TopBottomResponse:
        """Render Top/Bottom students: round, sort, slice."""
        students = data["students"]
        top_n = data["top_n"]
        bottom_n = data["bottom_n"]

        sorted_students = sorted(students, key=lambda x: x["average"], reverse=True)

        items = [
            StudentRankItem(
                student_name=s["student_name"],
                student_tz=s["student_tz"],
                average=round(s["average"], 1),
            )
            for s in sorted_students
        ]

        return TopBottomResponse(
            top=items[:top_n],
            bottom=items[-bottom_n:] if len(items) >= bottom_n else items,
        )
