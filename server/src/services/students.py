from uuid import UUID

from sqlmodel import func, select

from ..constants import (
    AT_RISK_GRADE_THRESHOLD,
    ATTENDANCE_WEIGHT,
    ATTENDANCE_WEIGHT_NO_GRADES,
    BEHAVIOR_WEIGHT,
    BEHAVIOR_WEIGHT_NO_GRADES,
    DEFAULT_PAGE_SIZE,
    GRADE_WEIGHT,
)
from ..models import AttendanceRecord, Class, Grade, Student
from ..utils.stats import calculate_at_risk_status, calculate_average, sum_attendance_stats
from .base import BaseService


class StudentService(BaseService):
    """Core service for Student domain logic."""

    def list_students(
        self,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        class_id: UUID | None = None,
        search: str | None = None,
        at_risk_only: bool = False,
        period: str | None = None,
    ) -> dict:
        """List students with filters and related data. Returns a dict for the view."""
        query = select(Student).where(Student.school_id == self.school_id)

        if class_id:
            query = query.where(Student.class_id == class_id)
        if search:
            query = query.where(Student.student_name.contains(search))

        if at_risk_only:
            subquery = (
                select(Grade.student_tz)
                .where(Grade.school_id == self.school_id)
                .group_by(Grade.student_tz)
                .having(func.avg(Grade.grade) < AT_RISK_GRADE_THRESHOLD)
            )
            if period:
                subquery = subquery.where(Grade.period == period)
            query = query.where(Student.student_tz.in_(subquery))

        count_query = select(func.count()).select_from(query.subquery())
        total = self.session.exec(count_query).one()

        query = query.offset((page - 1) * page_size).limit(page_size)
        students = self.session.exec(query).all()

        if not students:
            return {
                "items": [],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        student_tzs = [s.student_tz for s in students]
        class_ids = {s.class_id for s in students if s.class_id}

        classes_map = {}
        if class_ids:
            classes = self.session.exec(select(Class).where(Class.id.in_(class_ids))).all()
            classes_map = {c.id: c for c in classes}

        grade_query = select(Grade).where(
            Grade.student_tz.in_(student_tzs),
            Grade.school_id == self.school_id,
        )
        if period:
            grade_query = grade_query.where(Grade.period == period)
        all_grades = self.session.exec(grade_query).all()

        student_grades: dict[str, list[float]] = {tz: [] for tz in student_tzs}
        for g in all_grades:
            if g.student_tz in student_grades:
                student_grades[g.student_tz].append(g.grade)

        att_query = select(AttendanceRecord).where(
            AttendanceRecord.student_tz.in_(student_tzs),
            AttendanceRecord.school_id == self.school_id,
        )
        if period:
            att_query = att_query.where(AttendanceRecord.period == period)
        all_attendance = self.session.exec(att_query).all()

        student_attendance: dict[str, list[AttendanceRecord]] = {tz: [] for tz in student_tzs}
        for a in all_attendance:
            if a.student_tz in student_attendance:
                student_attendance[a.student_tz].append(a)

        result_items = []
        for student in students:
            cls = classes_map.get(student.class_id)
            grade_level = cls.grade_level if cls else None
            class_name = cls.class_name if cls else "Unknown"

            grades = student_grades.get(student.student_tz, [])
            avg_grade = calculate_average(grades)

            attendance_records = student_attendance.get(student.student_tz, [])
            att_stats = sum_attendance_stats(attendance_records)

            is_at_risk = calculate_at_risk_status(avg_grade)

            result_items.append({
                "student_tz": student.student_tz,
                "student_name": student.student_name,
                "class_id": student.class_id,
                "class_name": class_name,
                "grade_level": grade_level,
                "average_grade": avg_grade,
                "total_absences": att_stats["total_absences"],
                "total_negative_events": att_stats["total_negative_events"],
                "total_positive_events": att_stats["total_positive_events"],
                "is_at_risk": is_at_risk,
            })

        return {
            "items": result_items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_student_detail(self, student_tz: str, period: str | None = None) -> dict | None:
        """Get flattened detailed student data as a dict for the view."""
        student = self.session.get(Student, student_tz)
        if not student or student.school_id != self.school_id:
            return None

        cls = self.session.get(Class, student.class_id)

        grade_query = select(Grade).where(
            Grade.student_tz == student_tz,
            Grade.school_id == self.school_id,
        )
        if period:
            grade_query = grade_query.where(Grade.period == period)
        grades = self.session.exec(grade_query).all()
        grade_values = [g.grade for g in grades]

        att_query = select(AttendanceRecord).where(
            AttendanceRecord.student_tz == student_tz,
            AttendanceRecord.school_id == self.school_id,
        )
        if period:
            att_query = att_query.where(AttendanceRecord.period == period)
        attendance_records = self.session.exec(att_query).all()

        avg_grade = calculate_average(grade_values)
        att_stats = sum_attendance_stats(attendance_records)
        is_at_risk = calculate_at_risk_status(avg_grade)

        performance_score = self._calculate_performance_score(student_tz, period, grades, attendance_records)

        grade_level = cls.grade_level if cls else None
        class_name = cls.class_name if cls else "Unknown"

        return {
            "student_tz": student.student_tz,
            "student_name": student.student_name,
            "class_id": student.class_id,
            "class_name": class_name,
            "grade_level": grade_level,
            "average_grade": avg_grade,
            "total_absences": att_stats["total_absences"],
            "total_negative_events": att_stats["total_negative_events"],
            "total_positive_events": att_stats["total_positive_events"],
            "is_at_risk": is_at_risk,
            "performance_score": performance_score,
        }

    def get_dashboard_stats(
        self,
        class_id: UUID | None = None,
        period: str | None = None,
    ) -> dict:
        """Get dashboard statistics as a dict for the view."""
        class_query = select(Class).where(Class.school_id == self.school_id)
        if class_id:
            class_query = class_query.where(Class.id == class_id)
        classes = self.session.exec(class_query).all()
        class_map = {c.id: c for c in classes}

        if not classes:
            return {
                "total_students": 0,
                "average_grade": None,
                "at_risk_count": 0,
                "total_classes": 0,
                "classes": [],
            }

        student_query = select(Student).where(
            Student.class_id.in_(class_map.keys()),
            Student.school_id == self.school_id,
        )
        students = self.session.exec(student_query).all()
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

        student_stats = {}
        for s in students:
            s_grades = student_grades.get(s.student_tz)
            if s_grades:
                avg = sum(s_grades) / len(s_grades)
                student_stats[s.student_tz] = {
                    "avg": avg,
                    "at_risk": avg < AT_RISK_GRADE_THRESHOLD,
                    "class_id": s.class_id,
                }
            else:
                student_stats[s.student_tz] = {
                    "avg": None,
                    "at_risk": False,
                    "class_id": s.class_id,
                }

        class_stats = {cid: {"grades": [], "at_risk": 0, "students": 0} for cid in class_map.keys()}

        overall_grades = []
        total_at_risk = 0

        for s in students:
            stats = student_stats[s.student_tz]
            cid = stats["class_id"]

            if cid in class_stats:
                class_stats[cid]["students"] += 1
                if stats["avg"] is not None:
                    class_stats[cid]["grades"].append(stats["avg"])
                    overall_grades.append(stats["avg"])
                if stats["at_risk"]:
                    class_stats[cid]["at_risk"] += 1
                    total_at_risk += 1

        class_responses = []
        for cls in classes:
            stats = class_stats.get(cls.id)
            if not stats:
                continue

            c_grades = stats["grades"]
            c_avg = sum(c_grades) / len(c_grades) if c_grades else None

            class_responses.append({
                "id": cls.id,
                "class_name": cls.class_name,
                "grade_level": cls.grade_level,
                "student_count": stats["students"],
                "average_grade": c_avg,
                "at_risk_count": stats["at_risk"],
            })

        overall_avg = sum(overall_grades) / len(overall_grades) if overall_grades else None

        return {
            "total_students": len(students),
            "average_grade": overall_avg,
            "at_risk_count": total_at_risk,
            "total_classes": len(classes),
            "classes": class_responses,
        }

    def get_student_grades(self, student_tz: str, period: str | None = None) -> list[dict] | None:
        """Get all grades for a student as a list of dicts for the view."""
        student = self.session.get(Student, student_tz)
        if not student or student.school_id != self.school_id:
            return None

        query = select(Grade).where(
            Grade.student_tz == student_tz,
            Grade.school_id == self.school_id,
        )
        if period:
            query = query.where(Grade.period == period)

        grades = self.session.exec(query).all()

        return [
            {
                "id": g.id,
                "subject": g.subject,
                "teacher_name": g.teacher_name,
                "grade": g.grade,
                "period": g.period,
            }
            for g in grades
        ]

    def get_student_attendance(self, student_tz: str, period: str | None = None) -> list[dict] | None:
        """Get all attendance records for a student as a list of dicts for the view."""
        student = self.session.get(Student, student_tz)
        if not student or student.school_id != self.school_id:
            return None

        query = select(AttendanceRecord).where(
            AttendanceRecord.student_tz == student_tz,
            AttendanceRecord.school_id == self.school_id,
        )
        if period:
            query = query.where(AttendanceRecord.period == period)

        records = self.session.exec(query).all()

        return [
            {
                "id": r.id,
                "lessons_reported": r.lessons_reported,
                "absence": r.absence,
                "absence_justified": r.absence_justified,
                "late": r.late,
                "disturbance": r.disturbance,
                "total_absences": r.total_absences,
                "attendance": r.attendance,
                "total_negative_events": r.total_negative_events,
                "total_positive_events": r.total_positive_events,
                "period": r.period,
            }
            for r in records
        ]

    def _calculate_performance_score(self, student_tz: str, period: str | None, student_grades: list, attendance_records: list) -> float | None:
        """Internal logic to calculate performance score percentile."""
        total_students_count = self.session.exec(
            select(func.count(Student.student_tz)).where(Student.school_id == self.school_id)
        ).one()
        if total_students_count <= 1:
            return None

        avg_query = (
            select(Grade.student_tz, func.avg(Grade.grade))
            .where(Grade.school_id == self.school_id)
            .group_by(Grade.student_tz)
        )
        if period:
            avg_query = avg_query.where(Grade.period == period)
        all_avg_grades = self.session.exec(avg_query).all()
        avg_grades_map = {row[0]: row[1] for row in all_avg_grades}

        att_stats_query = (
            select(
                AttendanceRecord.student_tz,
                func.sum(AttendanceRecord.total_absences),
                func.sum(AttendanceRecord.total_negative_events),
                func.sum(AttendanceRecord.total_positive_events),
            )
            .where(AttendanceRecord.school_id == self.school_id)
            .group_by(AttendanceRecord.student_tz)
        )
        if period:
            att_stats_query = att_stats_query.where(AttendanceRecord.period == period)
        all_att_stats = self.session.exec(att_stats_query).all()
        att_stats_map = {
            row[0]: {
                "absences": row[1] or 0,
                "negative": row[2] or 0,
                "positive": row[3] or 0,
            }
            for row in all_att_stats
        }

        all_student_tzs = self.session.exec(
            select(Student.student_tz).where(Student.school_id == self.school_id)
        ).all()
        student_stats_list = []
        for tz in all_student_tzs:
            s_avg = avg_grades_map.get(tz)
            s_att = att_stats_map.get(tz, {"absences": 0, "negative": 0, "positive": 0})
            student_stats_list.append({
                "tz": tz,
                "avg_grade": s_avg,
                "absences": s_att["absences"],
                "negative": s_att["negative"],
                "positive": s_att["positive"],
            })

        target_stats = next((s for s in student_stats_list if s["tz"] == student_tz), None)
        if not target_stats:
            return None

        def percentile_rank(values: list[float], target: float) -> float:
            below = sum(1 for v in values if v < target)
            return (below / len(values)) * 100

        grade_values = [s["avg_grade"] for s in student_stats_list if s["avg_grade"] is not None]
        target_avg = target_stats["avg_grade"]
        grade_pct = percentile_rank(grade_values, target_avg) if target_avg is not None and grade_values else None

        absence_values = [-s["absences"] for s in student_stats_list]
        absence_pct = percentile_rank(absence_values, -target_stats["absences"])

        behavior_values = [s["positive"] - s["negative"] for s in student_stats_list]
        target_behavior = target_stats["positive"] - target_stats["negative"]
        behavior_pct = percentile_rank(behavior_values, target_behavior)

        if grade_pct is not None:
            return round(grade_pct * GRADE_WEIGHT + absence_pct * ATTENDANCE_WEIGHT + behavior_pct * BEHAVIOR_WEIGHT, 1)
        else:
            return round(absence_pct * ATTENDANCE_WEIGHT_NO_GRADES + behavior_pct * BEHAVIOR_WEIGHT_NO_GRADES, 1)
