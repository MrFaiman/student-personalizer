import numpy as np
from ..models import Class
from ..schemas.student import ClassResponse
from ..schemas.analytics import TopBottomResponse


class ClassDefaultView:
    """Default view presenter for Class data."""

    def render_list(self, data: list[dict]) -> list[ClassResponse]:
        """Render list of classes with stats."""
        result = []
        for item in data:
            cls: Class = item["class"]
            stats: dict = item["stats"]
            
            c_grades = stats["grades"]
            c_grades = stats["grades"]
            class_avg = np.mean(c_grades) if c_grades else None

            result.append(
                ClassResponse(
                    id=cls.id,
                    class_name=cls.class_name,
                    grade_level=cls.grade_level,
                    student_count=stats["students"],
                    average_grade=round(class_avg, 1) if class_avg else None,
                    at_risk_count=stats["at_risk"],
                )
            )
        
        result.sort(key=lambda x: x.class_name)
        return result

    def render_heatmap(self, data: dict) -> dict:
        """Render heatmap JSON."""
        if not data:
            return {}
            
        student_data = data["student_data"]
        all_subjects = data["all_subjects"]
        
        sorted_subjects = sorted(all_subjects)
        student_rows = []

        for tz, s_data in student_data.items():
            grades_dict = s_data["grades"]
            for subj in sorted_subjects:
                if subj not in grades_dict:
                    grades_dict[subj] = None
            
            valid_grades = [v for v in grades_dict.values() if v is not None]
            valid_grades = [v for v in grades_dict.values() if v is not None]
            avg = round(np.mean(valid_grades), 2) if valid_grades else 0

            student_rows.append({
                "student_name": s_data["name"],
                "student_tz": tz,
                "grades": grades_dict,
                "average": avg,
            })

        student_rows.sort(key=lambda x: x["student_name"])

        return {
            "subjects": sorted_subjects,
            "students": student_rows,
        }

    def render_rankings(self, data: dict) -> TopBottomResponse:
        """Render Top/Bottom students."""
        sorted_students = data["sorted_students"]
        top_n = data["top_n"]
        bottom_n = data["bottom_n"]
        
        # Round logic was in service in original, but belongs in View if it's formatting. 
        # But for sorting, I kept raw msg in service? 
        # Actually in service I returned dicts with 'average'. Logic was: `round(avg, 2)` inside the loop.
        # Let's ensure formatting is consistent.
        
        formatted_students = [
            {
                "student_name": s["student_name"],
                "student_tz": s["student_tz"],
                "average": round(s["average"], 2)
            }
            for s in sorted_students
        ]

        return TopBottomResponse(
            top=formatted_students[:top_n],
            bottom=formatted_students[-bottom_n:] if len(formatted_students) >= bottom_n else formatted_students,
        )
