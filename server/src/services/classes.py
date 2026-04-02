from uuid import UUID

from sqlalchemy import case, literal
from sqlmodel import Session, func, select

from ..auth.current_user import CurrentUser
from ..constants import AT_RISK_GRADE_THRESHOLD
from ..models import Class, Grade, Student


class ClassService:
    """Core service for Class domain logic."""

    def __init__(self, session: Session):
        self.session = session

    def _require_school_id(self, current_user: CurrentUser) -> int:
        if current_user.school_id is None:
            raise ValueError("School scope required")
        return current_user.school_id

    def list_classes_with_stats(
        self,
        *,
        current_user: CurrentUser,
        period: str | None = None,
        year: str | None = None,
    ) -> list[dict]:
        """
        Get all classes with calculated statistics.
        Returns pre-calculated dicts for the view to format.
        """
        school_id = self._require_school_id(current_user)
        classes = self.session.exec(select(Class).where(Class.school_id == school_id)).all()
        if not classes:
            return []

        class_map = {c.id: c for c in classes}

        # Subquery: per-student average grade
        student_avg_query = (
            select(
                Grade.student_tz,
                func.avg(Grade.grade).label("avg_grade"),
            )
            .where(Grade.school_id == school_id)
            .group_by(Grade.student_tz)
        )
        if year:
            student_avg_query = student_avg_query.where(Grade.year == year)
        if period:
            student_avg_query = student_avg_query.where(Grade.period == period)
        student_avg_sub = student_avg_query.subquery()

        # Aggregate per class: student count, class avg, at-risk count
        class_stats_query = (
            select(
                Student.class_id,
                func.count(Student.student_tz).label("student_count"),
                func.avg(student_avg_sub.c.avg_grade).label("class_avg"),
                func.count(case((student_avg_sub.c.avg_grade < AT_RISK_GRADE_THRESHOLD, literal(1)))).label("at_risk_count"),
            )
            .outerjoin(student_avg_sub, Student.student_tz == student_avg_sub.c.student_tz)
            .where(Student.class_id.isnot(None), Student.school_id == school_id)
            .group_by(Student.class_id)
        )
        rows = self.session.exec(class_stats_query).all()

        result_data = []
        for cid, student_count, class_avg, at_risk_count in rows:
            cls = class_map.get(cid)
            if not cls:
                continue

            result_data.append({
                "class": cls,
                "student_count": student_count,
                "average_grade": float(class_avg) if class_avg is not None else None,
                "at_risk_count": at_risk_count,
            })

        return result_data

    def get_class_heatmap(
        self,
        *,
        current_user: CurrentUser,
        class_id: UUID,
        period: str | None = None,
        year: str | None = None,
    ) -> dict:
        """
        Returns Heatmap Matrix: Student x Subject.
        All averages are pre-calculated.
        """
        school_id = self._require_school_id(current_user)
        students = self.session.exec(
            select(Student).where(Student.class_id == class_id, Student.school_id == school_id)
        ).all()
        if not students:
            return {}

        student_tzs = [s.student_tz for s in students]

        grade_query = select(Grade).where(Grade.school_id == school_id, Grade.student_tz.in_(student_tzs))
        if year:
            grade_query = grade_query.where(Grade.year == year)
        if period:
            grade_query = grade_query.where(Grade.period == period)
        grades = self.session.exec(grade_query).all()

        student_data = {s.student_tz: {"name": s.student_name, "grades": {}} for s in students}
        all_subjects: set[str] = set()

        for g in grades:
            if g.student_tz in student_data:
                student_data[g.student_tz]["grades"][g.subject_name] = g.grade
                all_subjects.add(g.subject_name)

        # Get per-student averages via SQL
        avg_query = (
            select(Grade.student_tz, func.avg(Grade.grade))
            .where(Grade.school_id == school_id, Grade.student_tz.in_(student_tzs))
            .group_by(Grade.student_tz)
        )
        if year:
            avg_query = avg_query.where(Grade.year == year)
        if period:
            avg_query = avg_query.where(Grade.period == period)
        avg_map = {row[0]: float(row[1]) for row in self.session.exec(avg_query).all()}

        student_rows = []
        for tz, s_data in student_data.items():
            student_rows.append({
                "student_name": s_data["name"],
                "student_tz": tz,
                "grades": s_data["grades"],
                "average": avg_map.get(tz, 0),
            })

        return {
            "subjects": all_subjects,
            "students": student_rows,
        }

    def get_top_bottom_students(
        self,
        *,
        current_user: CurrentUser,
        class_id: UUID,
        period: str | None = None,
        top_n: int = 5,
        bottom_n: int = 5,
        year: str | None = None,
    ) -> dict:
        """
        Returns sorted students with pre-calculated averages.
        """
        school_id = self._require_school_id(current_user)
        students = self.session.exec(
            select(Student).where(Student.class_id == class_id, Student.school_id == school_id)
        ).all()
        if not students:
            return {"students": [], "top_n": top_n, "bottom_n": bottom_n}

        student_tzs = [s.student_tz for s in students]
        student_name_map = {s.student_tz: s.student_name for s in students}

        # Get averages via SQL GROUP BY
        avg_query = (
            select(Grade.student_tz, func.avg(Grade.grade).label("avg_grade"))
            .where(Grade.school_id == school_id, Grade.student_tz.in_(student_tzs))
            .group_by(Grade.student_tz)
        )
        if year:
            avg_query = avg_query.where(Grade.year == year)
        if period:
            avg_query = avg_query.where(Grade.period == period)
        avg_rows = self.session.exec(avg_query).all()

        student_averages = []
        for tz, avg in avg_rows:
            student_averages.append({
                "student_name": student_name_map.get(tz, ""),
                "student_tz": tz,
                "average": float(avg),
            })

        return {
            "students": student_averages,
            "top_n": top_n,
            "bottom_n": bottom_n,
        }
