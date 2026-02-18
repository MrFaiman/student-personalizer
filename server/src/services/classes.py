from uuid import UUID

import numpy as np
from sqlmodel import select

from ..constants import AT_RISK_GRADE_THRESHOLD
from ..models import Class, Grade, Student
from .base import BaseService


class ClassService(BaseService):
    """Core service for Class domain logic."""

    def list_classes_with_stats(self, period: str | None = None) -> list[dict]:
        """Get all classes with calculated statistics."""
        classes = self.session.exec(
            select(Class).where(Class.school_id == self.school_id)
        ).all()
        if not classes:
            return []

        class_map = {c.id: c for c in classes}

        students = self.session.exec(
            select(Student).where(Student.school_id == self.school_id)
        ).all()
        student_tzs = [s.student_tz for s in students]

        grade_query = select(Grade).where(
            Grade.student_tz.in_(student_tzs),
            Grade.school_id == self.school_id,
        )
        if period:
            grade_query = grade_query.where(Grade.period == period)
        grades = self.session.exec(grade_query).all()

        student_grades: dict[str, list[float]] = {}
        for g in grades:
            if g.student_tz not in student_grades:
                student_grades[g.student_tz] = []
            student_grades[g.student_tz].append(g.grade)

        class_stats = {cid: {"grades": [], "at_risk": 0, "students": 0} for cid in class_map.keys()}

        for s in students:
            if not s.class_id or s.class_id not in class_stats:
                continue

            stats = class_stats[s.class_id]
            stats["students"] += 1

            s_grades = student_grades.get(s.student_tz)
            if s_grades:
                avg = np.mean(s_grades)
                stats["grades"].append(avg)
                if avg < AT_RISK_GRADE_THRESHOLD:
                    stats["at_risk"] += 1

        result_data = []
        for cls in classes:
            stats = class_stats.get(cls.id)
            if not stats:
                continue

            c_grades = stats["grades"]
            class_avg = float(np.mean(c_grades)) if c_grades else None

            result_data.append({
                "class": cls,
                "student_count": stats["students"],
                "average_grade": class_avg,
                "at_risk_count": stats["at_risk"],
            })

        return result_data

    def get_class_heatmap(self, class_id: UUID, period: str | None = None) -> dict:
        """Returns Heatmap Matrix: Student x Subject."""
        students = self.session.exec(
            select(Student).where(
                Student.class_id == class_id,
                Student.school_id == self.school_id,
            )
        ).all()
        if not students:
            return {}

        student_tzs = [s.student_tz for s in students]

        grade_query = select(Grade).where(
            Grade.student_tz.in_(student_tzs),
            Grade.school_id == self.school_id,
        )
        if period:
            grade_query = grade_query.where(Grade.period == period)
        grades = self.session.exec(grade_query).all()

        student_data = {s.student_tz: {"name": s.student_name, "grades": {}} for s in students}
        all_subjects: set[str] = set()

        for g in grades:
            if g.student_tz in student_data:
                student_data[g.student_tz]["grades"][g.subject] = g.grade
                all_subjects.add(g.subject)

        student_rows = []

        for tz, s_data in student_data.items():
            grades_dict = s_data["grades"]

            valid_grades = [v for v in grades_dict.values() if v is not None]
            avg = float(np.mean(valid_grades)) if valid_grades else 0

            student_rows.append({
                "student_name": s_data["name"],
                "student_tz": tz,
                "grades": grades_dict,
                "average": avg,
            })

        return {
            "subjects": all_subjects,
            "students": student_rows,
        }

    def get_top_bottom_students(self, class_id: UUID, period: str | None = None, top_n: int = 5, bottom_n: int = 5) -> dict:
        """Returns sorted students with pre-calculated averages."""
        students = self.session.exec(
            select(Student).where(
                Student.class_id == class_id,
                Student.school_id == self.school_id,
            )
        ).all()
        if not students:
            return {"sorted_students": [], "top_n": top_n, "bottom_n": bottom_n}

        student_tzs = [s.student_tz for s in students]

        grade_query = select(Grade).where(
            Grade.student_tz.in_(student_tzs),
            Grade.school_id == self.school_id,
        )
        if period:
            grade_query = grade_query.where(Grade.period == period)
        grades = self.session.exec(grade_query).all()

        student_grades: dict[str, list[float]] = {}
        for g in grades:
            if g.student_tz not in student_grades:
                student_grades[g.student_tz] = []
            student_grades[g.student_tz].append(g.grade)

        student_averages = []
        for student in students:
            s_grades = student_grades.get(student.student_tz)
            if s_grades:
                avg = float(np.mean(s_grades))
                student_averages.append({
                    "student_name": student.student_name,
                    "student_tz": student.student_tz,
                    "average": avg,
                })

        return {
            "students": student_averages,
            "top_n": top_n,
            "bottom_n": bottom_n,
        }
