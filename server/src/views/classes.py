from ..schemas.analytics import StudentRankItem, TopBottomResponse
from ..schemas.student import ClassResponse


class ClassDefaultView:
    """Default view presenter for Class data."""

    def render_list(self, data: list[dict]) -> list[ClassResponse]:
        """Render list of classes with rounding and sorting."""
        result = []
        for item in data:
            cls = item["class"]
            avg = item["average_grade"]
            result.append(
                ClassResponse(
                    id=cls.id,
                    class_name=cls.class_name,
                    grade_level=cls.grade_level,
                    student_count=item["student_count"],
                    average_grade=round(avg, 1) if avg is not None else None,
                    at_risk_count=item["at_risk_count"],
                )
            )

        result.sort(key=lambda x: x.class_name)
        return result

    def render_heatmap(self, data: dict) -> dict:
        """Render heatmap: sort subjects/students, round averages, fill missing."""
        subjects = sorted(data["subjects"])
        student_rows = []

        for row in data["students"]:
            grades_dict = dict(row["grades"])
            for subj in subjects:
                if subj not in grades_dict:
                    grades_dict[subj] = None

            student_rows.append({
                "student_name": row["student_name"],
                "student_tz": row["student_tz"],
                "grades": grades_dict,
                "average": round(row["average"], 1),
            })

        student_rows.sort(key=lambda x: x["student_name"])

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
