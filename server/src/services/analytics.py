"""Dashboard analytics service."""

from uuid import UUID

from sqlmodel import Session, select

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
        # Build grade query with filters
        grade_query = select(Grade)
        if period:
            grade_query = grade_query.where(Grade.period == period)

        # If grade_level filter, join with Student and Class
        if grade_level:
            grade_query = (
                grade_query.join(Student, Grade.student_tz == Student.student_tz)
                .join(Class, Student.class_id == Class.id)
                .where(Class.grade_level == grade_level)
            )

        grades = self.session.exec(grade_query).all()

        # Build attendance query with filters
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

        # Calculate layer average
        layer_average = None
        if grades:
            layer_average = round(sum(g.grade for g in grades) / len(grades), 2)

        # Calculate average absences
        avg_absences = 0
        if attendance:
            avg_absences = round(sum(a.total_absences for a in attendance) / len(attendance), 1)

        # Calculate at-risk students (average < 55)
        student_grades: dict[str, list[float]] = {}
        for g in grades:
            if g.student_tz not in student_grades:
                student_grades[g.student_tz] = []
            student_grades[g.student_tz].append(g.grade)

        at_risk_count = 0
        for student_tz, grade_list in student_grades.items():
            avg = sum(grade_list) / len(grade_list)
            if avg < 55:
                at_risk_count += 1

        return {
            "layer_average": layer_average,
            "avg_absences": avg_absences,
            "at_risk_students": at_risk_count,
            "total_students": len(student_grades),
        }

    def get_class_comparison(self, period: str | None = None, grade_level: str | None = None) -> list[dict]:
        """
        Returns Bar Chart data for class comparison.

        Returns:
            List of dicts with class_name and average grade
        """
        # Get all classes, optionally filtered by grade level
        class_query = select(Class)
        if grade_level:
            class_query = class_query.where(Class.grade_level == grade_level)

        classes = self.session.exec(class_query).all()

        result = []
        for cls in classes:
            # Get students in this class
            students = self.session.exec(select(Student).where(Student.class_id == cls.id)).all()

            # Get grades for these students
            class_grades = []
            for student in students:
                grade_query = select(Grade).where(Grade.student_tz == student.student_tz)
                if period:
                    grade_query = grade_query.where(Grade.period == period)
                grades = self.session.exec(grade_query).all()
                class_grades.extend([g.grade for g in grades])

            if class_grades:
                avg = round(sum(class_grades) / len(class_grades), 2)
                result.append(
                    {
                        "id": cls.id,
                        "class_name": cls.class_name,
                        "average_grade": avg,
                        "student_count": len(students),
                    }
                )

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
        # Get students in the class
        students = self.session.exec(select(Student).where(Student.class_id == class_id)).all()

        if not students:
            return {}

        all_subjects: set[str] = set()
        student_rows = []

        for student in students:
            grade_query = select(Grade).where(Grade.student_tz == student.student_tz)
            if period:
                grade_query = grade_query.where(Grade.period == period)
            grades = self.session.exec(grade_query).all()

            grades_dict: dict[str, float] = {}
            for g in grades:
                all_subjects.add(g.subject)
                grades_dict[g.subject] = g.grade

            avg = round(sum(grades_dict.values()) / len(grades_dict), 2) if grades_dict else 0
            student_rows.append(
                {
                    "student_name": student.student_name,
                    "student_tz": student.student_tz,
                    "grades": grades_dict,
                    "average": avg,
                }
            )

        # Fill missing subjects with None
        sorted_subjects = sorted(all_subjects)
        for row in student_rows:
            for subject in sorted_subjects:
                if subject not in row["grades"]:
                    row["grades"][subject] = None

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
        # Get students in the class
        students = self.session.exec(select(Student).where(Student.class_id == class_id)).all()

        student_averages = []

        for student in students:
            grade_query = select(Grade).where(Grade.student_tz == student.student_tz)
            if period:
                grade_query = grade_query.where(Grade.period == period)
            grades = self.session.exec(grade_query).all()

            if grades:
                avg = sum(g.grade for g in grades) / len(grades)
                student_averages.append(
                    {
                        "student_name": student.student_name,
                        "student_tz": student.student_tz,
                        "average": round(avg, 2),
                    }
                )

        # Sort by average
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

        # Categorize grades
        categories = {
            "Fail (<55)": 0,
            "Medium (55-75)": 0,
            "Good (76-90)": 0,
            "Excellent (>90)": 0,
        }

        for g in grades:
            if g.grade < 55:
                categories["Fail (<55)"] += 1
            elif g.grade <= 75:
                categories["Medium (55-75)"] += 1
            elif g.grade <= 90:
                categories["Good (76-90)"] += 1
            else:
                categories["Excellent (>90)"] += 1

        distribution = [{"category": cat, "count": count} for cat, count in categories.items()]

        avg_grade = round(sum(g.grade for g in grades) / len(grades), 2)

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

        # Group by subject (in case of multiple grades per subject)
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

        subjects = sorted(set(g.subject for g in grades))
        student_tzs = set(g.student_tz for g in grades)
        avg = round(sum(g.grade for g in grades) / len(grades), 2)

        # Grade distribution
        categories = {
            "Fail (<55)": 0,
            "Medium (55-75)": 0,
            "Good (76-90)": 0,
            "Excellent (>90)": 0,
        }
        for g in grades:
            if g.grade < 55:
                categories["Fail (<55)"] += 1
            elif g.grade <= 75:
                categories["Medium (55-75)"] += 1
            elif g.grade <= 90:
                categories["Good (76-90)"] += 1
            else:
                categories["Excellent (>90)"] += 1

        distribution = [{"category": cat, "count": count} for cat, count in categories.items()]

        # Per-class performance
        class_grades: dict[str, list[float]] = {}
        class_students: dict[str, set[str]] = {}
        class_ids: dict[str, str] = {}

        for g in grades:
            student = self.session.exec(select(Student).where(Student.student_tz == g.student_tz)).first()
            if student and student.class_id:
                cls = self.session.exec(select(Class).where(Class.id == student.class_id)).first()
                if cls:
                    if cls.class_name not in class_grades:
                        class_grades[cls.class_name] = []
                        class_students[cls.class_name] = set()
                        class_ids[cls.class_name] = str(cls.id)
                    class_grades[cls.class_name].append(g.grade)
                    class_students[cls.class_name].add(g.student_tz)

        def _build_distribution(grade_list: list[float]) -> list[dict]:
            cats = {"Fail (<55)": 0, "Medium (55-75)": 0, "Good (76-90)": 0, "Excellent (>90)": 0}
            for v in grade_list:
                if v < 55:
                    cats["Fail (<55)"] += 1
                elif v <= 75:
                    cats["Medium (55-75)"] += 1
                elif v <= 90:
                    cats["Good (76-90)"] += 1
                else:
                    cats["Excellent (>90)"] += 1
            return [{"category": c, "count": n} for c, n in cats.items()]

        def _build_histogram(grade_list: list[float], step: int = 5) -> list[dict]:
            bins: dict[int, int] = {g: 0 for g in range(0, 101, step)}
            for v in grade_list:
                b = min(int(v // step) * step, 100)
                bins[b] = bins.get(b, 0) + 1
            return [{"grade": g, "count": c} for g, c in sorted(bins.items())]

        grade_histogram = _build_histogram([g.grade for g in grades])

        class_performance = sorted(
            [
                {
                    "class_name": name,
                    "class_id": class_ids[name],
                    "average_grade": round(sum(gs) / len(gs), 2),
                    "student_count": len(class_students[name]),
                    "distribution": _build_distribution(gs),
                    "grade_histogram": _build_histogram(gs),
                }
                for name, gs in class_grades.items()
            ],
            key=lambda x: x["class_name"],
        )

        classes_list = sorted(class_grades.keys())

        # Per-subject performance
        subject_grades: dict[str, list[float]] = {}
        subject_students: dict[str, set[str]] = {}
        for g in grades:
            if g.subject not in subject_grades:
                subject_grades[g.subject] = []
                subject_students[g.subject] = set()
            subject_grades[g.subject].append(g.grade)
            subject_students[g.subject].add(g.student_tz)

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
            "subjects": subjects,
            "classes": classes_list,
            "student_count": len(student_tzs),
            "average_grade": avg,
            "distribution": distribution,
            "grade_histogram": grade_histogram,
            "class_performance": class_performance,
            "subject_performance": subject_performance,
        }
