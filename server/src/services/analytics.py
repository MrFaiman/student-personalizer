from uuid import UUID

from sqlalchemy import case, literal
from sqlmodel import Session, func, select

from ..constants import AT_RISK_GRADE_THRESHOLD
from ..models import AttendanceRecord, Class, Grade, Student, Teacher


class AnalyticsService:
    """Core service for functional/layer analytics and advanced comparisons."""

    def __init__(self, session: Session):
        self.session = session

    def _student_tz_filter(self, grade_level: str | None) -> list[str] | None:
        """Get student_tzs filtered by grade_level, or None if no filter."""
        if not grade_level:
            return None
        query = (
            select(Student.student_tz)
            .join(Class, Student.class_id == Class.id)
            .where(Class.grade_level == grade_level)
        )
        return list(self.session.exec(query).all())

    def get_layer_kpis(self, period: str | None = None, grade_level: str | None = None) -> dict:
        """Returns Dashboard Homepage KPIs as pre-calculated dict."""
        # Build base filter conditions for grades
        grade_conditions = []
        if period:
            grade_conditions.append(Grade.period == period)

        student_tzs = self._student_tz_filter(grade_level)
        if student_tzs is not None:
            if not student_tzs:
                return {"layer_average": None, "avg_absences": 0.0, "at_risk_count": 0, "total_students": 0}
            grade_conditions.append(Grade.student_tz.in_(student_tzs))

        # Overall average grade
        avg_query = select(func.avg(Grade.grade))
        for cond in grade_conditions:
            avg_query = avg_query.where(cond)
        layer_average = self.session.exec(avg_query).one()

        # Total distinct students and at-risk count via subquery
        student_avg_query = (
            select(Grade.student_tz, func.avg(Grade.grade).label("avg_grade"))
            .group_by(Grade.student_tz)
        )
        for cond in grade_conditions:
            student_avg_query = student_avg_query.where(cond)
        student_avg_sub = student_avg_query.subquery()

        stats_query = select(
            func.count().label("total"),
            func.count(case((student_avg_sub.c.avg_grade < AT_RISK_GRADE_THRESHOLD, literal(1)))).label("at_risk"),
        ).select_from(student_avg_sub)
        stats_row = self.session.exec(stats_query).one()
        total_students = stats_row[0]
        at_risk_count = stats_row[1]

        # Average absences
        att_query = select(func.avg(AttendanceRecord.total_absences))
        if period:
            att_query = att_query.where(AttendanceRecord.period == period)
        if student_tzs is not None:
            att_query = att_query.where(AttendanceRecord.student_tz.in_(student_tzs))
        avg_absences = self.session.exec(att_query).one() or 0.0

        return {
            "layer_average": float(layer_average) if layer_average is not None else None,
            "avg_absences": float(avg_absences),
            "at_risk_count": at_risk_count,
            "total_students": total_students,
        }

    def get_class_comparison(self, period: str | None = None, grade_level: str | None = None) -> list[dict]:
        """Returns class comparison data with pre-calculated averages."""
        class_query = select(Class)
        if grade_level:
            class_query = class_query.where(Class.grade_level == grade_level)
        classes = self.session.exec(class_query).all()

        if not classes:
            return []

        class_map = {c.id: c for c in classes}

        # SQL: AVG(grade), COUNT(DISTINCT student_tz) grouped by class_id
        query = (
            select(
                Student.class_id,
                func.avg(Grade.grade).label("avg_grade"),
                func.count(func.distinct(Grade.student_tz)).label("student_count"),
            )
            .join(Student, Grade.student_tz == Student.student_tz)
            .where(Student.class_id.in_(class_map.keys()))
            .group_by(Student.class_id)
        )
        if period:
            query = query.where(Grade.period == period)

        rows = self.session.exec(query).all()

        result = []
        for cid, avg_grade, student_count in rows:
            cls = class_map.get(cid)
            if cls and student_count > 0:
                result.append({
                    "class": cls,
                    "average_grade": float(avg_grade) if avg_grade is not None else 0,
                    "student_count": student_count,
                })

        return result

    def get_student_radar(self, student_tz: str, period: str | None = None) -> dict:
        """Returns subject -> average grade mapping."""
        query = (
            select(Grade.subject_name, func.avg(Grade.grade))
            .where(Grade.student_tz == student_tz)
            .group_by(Grade.subject_name)
        )
        if period:
            query = query.where(Grade.period == period)

        rows = self.session.exec(query).all()
        return {subject: float(avg) for subject, avg in rows}

    def get_metadata_options(self) -> dict:
        """Get available filter options."""
        periods = self.session.exec(select(Grade.period).distinct()).all()
        levels = self.session.exec(select(Class.grade_level).distinct()).all()
        teachers = self.session.exec(select(Grade.teacher_name).distinct()).all()
        valid_teachers = [t for t in teachers if t is not None]

        return {
            "periods": list(set(periods)),
            "grade_levels": list(set(levels)),
            "teachers": valid_teachers,
        }

    def get_period_comparison(
        self,
        period_a: str,
        period_b: str,
        comparison_type: str = "class",
        grade_level: str | None = None,
        class_id: str | None = None,
    ) -> dict:
        """Compare average grades between two periods."""
        def get_grades_for_period(period: str) -> list[Grade]:
            query = select(Grade).where(Grade.period == period)

            if class_id:
                query = query.join(
                    Student, Grade.student_tz == Student.student_tz
                ).where(Student.class_id == UUID(class_id))
            elif grade_level:
                query = (
                    query.join(Student, Grade.student_tz == Student.student_tz)
                    .join(Class, Student.class_id == Class.id)
                    .where(Class.grade_level == grade_level)
                )

            return list(self.session.exec(query).all())

        grades_a = get_grades_for_period(period_a)
        grades_b = get_grades_for_period(period_b)

        if comparison_type == "class":
            return self._compare_by_class(grades_a, grades_b, period_a, period_b)
        elif comparison_type == "subject_teacher":
            return self._compare_by_subject_teacher(grades_a, grades_b, period_a, period_b)
        else:  # subject
            return self._compare_by_subject(grades_a, grades_b, period_a, period_b)

    def _get_student_class_mapping(self, student_tzs: set[str]) -> tuple[dict, dict]:
        """Get student-to-class mapping and class info."""
        if not student_tzs:
            return {}, {}

        students = self.session.exec(
            select(Student).where(Student.student_tz.in_(student_tzs))
        ).all()
        student_class_map = {s.student_tz: s.class_id for s in students}

        class_ids = set(cid for cid in student_class_map.values() if cid)
        classes = []
        if class_ids:
            classes = self.session.exec(select(Class).where(Class.id.in_(class_ids))).all()
        class_map = {c.id: c for c in classes}

        return student_class_map, class_map

    def _compare_by_class(
        self, grades_a: list, grades_b: list, period_a: str, period_b: str
    ) -> dict:
        """Compare class averages between periods."""
        student_tzs = set(g.student_tz for g in grades_a + grades_b)
        student_class_map, class_map = self._get_student_class_mapping(student_tzs)

        def aggregate_by_class(grades: list) -> dict:
            class_data: dict = {}
            for g in grades:
                cid = student_class_map.get(g.student_tz)
                if cid:
                    if cid not in class_data:
                        class_data[cid] = {"grades": [], "students": set()}
                    class_data[cid]["grades"].append(g.grade)
                    class_data[cid]["students"].add(g.student_tz)
            return class_data

        data_a = aggregate_by_class(grades_a)
        data_b = aggregate_by_class(grades_b)

        result = []
        all_class_ids = set(data_a.keys()) | set(data_b.keys())

        for cid in all_class_ids:
            cls = class_map.get(cid)
            if not cls:
                continue

            result.append({
                "id": str(cid),
                "name": cls.class_name,
                "grades_a": data_a.get(cid, {}).get("grades", []),
                "grades_b": data_b.get(cid, {}).get("grades", []),
                "student_count_a": len(data_a.get(cid, {}).get("students", set())),
                "student_count_b": len(data_b.get(cid, {}).get("students", set())),
            })

        return {
            "comparison_type": "class",
            "period_a": period_a,
            "period_b": period_b,
            "data": result,
        }

    def _compare_by_subject_teacher(
        self, grades_a: list, grades_b: list, period_a: str, period_b: str
    ) -> dict:
        """Compare subject-teacher combination averages."""
        def aggregate_by_subject_teacher(grades: list) -> dict:
            data: dict = {}
            for g in grades:
                key = f"{g.subject_name}|{g.teacher_name or 'Unknown'}"
                if key not in data:
                    data[key] = {
                        "grades": [],
                        "students": set(),
                        "subject": g.subject_name,
                        "teacher_name": g.teacher_name,
                    }
                data[key]["grades"].append(g.grade)
                data[key]["students"].add(g.student_tz)
            return data

        data_a = aggregate_by_subject_teacher(grades_a)
        data_b = aggregate_by_subject_teacher(grades_b)

        result = []
        all_keys = set(data_a.keys()) | set(data_b.keys())

        for key in all_keys:
            a_info = data_a.get(key, {})
            b_info = data_b.get(key, {})

            subject = a_info.get("subject") or b_info.get("subject")
            teacher = a_info.get("teacher_name") or b_info.get("teacher_name")

            result.append({
                "id": key,
                "subject": subject,
                "teacher_name": teacher,
                "grades_a": a_info.get("grades", []),
                "grades_b": b_info.get("grades", []),
                "student_count_a": len(a_info.get("students", set())),
                "student_count_b": len(b_info.get("students", set())),
            })

        return {
            "comparison_type": "subject_teacher",
            "period_a": period_a,
            "period_b": period_b,
            "data": result,
        }

    def _compare_by_subject(
        self, grades_a: list, grades_b: list, period_a: str, period_b: str
    ) -> dict:
        """Compare subject averages."""
        def aggregate_by_subject(grades: list) -> dict:
            data: dict = {}
            for g in grades:
                if g.subject_name not in data:
                    data[g.subject_name] = {
                        "grades": [],
                        "students": set(),
                        "teachers": set(),
                    }
                data[g.subject_name]["grades"].append(g.grade)
                data[g.subject_name]["students"].add(g.student_tz)
                if g.teacher_name:
                    data[g.subject_name]["teachers"].add(g.teacher_name)
            return data

        data_a = aggregate_by_subject(grades_a)
        data_b = aggregate_by_subject(grades_b)

        result = []
        all_subjects = set(data_a.keys()) | set(data_b.keys())

        for subject in all_subjects:
            a_info = data_a.get(subject, {})
            b_info = data_b.get(subject, {})

            teachers = a_info.get("teachers", set()) | b_info.get("teachers", set())

            result.append({
                "id": subject,
                "subject": subject,
                "teachers": teachers,
                "grades_a": a_info.get("grades", []),
                "grades_b": b_info.get("grades", []),
                "student_count_a": len(a_info.get("students", set())),
                "student_count_b": len(b_info.get("students", set())),
            })

        return {
            "comparison_type": "subject",
            "period_a": period_a,
            "period_b": period_b,
            "data": result,
        }

    def get_red_student_segmentation(
        self,
        period: str | None = None,
        grade_level: str | None = None,
    ) -> dict:
        """Get at-risk student segmentation by class, layer, teacher, subject."""
        # CTE 1: per-student average grades
        grade_conditions = []
        if period:
            grade_conditions.append(Grade.period == period)

        student_avg_query = (
            select(Grade.student_tz, func.avg(Grade.grade).label("avg_grade"))
            .group_by(Grade.student_tz)
        )
        for cond in grade_conditions:
            student_avg_query = student_avg_query.where(cond)
        student_avg_sub = student_avg_query.subquery()

        # Get student info with class details, joined with averages
        base_query = (
            select(
                Student.student_tz,
                Student.class_id,
                Class.class_name,
                Class.grade_level,
                student_avg_sub.c.avg_grade,
            )
            .join(student_avg_sub, Student.student_tz == student_avg_sub.c.student_tz)
            .outerjoin(Class, Student.class_id == Class.id)
        )
        if grade_level:
            base_query = base_query.where(Class.grade_level == grade_level)

        rows = self.session.exec(base_query).all()

        # Build lookup maps
        all_student_tzs = set()
        red_student_tzs = set()
        student_averages: dict[str, float] = {}
        student_class_map: dict[str, dict] = {}

        for tz, class_id, class_name, gl, avg_grade in rows:
            all_student_tzs.add(tz)
            avg_val = float(avg_grade)
            student_averages[tz] = avg_val
            student_class_map[tz] = {"class_id": class_id, "class_name": class_name, "grade_level": gl}
            if avg_val < AT_RISK_GRADE_THRESHOLD:
                red_student_tzs.add(tz)

        # Segmentation by class
        by_class: dict = {}
        for tz in all_student_tzs:
            info = student_class_map[tz]
            cid = info["class_id"]
            if cid:
                if cid not in by_class:
                    by_class[cid] = {"name": info["class_name"], "total": 0, "red": 0, "red_grades": []}
                by_class[cid]["total"] += 1
                if tz in red_student_tzs:
                    by_class[cid]["red"] += 1
                    by_class[cid]["red_grades"].append(student_averages[tz])

        by_class_result = [
            {
                "id": str(cid),
                "name": data["name"],
                "red_student_count": data["red"],
                "total_student_count": data["total"],
                "red_grades": data["red_grades"],
            }
            for cid, data in by_class.items()
        ]

        # Segmentation by layer
        by_layer: dict = {}
        for tz in all_student_tzs:
            info = student_class_map[tz]
            level = info["grade_level"]
            if level:
                if level not in by_layer:
                    by_layer[level] = {"total": 0, "red": 0, "red_grades": []}
                by_layer[level]["total"] += 1
                if tz in red_student_tzs:
                    by_layer[level]["red"] += 1
                    by_layer[level]["red_grades"].append(student_averages[tz])

        by_layer_result = [
            {
                "id": level,
                "name": level,
                "red_student_count": data["red"],
                "total_student_count": data["total"],
                "red_grades": data["red_grades"],
            }
            for level, data in by_layer.items()
        ]

        # Segmentation by teacher and subject - need grade-level data
        grade_query = select(Grade)
        if period:
            grade_query = grade_query.where(Grade.period == period)
        if all_student_tzs:
            grade_query = grade_query.where(Grade.student_tz.in_(all_student_tzs))
        grades = self.session.exec(grade_query).all()

        by_teacher: dict = {}
        for g in grades:
            if not g.teacher_name:
                continue
            if g.teacher_name not in by_teacher:
                by_teacher[g.teacher_name] = {"students": set(), "red_students": set(), "red_grades": []}
            by_teacher[g.teacher_name]["students"].add(g.student_tz)
            if g.student_tz in red_student_tzs:
                by_teacher[g.teacher_name]["red_students"].add(g.student_tz)

        for teacher_name in by_teacher:
            for tz in by_teacher[teacher_name]["red_students"]:
                by_teacher[teacher_name]["red_grades"].append(student_averages[tz])

        by_teacher_result = [
            {
                "id": name,
                "name": name,
                "red_student_count": len(data["red_students"]),
                "total_student_count": len(data["students"]),
                "red_grades": data["red_grades"],
            }
            for name, data in by_teacher.items()
        ]

        # Segmentation by subject
        by_subject: dict = {}
        for g in grades:
            if g.student_tz in red_student_tzs:
                if g.subject_name not in by_subject:
                    by_subject[g.subject_name] = {"students": set(), "grades": []}
                by_subject[g.subject_name]["students"].add(g.student_tz)
                if g.grade < AT_RISK_GRADE_THRESHOLD:
                    by_subject[g.subject_name]["grades"].append(g.grade)

        by_subject_result = [
            {
                "id": subject,
                "name": subject,
                "red_student_count": len(data["students"]),
                "total_student_count": len(red_student_tzs),
                "red_grades": data["grades"],
            }
            for subject, data in by_subject.items()
        ]

        return {
            "total_red_students": len(red_student_tzs),
            "threshold": AT_RISK_GRADE_THRESHOLD,
            "by_class": by_class_result,
            "by_layer": by_layer_result,
            "by_teacher": by_teacher_result,
            "by_subject": by_subject_result,
        }

    def get_red_student_list(
        self,
        period: str | None = None,
        grade_level: str | None = None,
        class_id: str | None = None,
        teacher_name: str | None = None,
        subject: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get paginated list of red students with details."""
        # Build base grade query with filters
        grade_conditions = []
        if period:
            grade_conditions.append(Grade.period == period)
        if teacher_name:
            grade_conditions.append(Grade.teacher_name == teacher_name)
        if subject:
            grade_conditions.append(Grade.subject_name == subject)

        # Subquery: per-student avg with HAVING < threshold
        student_avg_query = (
            select(Grade.student_tz, func.avg(Grade.grade).label("avg_grade"))
            .group_by(Grade.student_tz)
            .having(func.avg(Grade.grade) < AT_RISK_GRADE_THRESHOLD)
        )
        for cond in grade_conditions:
            student_avg_query = student_avg_query.where(cond)
        student_avg_sub = student_avg_query.subquery()

        # Join with student + class for filtering and info
        query = (
            select(
                Student.student_tz,
                Student.student_name,
                Class.class_name,
                Class.grade_level,
                student_avg_sub.c.avg_grade,
            )
            .join(student_avg_sub, Student.student_tz == student_avg_sub.c.student_tz)
            .outerjoin(Class, Student.class_id == Class.id)
        )
        if grade_level:
            query = query.where(Class.grade_level == grade_level)
        if class_id:
            query = query.where(Student.class_id == UUID(class_id))

        # Get total count
        count_sub = query.subquery()
        total = self.session.exec(select(func.count()).select_from(count_sub)).one()

        # Paginate and sort
        query = query.order_by(student_avg_sub.c.avg_grade)
        query = query.offset((page - 1) * page_size).limit(page_size)
        red_rows = self.session.exec(query).all()

        if not red_rows:
            return {"total": total, "page": page, "page_size": page_size, "students": []}

        # Get failing subjects for these students
        red_tzs = [row[0] for row in red_rows]
        failing_query = (
            select(Grade.student_tz, Grade.subject_name, Grade.teacher_name, Grade.grade)
            .where(Grade.student_tz.in_(red_tzs))
            .where(Grade.grade < AT_RISK_GRADE_THRESHOLD)
        )
        for cond in grade_conditions:
            failing_query = failing_query.where(cond)
        failing_grades = self.session.exec(failing_query).all()

        failing_map: dict[str, list] = {}
        for tz, subj, tname, grade in failing_grades:
            if tz not in failing_map:
                failing_map[tz] = []
            failing_map[tz].append({"subject": subj, "teacher_name": tname, "grade": grade})

        students = []
        for tz, name, class_name, gl, avg in red_rows:
            students.append({
                "student_tz": tz,
                "student_name": name,
                "class_name": class_name,
                "grade_level": gl,
                "average_grade": float(avg),
                "failing_subjects": failing_map.get(tz, []),
            })

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "students": students,
        }

    def get_versus_comparison(
        self,
        comparison_type: str,
        entity_ids: list[str],
        period: str | None = None,
        metric: str = "average_grade",
    ) -> dict:
        """Get versus comparison data for charts."""
        series = []

        if comparison_type == "class":
            # Batch query: all classes at once
            class_uuids = []
            for cid in entity_ids:
                try:
                    class_uuids.append(UUID(cid))
                except ValueError:
                    continue

            if class_uuids:
                classes = self.session.exec(select(Class).where(Class.id.in_(class_uuids))).all()
                class_map = {c.id: c for c in classes}

                query = (
                    select(
                        Student.class_id,
                        func.avg(Grade.grade).label("avg_grade"),
                        func.count(func.distinct(Grade.student_tz)).label("student_count"),
                        func.count(func.distinct(Student.student_tz)).label("total_students"),
                    )
                    .join(Student, Grade.student_tz == Student.student_tz)
                    .where(Student.class_id.in_(class_uuids))
                    .group_by(Student.class_id)
                )
                if period:
                    query = query.where(Grade.period == period)
                rows = self.session.exec(query).all()

                # Get subjects per class
                subj_query = (
                    select(Student.class_id, func.array_agg(func.distinct(Grade.subject_name)))
                    .join(Student, Grade.student_tz == Student.student_tz)
                    .where(Student.class_id.in_(class_uuids))
                    .group_by(Student.class_id)
                )
                if period:
                    subj_query = subj_query.where(Grade.period == period)
                subj_rows = self.session.exec(subj_query).all()
                subj_map = {row[0]: row[1] for row in subj_rows}

                for cid, avg, student_count, total_students in rows:
                    cls = class_map.get(cid)
                    if cls:
                        series.append({
                            "id": str(cls.id),
                            "name": cls.class_name,
                            "value": float(avg),
                            "student_count": total_students,
                            "subjects": subj_map.get(cid) or [],
                        })

        elif comparison_type == "teacher":
            teacher_uuids = []
            for tid in entity_ids:
                try:
                    teacher_uuids.append(UUID(tid))
                except ValueError:
                    continue

            if teacher_uuids:
                teachers = self.session.exec(select(Teacher).where(Teacher.id.in_(teacher_uuids))).all()
                teacher_map = {t.id: t for t in teachers}

                query = (
                    select(
                        Grade.teacher_id,
                        func.avg(Grade.grade).label("avg_grade"),
                        func.count(func.distinct(Grade.student_tz)).label("student_count"),
                    )
                    .where(Grade.teacher_id.in_(teacher_uuids))
                    .group_by(Grade.teacher_id)
                )
                if period:
                    query = query.where(Grade.period == period)
                rows = self.session.exec(query).all()

                # Get subjects per teacher
                subj_query = (
                    select(Grade.teacher_id, func.array_agg(func.distinct(Grade.subject_name)))
                    .where(Grade.teacher_id.in_(teacher_uuids))
                    .group_by(Grade.teacher_id)
                )
                if period:
                    subj_query = subj_query.where(Grade.period == period)
                subj_rows = self.session.exec(subj_query).all()
                subj_map = {row[0]: row[1] for row in subj_rows}

                for tid, avg, student_count in rows:
                    teacher = teacher_map.get(tid)
                    if teacher:
                        series.append({
                            "id": str(teacher.id),
                            "name": teacher.name,
                            "value": float(avg),
                            "student_count": student_count,
                            "subjects": subj_map.get(tid) or [],
                            "teacher_name": teacher.name,
                        })

        elif comparison_type == "layer":
            if entity_ids:
                query = (
                    select(
                        Class.grade_level,
                        func.avg(Grade.grade).label("avg_grade"),
                        func.count(func.distinct(Grade.student_tz)).label("student_count"),
                    )
                    .join(Student, Grade.student_tz == Student.student_tz)
                    .join(Class, Student.class_id == Class.id)
                    .where(Class.grade_level.in_(entity_ids))
                    .group_by(Class.grade_level)
                )
                if period:
                    query = query.where(Grade.period == period)
                rows = self.session.exec(query).all()

                # Get subjects per layer
                subj_query = (
                    select(Class.grade_level, func.array_agg(func.distinct(Grade.subject_name)))
                    .join(Student, Grade.student_tz == Student.student_tz)
                    .join(Class, Student.class_id == Class.id)
                    .where(Class.grade_level.in_(entity_ids))
                    .group_by(Class.grade_level)
                )
                if period:
                    subj_query = subj_query.where(Grade.period == period)
                subj_rows = self.session.exec(subj_query).all()
                subj_map = {row[0]: row[1] for row in subj_rows}

                for level, avg, student_count in rows:
                    series.append({
                        "id": level,
                        "name": f"Grade {level}",
                        "value": float(avg),
                        "student_count": student_count,
                        "subjects": subj_map.get(level) or [],
                    })

        return {
            "comparison_type": comparison_type,
            "metric": metric,
            "series": series,
        }

    def get_cascading_filter_options(
        self,
        grade_level: str | None = None,
        class_id: str | None = None,
        period: str | None = None,
    ) -> dict:
        """Get filter options based on current selections (cascading filters)."""
        class_query = select(Class)
        if grade_level:
            class_query = class_query.where(Class.grade_level == grade_level)
        classes = self.session.exec(class_query).all()

        class_options = [
            {"id": str(c.id), "class_name": c.class_name, "grade_level": c.grade_level}
            for c in classes
        ]

        # Build student_tz filter
        student_tzs: list[str] = []
        if class_id:
            try:
                class_uuid = UUID(class_id)
                student_tzs = list(
                    self.session.exec(
                        select(Student.student_tz).where(Student.class_id == class_uuid)
                    ).all()
                )
            except ValueError:
                pass
        elif grade_level:
            class_ids = [c.id for c in classes]
            if class_ids:
                student_tzs = list(
                    self.session.exec(
                        select(Student.student_tz).where(Student.class_id.in_(class_ids))
                    ).all()
                )

        # Single query for teacher_name, teacher_id, subject — no N+1
        teacher_subject_query = select(
            Grade.teacher_name, Grade.teacher_id, Grade.subject_name
        ).distinct()
        if student_tzs:
            teacher_subject_query = teacher_subject_query.where(Grade.student_tz.in_(student_tzs))
        if period:
            teacher_subject_query = teacher_subject_query.where(Grade.period == period)
        teacher_subject_rows = self.session.exec(teacher_subject_query).all()

        teacher_subjects: dict = {}
        all_subjects: set[str] = set()
        for tname, tid, subj in teacher_subject_rows:
            all_subjects.add(subj)
            if tname:
                if tname not in teacher_subjects:
                    teacher_subjects[tname] = {"id": str(tid) if tid else None, "subjects": set()}
                teacher_subjects[tname]["subjects"].add(subj)

        teacher_options = [
            {"id": data["id"], "name": name, "subjects": list(data["subjects"])}
            for name, data in teacher_subjects.items()
        ]

        return {
            "classes": class_options,
            "teachers": teacher_options,
            "subjects": sorted(all_subjects),
        }
