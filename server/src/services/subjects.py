from uuid import UUID

from sqlmodel import Session, func, select

from ..auth.current_user import CurrentUser
from ..constants import AT_RISK_GRADE_THRESHOLD
from ..models import Class, Grade, Student, Subject


class SubjectService:
    """Core service for Subject domain logic."""

    def __init__(self, session: Session):
        self.session = session

    def _require_school_id(self, current_user: CurrentUser) -> int:
        if current_user.school_id is None:
            raise ValueError("School scope required")
        return current_user.school_id

    def list_subjects(self, *, current_user: CurrentUser, period: str | None = None, year: str | None = None) -> list[str]:
        """Get list of all subject names with available grades."""
        school_id = self._require_school_id(current_user)
        query = (
            select(Grade.subject_name)
            .distinct()
            .where(Grade.school_id == school_id, Grade.subject_name.is_not(None))
        )
        if year:
            query = query.where(Grade.year == year)
        if period:
            query = query.where(Grade.period == period)
        return list(self.session.exec(query).all())

    def get_subjects_list_with_stats(
        self, *, current_user: CurrentUser, period: str | None = None, grade_level: str | None = None, year: str | None = None
    ) -> list[dict]:
        """Get list of all subjects with summary stats (pre-calculated)."""
        school_id = self._require_school_id(current_user)
        # SQL: aggregate grades grouped by subject
        query = (
            select(
                Grade.subject_name,
                Grade.subject_id,
                func.avg(Grade.grade).label("avg_grade"),
                func.count(func.distinct(Grade.student_tz)).label("student_count"),
                func.array_agg(func.distinct(Grade.teacher_name)).label("teachers"),
            )
            .where(Grade.school_id == school_id, Grade.subject_name.isnot(None))
            .group_by(Grade.subject_name, Grade.subject_id)
        )
        if year:
            query = query.where(Grade.year == year)
        if period:
            query = query.where(Grade.period == period)

        if grade_level:
            query = (
                query.join(Student, Grade.student_tz == Student.student_tz)
                .join(Class, Student.class_id == Class.id)
                .where(Class.school_id == school_id, Student.school_id == school_id, Class.grade_level == grade_level)
            )

        rows = self.session.exec(query).all()

        results = []
        for name, sid, avg_grade, student_count, teachers in rows:
            results.append({
                "id": sid,
                "name": name,
                "student_count": student_count,
                "average_grade": float(avg_grade) if avg_grade is not None else 0,
                "teachers": set(teachers) if teachers else set(),
            })

        return results

    def get_subject_stats(
        self,
        *,
        current_user: CurrentUser,
        subject_name: str,
        period: str | None = None,
        year: str | None = None,
    ) -> dict:
        """Get raw grade data for a subject."""
        school_id = self._require_school_id(current_user)
        query = select(Grade).where(Grade.school_id == school_id, Grade.subject_name == subject_name)
        if year:
            query = query.where(Grade.year == year)
        if period:
            query = query.where(Grade.period == period)

        grades = self.session.exec(query).all()

        if not grades:
            return {"total_students": 0}

        student_tzs = set(g.student_tz for g in grades)

        return {
            "subject_name": subject_name,
            "total_students": len(student_tzs),
            "grades": [g.grade for g in grades],
            "teachers": set(g.teacher_name for g in grades if g.teacher_name),
        }

    def get_subject_detail(
        self,
        *,
        current_user: CurrentUser,
        subject_id: UUID,
        period: str | None = None,
        year: str | None = None,
    ) -> dict | None:
        """Get detailed analytics for a specific subject (pre-calculated)."""
        school_id = self._require_school_id(current_user)
        subject = self.session.get(Subject, subject_id)
        if not subject or subject.school_id != school_id:
            return None

        query = select(Grade).where(Grade.school_id == school_id, Grade.subject_id == subject_id)
        if year:
            query = query.where(Grade.year == year)
        if period:
            query = query.where(Grade.period == period)
        grades = self.session.exec(query).all()

        if not grades:
            return {
                "subject": subject,
                "stats": {
                    "student_count": 0,
                    "average_grade": 0,
                    "at_risk_count": 0,
                    "classes_count": 0,
                },
                "classes": [],
                "grades": [],
                "teachers": [],
            }

        student_tzs = set(g.student_tz for g in grades)

        # Overall stats via SQL
        stats_query = (
            select(
                func.avg(Grade.grade).label("avg_grade"),
                func.count(func.distinct(Grade.student_tz)).label("student_count"),
            )
            .where(Grade.subject_id == subject_id)
        )
        if year:
            stats_query = stats_query.where(Grade.year == year)
        if period:
            stats_query = stats_query.where(Grade.period == period)
        stats_row = self.session.exec(stats_query).one()
        avg_grade = float(stats_row[0]) if stats_row[0] is not None else 0

        # At-risk: students with avg < threshold for this subject
        at_risk_inner = (
            select(Grade.student_tz)
            .where(Grade.subject_id == subject_id)
        )
        if year:
            at_risk_inner = at_risk_inner.where(Grade.year == year)
        if period:
            at_risk_inner = at_risk_inner.where(Grade.period == period)

        at_risk_inner = (
            at_risk_inner
            .group_by(Grade.student_tz)
            .having(func.avg(Grade.grade) < AT_RISK_GRADE_THRESHOLD)
            .subquery()
        )
        at_risk_query = select(func.count()).select_from(at_risk_inner)
        at_risk_students = self.session.exec(at_risk_query).one()

        # Class breakdown via SQL
        students = self.session.exec(select(Student).where(Student.student_tz.in_(student_tzs))).all()
        student_map = {s.student_tz: s for s in students}

        class_ids = set(s.class_id for s in students if s.class_id)
        classes = self.session.exec(select(Class).where(Class.id.in_(class_ids))).all() if class_ids else []
        class_map = {c.id: c for c in classes}

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
            c_avg = sum(c_grades) / len(c_grades) if c_grades else 0

            classes_data.append({
                "id": str(cls.id),
                "name": cls.class_name,
                "student_count": len(stats["students"]),
                "average_grade": round(c_avg, 1),
                "at_risk_count": stats["at_risk"],
            })

        return {
            "subject": subject,
            "stats": {
                "student_count": len(student_tzs),
                "average_grade": round(avg_grade, 1),
                "at_risk_count": at_risk_students,
                "classes_count": len(class_ids),
            },
            "classes": classes_data,
            "grades": grades,
            "teachers": set(g.teacher_name for g in grades if g.teacher_name),
        }
