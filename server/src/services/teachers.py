from uuid import UUID

import numpy as np
from sqlmodel import select

from ..constants import AT_RISK_GRADE_THRESHOLD
from ..models import Class, Grade, Student, Teacher
from .base import BaseService


class TeacherService(BaseService):
    """Core service for Teacher domain logic."""

    def list_teachers(self, period: str | None = None) -> list[str]:
        """Get list of all teacher names with available grades."""
        query = (
            select(Grade.teacher_name)
            .distinct()
            .where(Grade.teacher_name.is_not(None), Grade.school_id == self.school_id)
        )
        if period:
            query = query.where(Grade.period == period)
        return list(self.session.exec(query).all())

    def get_teachers_list_with_stats(
        self, period: str | None = None, grade_level: str | None = None
    ) -> list[dict]:
        """Get list of all teachers with summary stats (pre-calculated)."""
        query = select(Grade).where(Grade.school_id == self.school_id)
        if period:
            query = query.where(Grade.period == period)

        grades = self.session.exec(query).all()

        valid_student_tzs = set()
        if grade_level:
            student_query = (
                select(Student.student_tz)
                .join(Class)
                .where(Class.grade_level == grade_level, Student.school_id == self.school_id)
            )
            valid_student_tzs = set(self.session.exec(student_query).all())
            grades = [g for g in grades if g.student_tz in valid_student_tzs]

        teacher_stats: dict = {}

        for g in grades:
            if not g.teacher_name:
                continue

            if g.teacher_name not in teacher_stats:
                teacher_stats[g.teacher_name] = {
                    "teacher_id": g.teacher_id,
                    "grades": [],
                    "students": set(),
                    "subjects": set(),
                }

            stats = teacher_stats[g.teacher_name]
            stats["grades"].append(g.grade)
            stats["students"].add(g.student_tz)
            stats["subjects"].add(g.subject)
            if g.teacher_id:
                stats["teacher_id"] = g.teacher_id

        results = []
        for name, stats in teacher_stats.items():
            grades_list = stats["grades"]
            avg = float(np.mean(grades_list)) if grades_list else 0

            results.append({
                "id": stats["teacher_id"],
                "name": name,
                "student_count": len(stats["students"]),
                "average_grade": avg,
                "subjects": stats["subjects"],
            })

        return results

    def get_teacher_stats(self, teacher_name: str, period: str | None = None) -> dict:
        """Get raw grade data for a teacher."""
        query = select(Grade).where(
            Grade.teacher_name == teacher_name,
            Grade.school_id == self.school_id,
        )
        if period:
            query = query.where(Grade.period == period)

        grades = self.session.exec(query).all()

        if not grades:
            return {"total_students": 0}

        student_tzs = set(g.student_tz for g in grades)

        return {
            "teacher_name": teacher_name,
            "total_students": len(student_tzs),
            "grades": [g.grade for g in grades],
            "subjects": set(g.subject for g in grades),
        }

    def get_teacher_detail(self, teacher_id: UUID, period: str | None = None) -> dict | None:
        """Get detailed analytics for a specific teacher (pre-calculated)."""
        teacher = self.session.get(Teacher, teacher_id)
        if not teacher or teacher.school_id != self.school_id:
            return None

        query = select(Grade).where(
            Grade.teacher_id == teacher_id,
            Grade.school_id == self.school_id,
        )
        if period:
            query = query.where(Grade.period == period)
        grades = self.session.exec(query).all()

        if not grades:
            return {
                "teacher": teacher,
                "stats": {
                    "student_count": 0,
                    "average_grade": 0,
                    "at_risk_count": 0,
                    "classes_count": 0,
                },
                "classes": [],
                "grades": [],
            }

        student_tzs = set(g.student_tz for g in grades)

        students = self.session.exec(select(Student).where(Student.student_tz.in_(student_tzs))).all()
        student_map = {s.student_tz: s for s in students}

        class_ids = set(s.class_id for s in students if s.class_id)
        classes = self.session.exec(select(Class).where(Class.id.in_(class_ids))).all()
        class_map = {c.id: c for c in classes}

        avg_grade = float(np.mean([g.grade for g in grades])) if grades else 0

        # Analyze by class
        class_stats: dict = {}
        for g in grades:
            s = student_map.get(g.student_tz)
            if not s or not s.class_id:
                continue

            cid = s.class_id
            if cid not in class_stats:
                class_stats[cid] = {"grades": [], "students": set(), "at_risk": 0}

            class_stats[cid]["grades"].append(g.grade)
            class_stats[cid]["students"].add(g.student_tz)
            if g.grade < AT_RISK_GRADE_THRESHOLD:
                class_stats[cid]["at_risk"] += 1

        classes_data = []
        for cid, stats in class_stats.items():
            cls = class_map.get(cid)
            if not cls:
                continue

            c_grades = stats["grades"]
            c_avg = float(np.mean(c_grades))

            classes_data.append({
                "id": str(cls.id),
                "name": cls.class_name,
                "student_count": len(stats["students"]),
                "average_grade": round(c_avg, 1),
                "at_risk_count": stats["at_risk"],
            })

        # At-risk: students with avg < threshold with this teacher
        student_avgs: dict[str, list[float]] = {}
        for g in grades:
            if g.student_tz not in student_avgs:
                student_avgs[g.student_tz] = []
            student_avgs[g.student_tz].append(g.grade)

        at_risk_students = 0
        for grades_list in student_avgs.values():
            if np.mean(grades_list) < AT_RISK_GRADE_THRESHOLD:
                at_risk_students += 1

        return {
            "teacher": teacher,
            "stats": {
                "student_count": len(student_tzs),
                "average_grade": round(avg_grade, 1),
                "at_risk_count": at_risk_students,
                "classes_count": len(class_ids),
            },
            "classes": classes_data,
            "grades": grades,
        }
