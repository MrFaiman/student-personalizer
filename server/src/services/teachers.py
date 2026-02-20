from uuid import UUID

from sqlmodel import Session, func, select

from ..constants import AT_RISK_GRADE_THRESHOLD
from ..models import Class, Grade, Student, Teacher


class TeacherService:
    """Core service for Teacher domain logic."""

    def __init__(self, session: Session):
        self.session = session

    def list_teachers(self, period: str | None = None) -> list[str]:
        """Get list of all teacher names with available grades."""
        query = select(Grade.teacher_name).distinct().where(Grade.teacher_name.is_not(None))
        if period:
            query = query.where(Grade.period == period)
        return list(self.session.exec(query).all())

    def get_teachers_list_with_stats(
        self, period: str | None = None, grade_level: str | None = None
    ) -> list[dict]:
        """Get list of all teachers with summary stats (pre-calculated)."""
        # SQL: aggregate grades grouped by teacher
        query = (
            select(
                Grade.teacher_name,
                Grade.teacher_id,
                func.avg(Grade.grade).label("avg_grade"),
                func.count(func.distinct(Grade.student_tz)).label("student_count"),
                func.array_agg(func.distinct(Grade.subject)).label("subjects"),
            )
            .where(Grade.teacher_name.isnot(None))
            .group_by(Grade.teacher_name, Grade.teacher_id)
        )
        if period:
            query = query.where(Grade.period == period)

        if grade_level:
            query = (
                query.join(Student, Grade.student_tz == Student.student_tz)
                .join(Class, Student.class_id == Class.id)
                .where(Class.grade_level == grade_level)
            )

        rows = self.session.exec(query).all()

        results = []
        for name, tid, avg_grade, student_count, subjects in rows:
            results.append({
                "id": tid,
                "name": name,
                "student_count": student_count,
                "average_grade": float(avg_grade) if avg_grade is not None else 0,
                "subjects": set(subjects) if subjects else set(),
            })

        return results

    def get_teacher_stats(self, teacher_name: str, period: str | None = None) -> dict:
        """Get raw grade data for a teacher."""
        query = select(Grade).where(Grade.teacher_name == teacher_name)
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
        if not teacher:
            return None

        query = select(Grade).where(Grade.teacher_id == teacher_id)
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

        # Overall stats via SQL
        stats_query = (
            select(
                func.avg(Grade.grade).label("avg_grade"),
                func.count(func.distinct(Grade.student_tz)).label("student_count"),
            )
            .where(Grade.teacher_id == teacher_id)
        )
        if period:
            stats_query = stats_query.where(Grade.period == period)
        stats_row = self.session.exec(stats_query).one()
        avg_grade = float(stats_row[0]) if stats_row[0] is not None else 0

        # At-risk: students with avg < threshold for this teacher
        at_risk_query = (
            select(func.count())
            .select_from(
                select(Grade.student_tz)
                .where(Grade.teacher_id == teacher_id)
                .group_by(Grade.student_tz)
                .having(func.avg(Grade.grade) < AT_RISK_GRADE_THRESHOLD)
                .subquery()
            )
        )
        if period:
            at_risk_inner = (
                select(Grade.student_tz)
                .where(Grade.teacher_id == teacher_id)
                .where(Grade.period == period)
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
