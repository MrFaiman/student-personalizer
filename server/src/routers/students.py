from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

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
    page_size: int = Query(default=20, le=100),
    class_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None),
    at_risk_only: bool = Query(default=False),
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """
    List students with optional filtering.

    - **class_id**: Filter by class ID
    - **search**: Search by student name
    - **at_risk_only**: Only show students with average < 55
    - **period**: Filter grades/attendance by period
    """
    # Base query
    query = select(Student)

    if class_id:
        query = query.where(Student.class_id == class_id)
    if search:
        query = query.where(Student.student_name.contains(search))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = session.exec(count_query).one()

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    students = session.exec(query).all()

    # Enrich with grades and attendance data
    result_items = []
    for student in students:
        # Get class info
        cls = session.get(Class, student.class_id)
        grade_level = cls.grade_level if cls else None
        class_name = cls.class_name if cls else "Unknown"

        # Get grades for this student (optionally filtered by period)
        grade_query = select(Grade).where(Grade.student_tz == student.student_tz)
        if period:
            grade_query = grade_query.where(Grade.period == period)
        grades = session.exec(grade_query).all()

        avg_grade = None
        if grades:
            avg_grade = sum(g.grade for g in grades) / len(grades)

        # Get attendance for this student (optionally filtered by period)
        att_query = select(AttendanceRecord).where(
            AttendanceRecord.student_tz == student.student_tz
        )
        if period:
            att_query = att_query.where(AttendanceRecord.period == period)
        attendance_records = session.exec(att_query).all()

        total_absences = sum(a.total_absences for a in attendance_records)
        total_negative = sum(a.total_negative_events for a in attendance_records)
        total_positive = sum(a.total_positive_events for a in attendance_records)

        is_at_risk = avg_grade is not None and avg_grade < 55

        if at_risk_only and not is_at_risk:
            continue

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
    # Get all classes
    class_query = select(Class)
    if class_id:
        class_query = class_query.where(Class.id == class_id)
    classes = session.exec(class_query).all()

    total_students = 0
    all_grades = []
    at_risk_count = 0
    class_responses = []

    for cls in classes:
        # Get students in this class
        student_query = select(Student).where(Student.class_id == cls.id)
        students = session.exec(student_query).all()

        class_grades = []
        class_at_risk = 0

        for student in students:
            total_students += 1

            # Get grades
            grade_query = select(Grade).where(Grade.student_tz == student.student_tz)
            if period:
                grade_query = grade_query.where(Grade.period == period)
            grades = session.exec(grade_query).all()

            if grades:
                avg = sum(g.grade for g in grades) / len(grades)
                class_grades.append(avg)
                all_grades.append(avg)
                if avg < 55:
                    class_at_risk += 1
                    at_risk_count += 1

        class_avg = sum(class_grades) / len(class_grades) if class_grades else None
        class_responses.append(
            ClassResponse(
                id=cls.id,
                class_name=cls.class_name,
                grade_level=cls.grade_level,
                student_count=len(students),
                average_grade=round(class_avg, 1) if class_avg else None,
                at_risk_count=class_at_risk,
            )
        )

    overall_avg = sum(all_grades) / len(all_grades) if all_grades else None

    return DashboardStats(
        total_students=total_students,
        average_grade=round(overall_avg, 1) if overall_avg else None,
        at_risk_count=at_risk_count,
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
    result = []

    for cls in classes:
        students = session.exec(
            select(Student).where(Student.class_id == cls.id)
        ).all()

        grades = []
        at_risk = 0

        for student in students:
            grade_query = select(Grade).where(Grade.student_tz == student.student_tz)
            if period:
                grade_query = grade_query.where(Grade.period == period)
            student_grades = session.exec(grade_query).all()

            if student_grades:
                avg = sum(g.grade for g in student_grades) / len(student_grades)
                grades.append(avg)
                if avg < 55:
                    at_risk += 1

        class_avg = sum(grades) / len(grades) if grades else None
        result.append(
            ClassResponse(
                id=cls.id,
                class_name=cls.class_name,
                grade_level=cls.grade_level,
                student_count=len(students),
                average_grade=round(class_avg, 1) if class_avg else None,
                at_risk_count=at_risk,
            )
        )

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

    # Get grades
    grade_query = select(Grade).where(Grade.student_tz == student_tz)
    if period:
        grade_query = grade_query.where(Grade.period == period)
    grades = session.exec(grade_query).all()

    avg_grade = None
    if grades:
        avg_grade = sum(g.grade for g in grades) / len(grades)

    # Get attendance
    att_query = select(AttendanceRecord).where(
        AttendanceRecord.student_tz == student_tz
    )
    if period:
        att_query = att_query.where(AttendanceRecord.period == period)
    attendance_records = session.exec(att_query).all()

    total_absences = sum(a.total_absences for a in attendance_records)
    total_negative = sum(a.total_negative_events for a in attendance_records)
    total_positive = sum(a.total_positive_events for a in attendance_records)

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
        is_at_risk=avg_grade is not None and avg_grade < 55,
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
            absence=r.absence,
            absence_justified=r.absence_justified,
            late=r.late,
            disturbance=r.disturbance,
            total_absences=r.total_absences,
            total_negative_events=r.total_negative_events,
            total_positive_events=r.total_positive_events,
            period=r.period,
        )
        for r in records
    ]
