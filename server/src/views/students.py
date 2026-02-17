from ..constants import AT_RISK_GRADE_THRESHOLD
from ..models import AttendanceRecord, Class, Grade, Student
from ..schemas.student import (
    StudentDetailResponse,
    StudentListResponse,
)


class StudentDefaultView:
    """Default view presenter for Student data."""

    def render_list(self, data: dict) -> StudentListResponse:
        """Render the student list response."""
        students = data["items"]
        classes_map = data["classes_map"]
        student_grades = data["student_grades"]
        student_attendance = data["student_attendance"]
        
        result_items = []
        for student in students:
            cls = classes_map.get(student.class_id)
            grade_level = cls.grade_level if cls else None
            class_name = cls.class_name if cls else "Unknown"

            grades = student_grades.get(student.student_tz, [])
            avg_grade = sum(grades) / len(grades) if grades else None

            attendance_records = student_attendance.get(student.student_tz, [])
            total_absences = sum(a.total_absences for a in attendance_records)
            total_negative = sum(a.total_negative_events for a in attendance_records)
            total_positive = sum(a.total_positive_events for a in attendance_records)

            is_at_risk = avg_grade is not None and avg_grade < AT_RISK_GRADE_THRESHOLD

            result_items.append(
                StudentDetailResponse(
                    student_tz=student.student_tz,
                    student_name=student.student_name,
                    class_id=student.class_id,
                    class_name=class_name,
                    grade_level=grade_level,
                    average_grade=round(avg_grade, 1) if avg_grade else None,
                    total_absences=total_absences,
                    total_negative_events=total_negative,
                    total_positive_events=total_positive,
                    is_at_risk=is_at_risk,
                )
            )

        return StudentListResponse(
            items=result_items,
            total=data["total"],
            page=data["page"],
            page_size=data["page_size"],
        )

    def render_detail(self, data: dict) -> StudentDetailResponse:
        """Render the student detail response."""
        student: Student = data["student"]
        cls: Class | None = data["class"]
        grades: list[Grade] = data["grades"]
        attendance: list[AttendanceRecord] = data["attendance"]
        performance_score = data["performance_score"]

        grade_level = cls.grade_level if cls else None
        class_name = cls.class_name if cls else "Unknown"

        avg_grade = None
        if grades:
            avg_grade = sum(g.grade for g in grades) / len(grades)

        total_absences = sum(a.total_absences for a in attendance)
        total_negative = sum(a.total_negative_events for a in attendance)
        total_positive = sum(a.total_positive_events for a in attendance)

        return StudentDetailResponse(
            student_tz=student.student_tz,
            student_name=student.student_name,
            class_id=student.class_id,
            class_name=class_name,
            grade_level=grade_level,
            average_grade=round(avg_grade, 1) if avg_grade else None,
            total_absences=total_absences,
            total_negative_events=total_negative,
            total_positive_events=total_positive,
            is_at_risk=avg_grade is not None and avg_grade < AT_RISK_GRADE_THRESHOLD,
            performance_score=performance_score,
        )
