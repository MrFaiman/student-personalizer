from uuid import UUID

from sqlalchemy import case, literal
from sqlmodel import Session, col, func, select

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


class StudentService:
    """Core service for Student domain logic."""

    def __init__(self, session: Session):
        self.session = session

    def list_students(
        self,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        class_id: UUID | None = None,
        search: str | None = None,
        at_risk_only: bool = False,
        period: str | None = None,
        year: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> dict:
        """List students with filters and related data. Returns a dict for the view."""
        query = select(Student)

        if class_id:
            query = query.where(Student.class_id == class_id)
        if search:
            query = query.where(Student.student_name.contains(search))

        if at_risk_only:
            subquery = (
                select(Grade.student_tz)
                .group_by(Grade.student_tz)
                .having(func.avg(Grade.grade) < AT_RISK_GRADE_THRESHOLD)
            )
            if year:
                subquery = subquery.where(Grade.year == year)
            if period:
                subquery = subquery.where(Grade.period == period)
            query = query.where(Student.student_tz.in_(subquery))

        count_query = select(func.count()).select_from(query.subquery())
        total = self.session.exec(count_query).one()

        # Apply SQL-level sorting for direct Student columns
        if sort_by == "student_name":
            query = query.order_by(Student.student_name.desc() if sort_order == "desc" else Student.student_name.asc())

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

        # Aggregate grades per student in SQL
        grade_avg_query = (
            select(Grade.student_tz, func.avg(Grade.grade))
            .where(Grade.student_tz.in_(student_tzs))
            .group_by(Grade.student_tz)
        )
        if year:
            grade_avg_query = grade_avg_query.where(Grade.year == year)
        if period:
            grade_avg_query = grade_avg_query.where(Grade.period == period)
        grade_avgs = {row[0]: float(row[1]) for row in self.session.exec(grade_avg_query).all()}

        # Aggregate attendance per student in SQL
        att_agg_query = (
            select(
                AttendanceRecord.student_tz,
                func.sum(AttendanceRecord.total_absences),
                func.sum(AttendanceRecord.total_negative_events),
                func.sum(AttendanceRecord.total_positive_events),
            )
            .where(AttendanceRecord.student_tz.in_(student_tzs))
            .group_by(AttendanceRecord.student_tz)
        )
        if year:
            att_agg_query = att_agg_query.where(AttendanceRecord.year == year)
        if period:
            att_agg_query = att_agg_query.where(AttendanceRecord.period == period)
        att_stats = {
            row[0]: {
                "total_absences": row[1] or 0,
                "total_negative_events": row[2] or 0,
                "total_positive_events": row[3] or 0,
            }
            for row in self.session.exec(att_agg_query).all()
        }

        result_items = []
        for student in students:
            cls = classes_map.get(student.class_id)
            grade_level = cls.grade_level if cls else None
            class_name = cls.class_name if cls else "Unknown"

            avg_grade = grade_avgs.get(student.student_tz)
            a = att_stats.get(student.student_tz, {"total_absences": 0, "total_negative_events": 0, "total_positive_events": 0})

            is_at_risk = avg_grade is not None and avg_grade < AT_RISK_GRADE_THRESHOLD

            result_items.append({
                "student_tz": student.student_tz,
                "student_name": student.student_name,
                "class_id": student.class_id,
                "class_name": class_name,
                "grade_level": grade_level,
                "average_grade": avg_grade,
                "total_absences": a["total_absences"],
                "total_negative_events": a["total_negative_events"],
                "total_positive_events": a["total_positive_events"],
                "is_at_risk": is_at_risk,
            })

        # Sort by computed columns in Python
        if sort_by in ("average_grade", "total_absences", "class_name"):
            reverse = sort_order == "desc"
            if sort_by == "average_grade":
                result_items.sort(key=lambda x: (x["average_grade"] is None, x["average_grade"] or 0), reverse=reverse)
            elif sort_by == "total_absences":
                result_items.sort(key=lambda x: x["total_absences"], reverse=reverse)
            elif sort_by == "class_name":
                result_items.sort(key=lambda x: x["class_name"] or "", reverse=reverse)

        return {
            "items": result_items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_student_detail(self, student_tz: str, period: str | None = None, year: str | None = None) -> dict | None:
        """Get flattened detailed student data as a dict for the view."""
        student = self.session.get(Student, student_tz)
        if not student:
            return None

        cls = self.session.get(Class, student.class_id)

        # Get average grade via SQL
        avg_query = select(func.avg(Grade.grade)).where(Grade.student_tz == student_tz)
        if year:
            avg_query = avg_query.where(Grade.year == year)
        if period:
            avg_query = avg_query.where(Grade.period == period)
        avg_grade_raw = self.session.exec(avg_query).one()
        avg_grade = float(avg_grade_raw) if avg_grade_raw is not None else None

        # Get attendance stats via SQL
        att_query = select(
            func.sum(AttendanceRecord.total_absences),
            func.sum(AttendanceRecord.total_negative_events),
            func.sum(AttendanceRecord.total_positive_events),
        ).where(AttendanceRecord.student_tz == student_tz)
        if year:
            att_query = att_query.where(AttendanceRecord.year == year)
        if period:
            att_query = att_query.where(AttendanceRecord.period == period)
        att_row = self.session.exec(att_query).one()

        total_absences = att_row[0] or 0
        total_negative_events = att_row[1] or 0
        total_positive_events = att_row[2] or 0

        is_at_risk = avg_grade is not None and avg_grade < AT_RISK_GRADE_THRESHOLD

        performance_score = self._calculate_performance_score(student_tz, period, year)

        grade_level = cls.grade_level if cls else None
        class_name = cls.class_name if cls else "Unknown"

        return {
            "student_tz": student.student_tz,
            "student_name": student.student_name,
            "class_id": student.class_id,
            "class_name": class_name,
            "grade_level": grade_level,
            "average_grade": avg_grade,
            "total_absences": total_absences,
            "total_negative_events": total_negative_events,
            "total_positive_events": total_positive_events,
            "is_at_risk": is_at_risk,
            "performance_score": performance_score,
        }

    def get_dashboard_stats(
        self,
        class_id: UUID | None = None,
        period: str | None = None,
        year: str | None = None,
    ) -> dict:
        """Get dashboard statistics as a dict for the view."""
        class_query = select(Class)
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

        # SQL: per-student average grade, grouped by class
        student_avg_subquery = (
            select(
                Grade.student_tz,
                func.avg(Grade.grade).label("avg_grade"),
            )
            .group_by(Grade.student_tz)
        )
        if year:
            student_avg_subquery = student_avg_subquery.where(Grade.year == year)
        if period:
            student_avg_subquery = student_avg_subquery.where(Grade.period == period)
        student_avg_sub = student_avg_subquery.subquery()

        # Join with students to get class_id, then aggregate per class
        class_stats_query = (
            select(
                Student.class_id,
                func.count(col(Student.student_tz)).label("student_count"),
                func.avg(student_avg_sub.c.avg_grade).label("class_avg"),
                func.count(case((student_avg_sub.c.avg_grade < AT_RISK_GRADE_THRESHOLD, literal(1)))).label("at_risk_count"),
            )
            .outerjoin(student_avg_sub, Student.student_tz == student_avg_sub.c.student_tz)
            .where(Student.class_id.in_(class_map.keys()))
            .group_by(Student.class_id)
        )
        class_rows = self.session.exec(class_stats_query).all()

        total_students = 0
        total_at_risk = 0
        all_avgs = []
        class_responses = []

        for row in class_rows:
            cid, student_count, class_avg, at_risk_count = row
            cls = class_map.get(cid)
            if not cls:
                continue

            total_students += student_count
            total_at_risk += at_risk_count
            if class_avg is not None:
                all_avgs.append(class_avg)

            class_responses.append({
                "id": cls.id,
                "class_name": cls.class_name,
                "grade_level": cls.grade_level,
                "student_count": student_count,
                "average_grade": float(class_avg) if class_avg is not None else None,
                "at_risk_count": at_risk_count,
            })

        overall_avg = sum(all_avgs) / len(all_avgs) if all_avgs else None

        return {
            "total_students": total_students,
            "average_grade": overall_avg,
            "at_risk_count": total_at_risk,
            "total_classes": len(classes),
            "classes": class_responses,
        }

    def get_student_grades(self, student_tz: str, period: str | None = None, year: str | None = None) -> list[dict] | None:
        """Get all grades for a student as a list of dicts for the view."""
        student = self.session.get(Student, student_tz)
        if not student:
            return None

        query = select(Grade).where(Grade.student_tz == student_tz)
        if year:
            query = query.where(Grade.year == year)
        if period:
            query = query.where(Grade.period == period)

        grades = self.session.exec(query).all()

        return [
            {
                "id": g.id,
                "subject": g.subject_name,
                "teacher_name": g.teacher_name,
                "grade": g.grade,
                "period": g.period,
                "year": g.year,
            }
            for g in grades
        ]

    def get_student_attendance(self, student_tz: str, period: str | None = None, year: str | None = None) -> list[dict] | None:
        """Get all attendance records for a student as a list of dicts for the view."""
        student = self.session.get(Student, student_tz)
        if not student:
            return None

        query = select(AttendanceRecord).where(AttendanceRecord.student_tz == student_tz)
        if year:
            query = query.where(AttendanceRecord.year == year)
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
                "year": r.year,
            }
            for r in records
        ]

    def _calculate_performance_score(self, student_tz: str, period: str | None, year: str | None = None) -> float | None:
        """Internal logic to calculate performance score percentile."""
        total_students_count = self.session.exec(select(func.count(Student.student_tz))).one()
        if total_students_count <= 1:
            return None

        # Get all student average grades via SQL
        avg_query = select(Grade.student_tz, func.avg(Grade.grade)).group_by(Grade.student_tz)
        if year:
            avg_query = avg_query.where(Grade.year == year)
        if period:
            avg_query = avg_query.where(Grade.period == period)
        all_avg_grades = self.session.exec(avg_query).all()
        avg_grades_map = {row[0]: row[1] for row in all_avg_grades}

        # Get all student attendance stats via SQL
        att_stats_query = select(
            AttendanceRecord.student_tz,
            func.sum(AttendanceRecord.total_absences),
            func.sum(AttendanceRecord.total_negative_events),
            func.sum(AttendanceRecord.total_positive_events),
        ).group_by(AttendanceRecord.student_tz)
        if year:
            att_stats_query = att_stats_query.where(AttendanceRecord.year == year)
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

        all_student_tzs = self.session.exec(select(Student.student_tz)).all()
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

    def get_student_timeline(self, student_tz: str) -> dict | None:
        """Query grades/attendance grouped by year+period, return list of timeline points."""
        student = self.session.get(Student, student_tz)
        if not student:
            return None

        # Aggregate grades at DB level: avg grade per (year, period)
        grades_agg_query = (
            select(
                Grade.year,
                Grade.period,
                func.avg(Grade.grade).label("avg_grade"),
            )
            .where(Grade.student_tz == student_tz)
            .group_by(Grade.year, Grade.period)
        )
        grade_rows = self.session.exec(grades_agg_query).all()

        # Aggregate attendance at DB level: sum lessons/attendance/absences per (year, period)
        att_agg_query = (
            select(
                AttendanceRecord.year,
                AttendanceRecord.period,
                func.sum(AttendanceRecord.lessons_reported).label("total_lessons"),
                func.sum(AttendanceRecord.attendance).label("total_attended"),
                func.sum(AttendanceRecord.total_absences).label("total_absences"),
            )
            .where(AttendanceRecord.student_tz == student_tz)
            .group_by(AttendanceRecord.year, AttendanceRecord.period)
        )
        att_rows = self.session.exec(att_agg_query).all()

        # Get per-subject grades for the subjects breakdown
        subject_grades_query = select(Grade.year, Grade.period, Grade.subject_name, Grade.grade).where(Grade.student_tz == student_tz)
        subject_grades = self.session.exec(subject_grades_query).all()

        timeline_map: dict[tuple[str, str], dict] = {}

        for row in grade_rows:
            key = (row.year, row.period)
            timeline_map[key] = {
                "avg_grade": round(float(row.avg_grade), 1) if row.avg_grade is not None else None,
                "attendance_rate": None,
                "absences": 0,
                "subjects": [],
            }

        for row in att_rows:
            key = (row.year, row.period)
            if key not in timeline_map:
                timeline_map[key] = {"avg_grade": None, "attendance_rate": None, "absences": 0, "subjects": []}
            total_lessons = row.total_lessons or 0
            total_attended = row.total_attended or 0
            timeline_map[key]["absences"] = row.total_absences or 0
            timeline_map[key]["attendance_rate"] = round((total_attended / total_lessons) * 100, 1) if total_lessons > 0 else None

        for sg in subject_grades:
            key = (sg.year, sg.period)
            if key in timeline_map:
                timeline_map[key]["subjects"].append({"subject": sg.subject_name, "grade": sg.grade})

        timeline = []
        for (year, period), data in timeline_map.items():
            label = f"{year} {period}" if year else period
            timeline.append({
                "year": year or "",
                "period": period,
                "label": label,
                "average_grade": data["avg_grade"],
                "attendance_rate": data["attendance_rate"],
                "total_absences": data["absences"],
                "subjects": data["subjects"],
            })

        # Sort chronologically: empty year sorts last, then by period
        timeline.sort(key=lambda x: (x["year"] or "\uffff", x["period"]))

        return {
            "student_tz": student.student_tz,
            "student_name": student.student_name,
            "timeline": timeline,
        }
