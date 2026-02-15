"""Dashboard analytics service."""

from uuid import UUID

from sqlmodel import Session, select

from ..constants import AT_RISK_GRADE_THRESHOLD, GOOD_GRADE_UPPER_BOUND, MEDIUM_GRADE_UPPER_BOUND
from ..models import AttendanceRecord, Class, Grade, Student, Teacher


class DashboardAnalytics:
    """Analytics engine for dashboard data."""

    def __init__(self, session: Session):
        self.session = session

    def get_layer_kpis(self, period: str | None = None, grade_level: str | None = None) -> dict:
        """
        Returns Dashboard Homepage KPIs.

        Args:
            period: Optional period filter (e.g., "Q1")
            grade_level: Optional grade level filter (e.g., "י")

        Returns:
            Dict with layer_average, avg_absences, at_risk_students
        """
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

        layer_average = None
        if grades:
            layer_average = round(sum(g.grade for g in grades) / len(grades), 2)

        avg_absences = 0
        if attendance:
            avg_absences = round(sum(a.total_absences for a in attendance) / len(attendance), 1)

        student_grades: dict[str, list[float]] = {}
        for g in grades:
            if g.student_tz not in student_grades:
                student_grades[g.student_tz] = []
            student_grades[g.student_tz].append(g.grade)

        at_risk_count = 0
        for student_tz, grade_list in student_grades.items():
            avg = sum(grade_list) / len(grade_list)
            if avg < AT_RISK_GRADE_THRESHOLD:
                at_risk_count += 1

        return {
            "layer_average": layer_average,
            "avg_absences": avg_absences,
            "at_risk_students": at_risk_count,
            "total_students": len(student_grades),
        }

    def _categorize_grades(self, grades: list[float]) -> list[dict]:
        """Categorize grades into buckets."""
        categories = {
            f"Fail (<{AT_RISK_GRADE_THRESHOLD})": 0,
            f"Medium ({AT_RISK_GRADE_THRESHOLD}-{MEDIUM_GRADE_UPPER_BOUND})": 0,
            f"Good ({MEDIUM_GRADE_UPPER_BOUND + 1}-{GOOD_GRADE_UPPER_BOUND})": 0,
            f"Excellent (>{GOOD_GRADE_UPPER_BOUND})": 0,
        }
        for g in grades:
            if g < AT_RISK_GRADE_THRESHOLD:
                categories[f"Fail (<{AT_RISK_GRADE_THRESHOLD})"] += 1
            elif g <= MEDIUM_GRADE_UPPER_BOUND:
                categories[f"Medium ({AT_RISK_GRADE_THRESHOLD}-{MEDIUM_GRADE_UPPER_BOUND})"] += 1
            elif g <= GOOD_GRADE_UPPER_BOUND:
                categories[f"Good ({MEDIUM_GRADE_UPPER_BOUND + 1}-{GOOD_GRADE_UPPER_BOUND})"] += 1
            else:
                categories[f"Excellent (>{GOOD_GRADE_UPPER_BOUND})"] += 1
        return [{"category": c, "count": n} for c, n in categories.items()]

    def _build_histogram(self, grades: list[float], step: int = 5) -> list[dict]:
        """Build grade histogram."""
        bins: dict[int, int] = {g: 0 for g in range(0, 101, step)}
        for v in grades:
            b = min(int(v // step) * step, 100)
            bins[b] = bins.get(b, 0) + 1
        return [{"grade": g, "count": c} for g, c in sorted(bins.items())]

    def get_class_comparison(self, period: str | None = None, grade_level: str | None = None) -> list[dict]:
        """
        Returns Bar Chart data for class comparison.

        Returns:
            List of dicts with class_name and average grade
        """
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

        class_aggregates = {cid: {"grades": [], "student_count": 0} for cid in class_map.keys()}

        for s in students:
            if not s.class_id or s.class_id not in class_aggregates:
                continue

            class_aggregates[s.class_id]["student_count"] += 1
            s_grades = student_grades.get(s.student_tz)
            if s_grades:
                class_aggregates[s.class_id]["grades"].extend(s_grades)

        result = []
        for cid, data in class_aggregates.items():
            cls = class_map[cid]
            all_grades = data["grades"]
            avg = round(sum(all_grades) / len(all_grades), 2) if all_grades else 0
            
            if data["student_count"] > 0:
                 result.append({
                    "id": cls.id,
                    "class_name": cls.class_name,
                    "average_grade": avg,
                    "student_count": data["student_count"],
                })

        return sorted(result, key=lambda x: x["class_name"])

    def get_class_heatmap(self, class_id: UUID, period: str | None = None) -> dict:
        """
        Returns Heatmap Matrix: Student x Subject.

        Args:
            class_id: The class ID to get heatmap for
            period: Optional period filter

        Returns:
            Dict with "subjects" list and "students" list (each with grades dict and average)
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

        sorted_subjects = sorted(all_subjects)
        student_rows = []

        for tz, data in student_data.items():
            grades_dict = data["grades"]
            for subj in sorted_subjects:
                if subj not in grades_dict:
                    grades_dict[subj] = None
            
            valid_grades = [v for v in grades_dict.values() if v is not None]
            avg = round(sum(valid_grades) / len(valid_grades), 2) if valid_grades else 0

            student_rows.append({
                "student_name": data["name"],
                "student_tz": tz,
                "grades": grades_dict,
                "average": avg,
            })

        student_rows.sort(key=lambda x: x["student_name"])

        return {
            "subjects": sorted_subjects,
            "students": student_rows,
        }

    def get_top_bottom_students(self, class_id: UUID, period: str | None = None, top_n: int = 5, bottom_n: int = 5) -> dict:
        """
        Returns Top N and Bottom N students in a class.

        Returns:
            Dict with "top" and "bottom" lists
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
                avg = sum(s_grades) / len(s_grades)
                student_averages.append(
                    {
                        "student_name": student.student_name,
                        "student_tz": student.student_tz,
                        "average": round(avg, 2),
                    }
                )

        sorted_students = sorted(student_averages, key=lambda x: x["average"], reverse=True)

        return {
            "top": sorted_students[:top_n],
            "bottom": sorted_students[-bottom_n:] if len(sorted_students) >= bottom_n else sorted_students,
        }

    def get_teacher_stats(self, teacher_name: str, period: str | None = None) -> dict:
        """
        Returns Teacher Grade Distribution.

        Args:
            teacher_name: Teacher name to filter by
            period: Optional period filter

        Returns:
            Dict with distribution data and summary stats
        """
        grade_query = select(Grade).where(Grade.teacher_name == teacher_name)
        if period:
            grade_query = grade_query.where(Grade.period == period)

        grades = self.session.exec(grade_query).all()

        if not grades:
            return {
                "distribution": [],
                "total_students": 0,
                "average_grade": None,
            }

        grade_values = [g.grade for g in grades]
        distribution = self._categorize_grades(grade_values)
        avg_grade = round(sum(grade_values) / len(grade_values), 2)

        return {
            "distribution": distribution,
            "total_students": len(grades),
            "average_grade": avg_grade,
            "teacher_name": teacher_name,
        }

    def get_student_radar(self, student_tz: str, period: str | None = None) -> list[dict]:
        """
        Returns data for Student Radar Chart (subject grades).

        Args:
            student_tz: Student TZ to get radar for
            period: Optional period filter

        Returns:
            List of dicts with subject and grade
        """
        grade_query = select(Grade).where(Grade.student_tz == student_tz)
        if period:
            grade_query = grade_query.where(Grade.period == period)

        grades = self.session.exec(grade_query).all()

        subject_grades: dict[str, list[float]] = {}
        for g in grades:
            if g.subject not in subject_grades:
                subject_grades[g.subject] = []
            subject_grades[g.subject].append(g.grade)

        result = []
        for subject, grade_list in subject_grades.items():
            avg = round(sum(grade_list) / len(grade_list), 2)
            result.append({"subject": subject, "grade": avg})

        return result

    def get_available_teachers(self, period: str | None = None) -> list[str]:
        """Get list of all teachers with grades."""
        grade_query = select(Grade.teacher_name).distinct()
        if period:
            grade_query = grade_query.where(Grade.period == period)

        teachers = self.session.exec(grade_query).all()
        return [t for t in teachers if t is not None]

    def get_available_periods(self) -> list[str]:
        """Get list of all available periods."""
        periods = self.session.exec(select(Grade.period).distinct()).all()
        return list(set(periods))

    def get_available_grade_levels(self) -> list[str]:
        """Get list of all grade levels."""
        levels = self.session.exec(select(Class.grade_level).distinct()).all()
        return list(set(levels))

    def get_teachers_list(self, period: str | None = None, grade_level: str | None = None) -> list[dict]:
        """Get list of teachers with summary stats."""
        teachers = self.session.exec(select(Teacher)).all()

        result = []
        for teacher in teachers:
            grade_query = select(Grade).where(Grade.teacher_id == teacher.id)
            if period:
                grade_query = grade_query.where(Grade.period == period)
            if grade_level:
                grade_query = (
                    grade_query.join(Student, Grade.student_tz == Student.student_tz)
                    .join(Class, Student.class_id == Class.id)
                    .where(Class.grade_level == grade_level)
                )

            grades = self.session.exec(grade_query).all()
            if not grades:
                continue

            subjects = set(g.subject for g in grades)
            students = set(g.student_tz for g in grades)
            avg = round(sum(g.grade for g in grades) / len(grades), 2)

            result.append({
                "id": str(teacher.id),
                "name": teacher.name,
                "subject_count": len(subjects),
                "student_count": len(students),
                "average_grade": avg,
            })

        return sorted(result, key=lambda x: x["name"])

    def get_teacher_detail(self, teacher_id: UUID, period: str | None = None) -> dict | None:
        """Get detailed teacher analytics."""
        teacher = self.session.exec(select(Teacher).where(Teacher.id == teacher_id)).first()
        if not teacher:
            return None

        grade_query = select(Grade).where(Grade.teacher_id == teacher.id)
        if period:
            grade_query = grade_query.where(Grade.period == period)

        grades = self.session.exec(grade_query).all()
        if not grades:
            return {
                "id": str(teacher.id),
                "name": teacher.name,
                "subjects": [],
                "classes": [],
                "student_count": 0,
                "average_grade": None,
                "distribution": [],
                "grade_histogram": [],
                "class_performance": [],
                "subject_performance": [],
            }

        grade_values = [g.grade for g in grades]
        avg = round(sum(grade_values) / len(grade_values), 2)
        distribution = self._categorize_grades(grade_values)
        grade_histogram = self._build_histogram(grade_values)

        student_tzs = list(set(g.student_tz for g in grades))
        students = []
        if student_tzs:
             students = self.session.exec(select(Student).where(Student.student_tz.in_(student_tzs))).all()
        
        student_map = {s.student_tz: s for s in students}
        
        class_ids = set(s.class_id for s in students if s.class_id)
        classes = []
        if class_ids:
            classes = self.session.exec(select(Class).where(Class.id.in_(class_ids))).all()
        
        class_map = {c.id: c for c in classes}

        class_grades: dict[str, list[float]] = {}
        class_students: dict[str, set[str]] = {}
        class_ids_map: dict[str, str] = {}

        subject_grades: dict[str, list[float]] = {}
        subject_students: dict[str, set[str]] = {}

        all_subjects = set()

        for g in grades:
            all_subjects.add(g.subject)

            if g.subject not in subject_grades:
                subject_grades[g.subject] = []
                subject_students[g.subject] = set()
            subject_grades[g.subject].append(g.grade)
            subject_students[g.subject].add(g.student_tz)

            student = student_map.get(g.student_tz)
            if student and student.class_id:
                cls = class_map.get(student.class_id)
                if cls:
                    cname = cls.class_name
                    if cname not in class_grades:
                        class_grades[cname] = []
                        class_students[cname] = set()
                        class_ids_map[cname] = str(cls.id)
                    class_grades[cname].append(g.grade)
                    class_students[cname].add(g.student_tz)

        class_performance = sorted(
            [
                {
                    "class_name": name,
                    "class_id": class_ids_map[name],
                    "average_grade": round(sum(gs) / len(gs), 2),
                    "student_count": len(class_students[name]),
                    "distribution": self._categorize_grades(gs),
                    "grade_histogram": self._build_histogram(gs),
                }
                for name, gs in class_grades.items()
            ],
            key=lambda x: x["class_name"],
        )

        subject_performance = sorted(
            [
                {
                    "subject": subj,
                    "average_grade": round(sum(gs) / len(gs), 2),
                    "student_count": len(subject_students[subj]),
                }
                for subj, gs in subject_grades.items()
            ],
            key=lambda x: x["subject"],
        )

        return {
            "id": str(teacher.id),
            "name": teacher.name,
            "subjects": sorted(all_subjects),
            "classes": sorted(class_grades.keys()),
            "student_count": len(student_tzs),
            "average_grade": avg,
            "distribution": distribution,
            "grade_histogram": grade_histogram,
            "class_performance": class_performance,
            "subject_performance": subject_performance,
        }
