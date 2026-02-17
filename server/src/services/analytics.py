from uuid import UUID

import numpy as np
from sqlmodel import Session, select

from ..constants import AT_RISK_GRADE_THRESHOLD
from ..models import AttendanceRecord, Class, Grade, Student, Teacher


class AnalyticsService:
    """Core service for functional/layer analytics and advanced comparisons."""

    def __init__(self, session: Session):
        self.session = session

    def get_layer_kpis(self, period: str | None = None, grade_level: str | None = None) -> dict:
        """Returns Dashboard Homepage KPIs as pre-calculated dict."""
        grade_query = select(Grade)
        if period:
            grade_query = grade_query.where(Grade.period == period)

        if grade_level:
            grade_query = (
                grade_query.join(Student, Grade.student_tz == Student.student_tz)
                .join(Class, Student.class_id == Class.id)
                .where(Class.grade_level == grade_level)
            )

        grades = self.session.exec(grade_query).all()

        att_query = select(AttendanceRecord)
        if period:
            att_query = att_query.where(AttendanceRecord.period == period)

        if grade_level:
            att_query = (
                att_query.join(Student, AttendanceRecord.student_tz == Student.student_tz)
                .join(Class, Student.class_id == Class.id)
                .where(Class.grade_level == grade_level)
            )

        attendance = self.session.exec(att_query).all()

        # Calculate at-risk based on student averages
        student_grades: dict[str, list[float]] = {}
        for g in grades:
            if g.student_tz not in student_grades:
                student_grades[g.student_tz] = []
            student_grades[g.student_tz].append(g.grade)

        at_risk_count = 0
        for grade_list in student_grades.values():
            if np.mean(grade_list) < AT_RISK_GRADE_THRESHOLD:
                at_risk_count += 1

        grade_values = [g.grade for g in grades]
        layer_average = sum(grade_values) / len(grade_values) if grade_values else None

        avg_absences = 0.0
        if attendance:
            avg_absences = sum(a.total_absences for a in attendance) / len(attendance)

        return {
            "layer_average": layer_average,
            "avg_absences": avg_absences,
            "at_risk_count": at_risk_count,
            "total_students": len(student_grades),
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

        student_query = select(Student).where(Student.class_id.in_(class_map.keys()))
        students = self.session.exec(student_query).all()
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

        result = []
        for cid, cls in class_map.items():
            class_grades = []
            class_student_count = 0

            for s in students:
                if s.class_id == cid:
                    class_student_count += 1
                    class_grades.extend(student_grades.get(s.student_tz, []))

            avg = sum(class_grades) / len(class_grades) if class_grades else 0

            if class_student_count > 0:
                result.append({
                    "class": cls,
                    "average_grade": avg,
                    "student_count": class_student_count,
                })

        return result

    def get_student_radar(self, student_tz: str, period: str | None = None) -> dict:
        """Returns subject -> average grade mapping."""
        grade_query = select(Grade).where(Grade.student_tz == student_tz)
        if period:
            grade_query = grade_query.where(Grade.period == period)

        grades = self.session.exec(grade_query).all()

        subject_grades: dict[str, list[float]] = {}
        for g in grades:
            if g.subject not in subject_grades:
                subject_grades[g.subject] = []
            subject_grades[g.subject].append(g.grade)

        return {
            subject: sum(g) / len(g)
            for subject, g in subject_grades.items()
        }

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
                key = f"{g.subject}|{g.teacher_name or 'Unknown'}"
                if key not in data:
                    data[key] = {
                        "grades": [],
                        "students": set(),
                        "subject": g.subject,
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
                if g.subject not in data:
                    data[g.subject] = {
                        "grades": [],
                        "students": set(),
                        "teachers": set(),
                    }
                data[g.subject]["grades"].append(g.grade)
                data[g.subject]["students"].add(g.student_tz)
                if g.teacher_name:
                    data[g.subject]["teachers"].add(g.teacher_name)
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
        grade_query = select(Grade)
        if period:
            grade_query = grade_query.where(Grade.period == period)

        grades = list(self.session.exec(grade_query).all())

        # Calculate student averages
        student_grades: dict[str, list[float]] = {}
        for g in grades:
            if g.student_tz not in student_grades:
                student_grades[g.student_tz] = []
            student_grades[g.student_tz].append(g.grade)

        # Identify red students
        red_student_tzs: set[str] = set()
        student_averages: dict[str, float] = {}
        for tz, grade_list in student_grades.items():
            avg = float(np.mean(grade_list))
            student_averages[tz] = avg
            if avg < AT_RISK_GRADE_THRESHOLD:
                red_student_tzs.add(tz)

        # Get student info
        all_student_tzs = set(student_grades.keys())
        students = []
        if all_student_tzs:
            students = self.session.exec(
                select(Student).where(Student.student_tz.in_(all_student_tzs))
            ).all()
        student_map = {s.student_tz: s for s in students}

        # Get class info
        class_ids = set(s.class_id for s in students if s.class_id)
        classes = []
        if class_ids:
            classes = self.session.exec(select(Class).where(Class.id.in_(class_ids))).all()
        class_map = {c.id: c for c in classes}

        # Filter by grade_level if specified
        if grade_level:
            class_ids_for_level = {c.id for c in classes if c.grade_level == grade_level}
            filtered_students = {
                tz
                for tz in all_student_tzs
                if student_map.get(tz) and student_map[tz].class_id in class_ids_for_level
            }
            red_student_tzs = red_student_tzs & filtered_students
            all_student_tzs = filtered_students

        # Segmentation by class
        by_class: dict = {}
        for tz in all_student_tzs:
            student = student_map.get(tz)
            if student and student.class_id:
                cls = class_map.get(student.class_id)
                if cls:
                    if cls.id not in by_class:
                        by_class[cls.id] = {
                            "name": cls.class_name,
                            "total": 0,
                            "red": 0,
                            "red_grades": [],
                        }
                    by_class[cls.id]["total"] += 1
                    if tz in red_student_tzs:
                        by_class[cls.id]["red"] += 1
                        by_class[cls.id]["red_grades"].append(student_averages[tz])

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
            student = student_map.get(tz)
            if student and student.class_id:
                cls = class_map.get(student.class_id)
                if cls:
                    level = cls.grade_level
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

        # Segmentation by teacher
        by_teacher: dict = {}
        for g in grades:
            if g.student_tz not in all_student_tzs or not g.teacher_name:
                continue

            if g.teacher_name not in by_teacher:
                by_teacher[g.teacher_name] = {
                    "students": set(),
                    "red_students": set(),
                    "red_grades": [],
                }
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
                if g.subject not in by_subject:
                    by_subject[g.subject] = {"students": set(), "grades": []}
                by_subject[g.subject]["students"].add(g.student_tz)
                if g.grade < AT_RISK_GRADE_THRESHOLD:
                    by_subject[g.subject]["grades"].append(g.grade)

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
        grade_query = select(Grade)
        if period:
            grade_query = grade_query.where(Grade.period == period)
        if teacher_name:
            grade_query = grade_query.where(Grade.teacher_name == teacher_name)
        if subject:
            grade_query = grade_query.where(Grade.subject == subject)

        grades = list(self.session.exec(grade_query).all())

        student_grades: dict[str, list[float]] = {}
        student_grade_details: dict[str, list] = {}

        for g in grades:
            if g.student_tz not in student_grades:
                student_grades[g.student_tz] = []
                student_grade_details[g.student_tz] = []
            student_grades[g.student_tz].append(g.grade)
            if g.grade < AT_RISK_GRADE_THRESHOLD:
                student_grade_details[g.student_tz].append({
                    "subject": g.subject,
                    "teacher_name": g.teacher_name,
                    "grade": g.grade,
                })

        red_students: dict[str, float] = {}
        for tz, grade_list in student_grades.items():
            avg = float(np.mean(grade_list))
            if avg < AT_RISK_GRADE_THRESHOLD:
                red_students[tz] = avg

        student_tzs = list(red_students.keys())
        if not student_tzs:
            return {"total": 0, "page": page, "page_size": page_size, "students": []}

        students = self.session.exec(
            select(Student).where(Student.student_tz.in_(student_tzs))
        ).all()
        student_map = {s.student_tz: s for s in students}

        class_ids = set(s.class_id for s in students if s.class_id)
        classes = []
        if class_ids:
            classes = self.session.exec(select(Class).where(Class.id.in_(class_ids))).all()
        class_map = {c.id: c for c in classes}

        filtered_students = []
        for tz, avg in red_students.items():
            student = student_map.get(tz)
            if not student:
                continue

            cls = class_map.get(student.class_id) if student.class_id else None

            if grade_level and (not cls or cls.grade_level != grade_level):
                continue
            if class_id and (not student.class_id or str(student.class_id) != class_id):
                continue

            filtered_students.append({
                "student_tz": tz,
                "student_name": student.student_name,
                "class_name": cls.class_name if cls else None,
                "grade_level": cls.grade_level if cls else None,
                "average_grade": avg,
                "failing_subjects": student_grade_details.get(tz, []),
            })

        filtered_students.sort(key=lambda x: x["average_grade"])

        total = len(filtered_students)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = filtered_students[start:end]

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "students": paginated,
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
            for cid in entity_ids:
                try:
                    class_uuid = UUID(cid)
                except ValueError:
                    continue

                cls = self.session.exec(select(Class).where(Class.id == class_uuid)).first()
                if not cls:
                    continue

                students = self.session.exec(
                    select(Student).where(Student.class_id == cls.id)
                ).all()
                student_tzs = [s.student_tz for s in students]

                if not student_tzs:
                    continue

                grade_query = select(Grade).where(Grade.student_tz.in_(student_tzs))
                if period:
                    grade_query = grade_query.where(Grade.period == period)
                grades = self.session.exec(grade_query).all()

                if grades:
                    avg = sum(g.grade for g in grades) / len(grades)
                    subjects = list(set(g.subject for g in grades))
                    series.append({
                        "id": str(cls.id),
                        "name": cls.class_name,
                        "value": avg,
                        "student_count": len(students),
                        "subjects": subjects,
                    })

        elif comparison_type == "teacher":
            for teacher_id in entity_ids:
                try:
                    teacher_uuid = UUID(teacher_id)
                except ValueError:
                    continue

                teacher = self.session.exec(
                    select(Teacher).where(Teacher.id == teacher_uuid)
                ).first()
                if not teacher:
                    continue

                grade_query = select(Grade).where(Grade.teacher_id == teacher.id)
                if period:
                    grade_query = grade_query.where(Grade.period == period)
                grades = list(self.session.exec(grade_query).all())

                if grades:
                    avg = float(np.mean([g.grade for g in grades]))
                    student_count = len(set(g.student_tz for g in grades))
                    subjects = list(set(g.subject for g in grades))
                    series.append({
                        "id": str(teacher.id),
                        "name": teacher.name,
                        "value": avg,
                        "student_count": student_count,
                        "subjects": subjects,
                        "teacher_name": teacher.name,
                    })

        elif comparison_type == "layer":
            for level in entity_ids:
                classes = self.session.exec(
                    select(Class).where(Class.grade_level == level)
                ).all()
                class_ids = [c.id for c in classes]

                if not class_ids:
                    continue

                students = self.session.exec(
                    select(Student).where(Student.class_id.in_(class_ids))
                ).all()
                student_tzs = [s.student_tz for s in students]

                if not student_tzs:
                    continue

                grade_query = select(Grade).where(Grade.student_tz.in_(student_tzs))
                if period:
                    grade_query = grade_query.where(Grade.period == period)
                grades = self.session.exec(grade_query).all()

                if grades:
                    avg = sum(g.grade for g in grades) / len(grades)
                    subjects = list(set(g.subject for g in grades))
                    series.append({
                        "id": level,
                        "name": f"Grade {level}",
                        "value": avg,
                        "student_count": len(students),
                        "subjects": subjects,
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

        if student_tzs:
            grade_query = select(Grade.teacher_name, Grade.teacher_id).distinct()
            grade_query = grade_query.where(Grade.student_tz.in_(student_tzs))
            if period:
                grade_query = grade_query.where(Grade.period == period)
            teacher_rows = self.session.exec(grade_query).all()
        else:
            grade_query = select(Grade.teacher_name, Grade.teacher_id).distinct()
            if period:
                grade_query = grade_query.where(Grade.period == period)
            teacher_rows = self.session.exec(grade_query).all()

        teacher_subjects: dict = {}
        for tname, tid in teacher_rows:
            if tname:
                if tname not in teacher_subjects:
                    teacher_subjects[tname] = {"id": str(tid) if tid else None, "subjects": set()}
                subject_query = select(Grade.subject).distinct().where(Grade.teacher_name == tname)
                if period:
                    subject_query = subject_query.where(Grade.period == period)
                subjects = self.session.exec(subject_query).all()
                teacher_subjects[tname]["subjects"].update(subjects)

        teacher_options = [
            {"id": data["id"], "name": name, "subjects": list(data["subjects"])}
            for name, data in teacher_subjects.items()
        ]

        if student_tzs:
            subject_query = select(Grade.subject).distinct().where(Grade.student_tz.in_(student_tzs))
        else:
            subject_query = select(Grade.subject).distinct()
        if period:
            subject_query = subject_query.where(Grade.period == period)

        subjects = list(self.session.exec(subject_query).all())

        return {
            "classes": class_options,
            "teachers": teacher_options,
            "subjects": list(subjects) if subjects else [],
        }
