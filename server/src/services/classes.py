import numpy as np
from uuid import UUID

from sqlmodel import Session, select

from ..constants import AT_RISK_GRADE_THRESHOLD
from ..models import Class, Grade, Student


class ClassService:
    """Core service for Class domain logic."""

    def __init__(self, session: Session):
        self.session = session

    def list_classes_with_stats(self, period: str | None = None) -> list[dict]:
        """
        Get all classes with calculated statistics.
        Returns a list of dicts suitable for the view.
        """
        classes = self.session.exec(select(Class)).all()
        if not classes:
            return []

        class_map = {c.id: c for c in classes}

        students = self.session.exec(select(Student)).all()
        student_tzs = [s.student_tz for s in students]

        grade_query = select(Grade).where(Grade.student_tz.in_(student_tzs))
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
            
            result_data.append({
                "class": cls,
                "stats": stats
            })
            
        return result_data

    def get_class_heatmap(self, class_id: UUID, period: str | None = None) -> dict:
        """
        Returns Heatmap Matrix: Student x Subject.
        """
        students = self.session.exec(select(Student).where(Student.class_id == class_id)).all()
        if not students:
            return {}

        student_tzs = [s.student_tz for s in students]

        grade_query = select(Grade).where(Grade.student_tz.in_(student_tzs))
        if period:
            grade_query = grade_query.where(Grade.period == period)
        grades = self.session.exec(grade_query).all()

        student_data = {s.student_tz: {"name": s.student_name, "grades": {}} for s in students}
        all_subjects = set()

        for g in grades:
            if g.student_tz in student_data:
                student_data[g.student_tz]["grades"][g.subject] = g.grade
                all_subjects.add(g.subject)
        
        return {
            "student_data": student_data,
            "all_subjects": all_subjects
        }

    def get_top_bottom_students(self, class_id: UUID, period: str | None = None, top_n: int = 5, bottom_n: int = 5) -> dict:
        """
        Returns Top N and Bottom N students in a class based on averages.
        """
        students = self.session.exec(select(Student).where(Student.class_id == class_id)).all()
        if not students:
             return {"top": [], "bottom": []}

        student_tzs = [s.student_tz for s in students]

        grade_query = select(Grade).where(Grade.student_tz.in_(student_tzs))
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
                avg = np.mean(s_grades)
                student_averages.append(
                    {
                        "student_name": student.student_name,
                        "student_tz": student.student_tz,
                        "average": avg,
                    }
                )

        sorted_students = sorted(student_averages, key=lambda x: x["average"], reverse=True)

        return {
            "sorted_students": sorted_students,
            "top_n": top_n,
            "bottom_n": bottom_n
        }
