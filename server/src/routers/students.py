from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
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
from ..database import get_session
from ..models import AttendanceRecord, Class, Grade, Student
from ..schemas.student import (
    AttendanceResponse,
    ClassResponse,
    DashboardStats,
    GradeResponse,
    StudentDetailResponse,
    StudentListResponse,
)

router = APIRouter(prefix="/api/students", tags=["students"])


@router.get("", response_model=StudentListResponse)
async def list_students(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, le=MAX_PAGE_SIZE),
    class_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None),
    at_risk_only: bool = Query(default=False),
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """List students with optional filtering."""
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

    count_query = select(func.count()).select_from(query.subquery())
    total = session.exec(count_query).one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    students = session.exec(query).all()

    if not students:
        return StudentListResponse(
            items=[],
            total=total,
            page=page,
            page_size=page_size,
        )

    student_tzs = [s.student_tz for s in students]
    class_ids = {s.class_id for s in students if s.class_id}

    classes_map = {}
    if class_ids:
        classes = session.exec(select(Class).where(Class.id.in_(class_ids))).all()
        classes_map = {c.id: c for c in classes}

    grade_query = select(Grade).where(Grade.student_tz.in_(student_tzs))
    if period:
        grade_query = grade_query.where(Grade.period == period)
    all_grades = session.exec(grade_query).all()

    student_grades: dict[str, list[float]] = {tz: [] for tz in student_tzs}
    for g in all_grades:
        if g.student_tz in student_grades:
            student_grades[g.student_tz].append(g.grade)

    att_query = select(AttendanceRecord).where(AttendanceRecord.student_tz.in_(student_tzs))
    if period:
        att_query = att_query.where(AttendanceRecord.period == period)
    all_attendance = session.exec(att_query).all()

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
        avg_grade = sum(grades) / len(grades) if grades else None

        attendance_records = student_attendance.get(student.student_tz, [])
        total_absences = sum(a.total_absences for a in attendance_records)
        total_negative = sum(a.total_negative_events for a in attendance_records)
        total_positive = sum(a.total_positive_events for a in attendance_records)

        is_at_risk = avg_grade is not None and avg_grade < AT_RISK_GRADE_THRESHOLD

        result_items.append(
            StudentDetailResponse(
                student_tz=student.student_tz,
                student_name=student.student_name,
                class_id=student.class_id,
                class_name=class_name,
                grade_level=grade_level,
                average_grade=round(avg_grade, 1) if avg_grade else None,
                total_absences=total_absences,
                total_negative_events=total_negative,
                total_positive_events=total_positive,
                is_at_risk=is_at_risk,
            )
        )

    return StudentListResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    class_id: UUID | None = Query(default=None),
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """Get dashboard statistics."""
    class_query = select(Class)
    if class_id:
        class_query = class_query.where(Class.id == class_id)
    classes = session.exec(class_query).all()
    class_map = {c.id: c for c in classes}

    if not classes:
         return DashboardStats(
            total_students=0,
            average_grade=None,
            at_risk_count=0,
            total_classes=0,
            classes=[],
        )

    student_query = select(Student).where(Student.class_id.in_(class_map.keys()))
    students = session.exec(student_query).all()
    student_tzs = [s.student_tz for s in students]

    grade_query = select(Grade).where(Grade.student_tz.in_(student_tzs))
    if period:
        grade_query = grade_query.where(Grade.period == period)
    grades = session.exec(grade_query).all()

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
                "class_id": s.class_id
            }
        else:
            student_stats[s.student_tz] = {
                "avg": None,
                "at_risk": False,
                "class_id": s.class_id
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
        
        class_responses.append(
            ClassResponse(
                id=cls.id,
                class_name=cls.class_name,
                grade_level=cls.grade_level,
                student_count=stats["students"],
                average_grade=round(c_avg, 1) if c_avg else None,
                at_risk_count=stats["at_risk"],
            )
        )
    
    class_responses.sort(key=lambda x: x.class_name)

    overall_avg = sum(overall_grades) / len(overall_grades) if overall_grades else None

    return DashboardStats(
        total_students=len(students),
        average_grade=round(overall_avg, 1) if overall_avg else None,
        at_risk_count=total_at_risk,
        total_classes=len(classes),
        classes=class_responses,
    )


@router.get("/classes", response_model=list[ClassResponse])
async def list_classes(
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """Get all classes with statistics."""
    classes = session.exec(select(Class)).all()
    class_map = {c.id: c for c in classes}

    if not classes:
        return []

    students = session.exec(select(Student)).all()
    student_tzs = [s.student_tz for s in students]

    grade_query = select(Grade).where(Grade.student_tz.in_(student_tzs))
    if period:
        grade_query = grade_query.where(Grade.period == period)
    grades = session.exec(grade_query).all()

    student_grades: dict[str, list[float]] = {}
    for g in grades:
        if g.student_tz not in student_grades:
            student_grades[g.student_tz] = []
        student_grades[g.student_tz].append(g.grade)

    class_stats = {cid: {"grades": [], "at_risk": 0, "students": 0} for cid in class_map.keys()}

    for s in students:
        if not s.class_id or s.class_id not in class_stats:
            continue
            
        stats = class_stats[s.class_id]
        stats["students"] += 1
        
        s_grades = student_grades.get(s.student_tz)
        if s_grades:
            avg = sum(s_grades) / len(s_grades)
            stats["grades"].append(avg)
            if avg < AT_RISK_GRADE_THRESHOLD:
                stats["at_risk"] += 1

    result = []
    for cls in classes:
        stats = class_stats.get(cls.id)
        if not stats:
            continue

        c_grades = stats["grades"]
        class_avg = sum(c_grades) / len(c_grades) if c_grades else None

        result.append(
            ClassResponse(
                id=cls.id,
                class_name=cls.class_name,
                grade_level=cls.grade_level,
                student_count=stats["students"],
                average_grade=round(class_avg, 1) if class_avg else None,
                at_risk_count=stats["at_risk"],
            )
        )
    
    result.sort(key=lambda x: x.class_name)

    return result


@router.get("/{student_tz}", response_model=StudentDetailResponse)
async def get_student(
    student_tz: str,
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """Get a specific student by TZ."""
    student = session.get(Student, student_tz)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    cls = session.get(Class, student.class_id)
    grade_level = cls.grade_level if cls else None
    class_name = cls.class_name if cls else "Unknown"

    grade_query = select(Grade).where(Grade.student_tz == student_tz)
    if period:
        grade_query = grade_query.where(Grade.period == period)
    grades = session.exec(grade_query).all()

    avg_grade = None
    if grades:
        avg_grade = sum(g.grade for g in grades) / len(grades)

    att_query = select(AttendanceRecord).where(AttendanceRecord.student_tz == student_tz)
    if period:
        att_query = att_query.where(AttendanceRecord.period == period)
    attendance_records = session.exec(att_query).all()

    total_absences = sum(a.total_absences for a in attendance_records)
    total_negative = sum(a.total_negative_events for a in attendance_records)
    total_positive = sum(a.total_positive_events for a in attendance_records)

    performance_score = None
    total_students_count = session.exec(select(func.count(Student.student_tz))).one()
    
    if total_students_count > 1:
        avg_query = select(Grade.student_tz, func.avg(Grade.grade)).group_by(Grade.student_tz)
        if period:
            avg_query = avg_query.where(Grade.period == period)
        all_avg_grades = session.exec(avg_query).all()
        avg_grades_map = {row[0]: row[1] for row in all_avg_grades}

        att_stats_query = select(
            AttendanceRecord.student_tz, 
            func.sum(AttendanceRecord.total_absences),
            func.sum(AttendanceRecord.total_negative_events),
            func.sum(AttendanceRecord.total_positive_events)
        ).group_by(AttendanceRecord.student_tz)
        if period:
            att_stats_query = att_stats_query.where(AttendanceRecord.period == period)
        all_att_stats = session.exec(att_stats_query).all()
        att_stats_map = {
            row[0]: {
                "absences": row[1] or 0, 
                "negative": row[2] or 0, 
                "positive": row[3] or 0
            } 
            for row in all_att_stats
        }

        all_student_tzs = session.exec(select(Student.student_tz)).all()
        
        student_stats = []
        for tz in all_student_tzs:
            s_avg = avg_grades_map.get(tz)
            s_att = att_stats_map.get(tz, {"absences": 0, "negative": 0, "positive": 0})
            
            student_stats.append({
                "tz": tz,
                "avg_grade": s_avg,
                "absences": s_att["absences"],
                "negative": s_att["negative"],
                "positive": s_att["positive"]
            })

        def percentile_rank(values: list[float], target: float) -> float:
            """Percentage of values strictly less than target."""
            below = sum(1 for v in values if v < target)
            return (below / len(values)) * 100

        target_stats = next((s for s in student_stats if s["tz"] == student_tz), None)
        
        if target_stats:
            grade_values = [s["avg_grade"] for s in student_stats if s["avg_grade"] is not None]
            target_avg = target_stats["avg_grade"]
            grade_pct = percentile_rank(grade_values, target_avg) if target_avg is not None and grade_values else None

            absence_values = [-s["absences"] for s in student_stats]
            absence_pct = percentile_rank(absence_values, -target_stats["absences"])

            behavior_values = [s["positive"] - s["negative"] for s in student_stats]
            target_behavior = target_stats["positive"] - target_stats["negative"]
            behavior_pct = percentile_rank(behavior_values, target_behavior)

            if grade_pct is not None:
                performance_score = round(grade_pct * GRADE_WEIGHT + absence_pct * ATTENDANCE_WEIGHT + behavior_pct * BEHAVIOR_WEIGHT, 1)
            else:
                performance_score = round(absence_pct * ATTENDANCE_WEIGHT_NO_GRADES + behavior_pct * BEHAVIOR_WEIGHT_NO_GRADES, 1)

    return StudentDetailResponse(
        student_tz=student.student_tz,
        student_name=student.student_name,
        class_id=student.class_id,
        class_name=class_name,
        grade_level=grade_level,
        average_grade=round(avg_grade, 1) if avg_grade else None,
        total_absences=total_absences,
        total_negative_events=total_negative,
        total_positive_events=total_positive,
        is_at_risk=avg_grade is not None and avg_grade < AT_RISK_GRADE_THRESHOLD,
        performance_score=performance_score,
    )


@router.get("/{student_tz}/grades", response_model=list[GradeResponse])
async def get_student_grades(
    student_tz: str,
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """Get all grades for a student."""
    student = session.get(Student, student_tz)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    query = select(Grade).where(Grade.student_tz == student_tz)
    if period:
        query = query.where(Grade.period == period)

    grades = session.exec(query).all()

    return [
        GradeResponse(
            id=g.id,
            subject=g.subject,
            teacher_name=g.teacher_name,
            grade=g.grade,
            period=g.period,
        )
        for g in grades
    ]


@router.get("/{student_tz}/attendance", response_model=list[AttendanceResponse])
async def get_student_attendance(
    student_tz: str,
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """Get all attendance records for a student."""
    student = session.get(Student, student_tz)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    query = select(AttendanceRecord).where(AttendanceRecord.student_tz == student_tz)
    if period:
        query = query.where(AttendanceRecord.period == period)

    records = session.exec(query).all()

    return [
        AttendanceResponse(
            id=r.id,
            lessons_reported=r.lessons_reported,
            absence=r.absence,
            absence_justified=r.absence_justified,
            late=r.late,
            disturbance=r.disturbance,
            total_absences=r.total_absences,
            attendance=r.attendance,
            total_negative_events=r.total_negative_events,
            total_positive_events=r.total_positive_events,
            period=r.period,
        )
        for r in records
    ]
