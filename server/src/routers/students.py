from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from ..constants import (
    AT_RISK_GRADE_THRESHOLD,
    DEFAULT_PAGE_SIZE,
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
from ..services.students import StudentService
from ..views.students import StudentDefaultView

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
    service = StudentService(session)
    view = StudentDefaultView()

    data = service.list_students(
        page=page,
        page_size=page_size,
        class_id=class_id,
        search=search,
        at_risk_only=at_risk_only,
        period=period,
    )

    return view.render_list(data)


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




@router.get("/{student_tz}", response_model=StudentDetailResponse)
async def get_student(
    student_tz: str,
    period: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """Get a specific student by TZ."""
    service = StudentService(session)
    view = StudentDefaultView()

    data = service.get_student_detail(student_tz, period)
    if not data:
        raise HTTPException(status_code=404, detail="Student not found")

    return view.render_detail(data)


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
