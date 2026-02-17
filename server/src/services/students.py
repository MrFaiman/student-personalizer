from uuid import UUID

from sqlmodel import Session, func, select

from ..constants import (
    AT_RISK_GRADE_THRESHOLD,
    ATTENDANCE_WEIGHT,
    ATTENDANCE_WEIGHT_NO_GRADES,
    BEHAVIOR_WEIGHT,
    BEHAVIOR_WEIGHT_NO_GRADES,
    DEFAULT_PAGE_SIZE,
    GRADE_WEIGHT,
    MAX_PAGE_SIZE,
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
    ) -> dict:
        """
        List students with filters and related data.
        Returns a dict containing all necessary data for the view.
        """
        # 1. Build Query
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
            if period:
                subquery = subquery.where(Grade.period == period)
            
            query = query.where(Student.student_tz.in_(subquery))

        # 2. total count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.session.exec(count_query).one()

        # 3. paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        students = self.session.exec(query).all()

        if not students:
             return {
                "items": [],
                "total": total,
                "page": page,
                "page_size": page_size,
                "classes_map": {},
                "student_grades": {},
                "student_attendance": {}
            }

        # 4. fetch related data
        student_tzs = [s.student_tz for s in students]
        class_ids = {s.class_id for s in students if s.class_id}

        classes_map = {}
        if class_ids:
            classes = self.session.exec(select(Class).where(Class.id.in_(class_ids))).all()
            classes_map = {c.id: c for c in classes}

        grade_query = select(Grade).where(Grade.student_tz.in_(student_tzs))
        if period:
            grade_query = grade_query.where(Grade.period == period)
        all_grades = self.session.exec(grade_query).all()

        student_grades: dict[str, list[float]] = {tz: [] for tz in student_tzs}
        for g in all_grades:
            if g.student_tz in student_grades:
                student_grades[g.student_tz].append(g.grade)

        att_query = select(AttendanceRecord).where(AttendanceRecord.student_tz.in_(student_tzs))
        if period:
            att_query = att_query.where(AttendanceRecord.period == period)
        all_attendance = self.session.exec(att_query).all()

        student_attendance: dict[str, list[AttendanceRecord]] = {tz: [] for tz in student_tzs}
        for a in all_attendance:
            if a.student_tz in student_attendance:
                student_attendance[a.student_tz].append(a)

        return {
            "items": students,
            "total": total,
            "page": page,
            "page_size": page_size,
            "classes_map": classes_map,
            "student_grades": student_grades,
            "student_attendance": student_attendance,
        }

    def get_student_detail(self, student_tz: str, period: str | None = None) -> dict | None:
        """Get flattened detailed student data."""
        student = self.session.get(Student, student_tz)
        if not student:
            return None

        cls = self.session.get(Class, student.class_id)
        
        # Grades
        grade_query = select(Grade).where(Grade.student_tz == student_tz)
        if period:
            grade_query = grade_query.where(Grade.period == period)
        grades = self.session.exec(grade_query).all()

        # Attendance
        att_query = select(AttendanceRecord).where(AttendanceRecord.student_tz == student_tz)
        if period:
            att_query = att_query.where(AttendanceRecord.period == period)
        attendance_records = self.session.exec(att_query).all()

        # Performance Score Calculation Logic
        performance_score = self._calculate_performance_score(student_tz, period, grades, attendance_records)

        return {
            "student": student,
            "class": cls,
            "grades": grades,
            "attendance": attendance_records,
            "performance_score": performance_score
        }

    def _calculate_performance_score(self, student_tz: str, period: str | None, student_grades: list[Grade], attendance_records: list[AttendanceRecord]) -> float | None:
        """Internal logic to calculate performance score percentile."""
        
        # Current logic requires fetching ALL students stats to calculate percentile. 
        # This is heavy but extracted verbatim from the router. A better approach would be ensuring analytics are pre-calculated.
        # For this refactor, I will preserve logic.
        
        total_students_count = self.session.exec(select(func.count(Student.student_tz))).one()
        if total_students_count <= 1:
            return None

        # 1. Avg grades for all
        avg_query = select(Grade.student_tz, func.avg(Grade.grade)).group_by(Grade.student_tz)
        if period:
            avg_query = avg_query.where(Grade.period == period)
        all_avg_grades = self.session.exec(avg_query).all()
        avg_grades_map = {row[0]: row[1] for row in all_avg_grades}

        # 2. Attendance stats for all
        att_stats_query = select(
            AttendanceRecord.student_tz, 
            func.sum(AttendanceRecord.total_absences),
            func.sum(AttendanceRecord.total_negative_events),
            func.sum(AttendanceRecord.total_positive_events)
        ).group_by(AttendanceRecord.student_tz)
        if period:
            att_stats_query = att_stats_query.where(AttendanceRecord.period == period)
        all_att_stats = self.session.exec(att_stats_query).all()
        att_stats_map = {
            row[0]: {
                "absences": row[1] or 0, 
                "negative": row[2] or 0, 
                "positive": row[3] or 0
            } 
            for row in all_att_stats
        }

        # 3. Build stats list
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
                "positive": s_att["positive"]
            })

        # 4. Calculate Percentiles
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
