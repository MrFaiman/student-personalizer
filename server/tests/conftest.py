
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.models import AttendanceRecord, Class, Grade, Student

# Student profiles used for seeding: (tz, name, grades, absence, late, dist, neg, pos)
PROFILES = [
    # Class Test-10A
    ("S001", "Alice", [90, 85, 80, 60, 50], 2, 1, 0, 3, 5),   # declining
    ("S002", "Bob", [60, 65, 70, 72, 73], 1, 0, 0, 1, 8),     # improving
    ("S003", "Carol", [40, 42, 38, 45, 41], 8, 3, 2, 13, 0),   # at-risk
    ("S004", "Dave", [88, 90, 92, 91, 93], 0, 0, 0, 0, 10),    # excellent
    
    # Class Test-10B
    ("S005", "Eve", [55, 50, 48, 52, 45], 5, 2, 1, 8, 1),      # borderline
    ("S006", "Frank", [70, 72, 68, 74, 71], 3, 1, 0, 4, 3),    # stable mid
    ("S007", "Grace", [95, 93, 96, 94, 97], 0, 0, 0, 0, 12),   # top
    ("S008", "Hank", [30, 35, 25, 40, 28], 10, 4, 3, 17, 0),   # dropout risk
]

def _create_engine():
    """Create an in-memory SQLite engine with StaticPool for connection sharing."""
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

def _seed_db(engine):
    """Populate the DB with test students, grades, and attendance."""
    with Session(engine) as s:
        # Create Classes
        class_a = Class(class_name="Test-10A", grade_level="10")
        class_b = Class(class_name="Test-10B", grade_level="10")
        s.add(class_a)
        s.add(class_b)
        s.commit()
        s.refresh(class_a)
        s.refresh(class_b)

        # Distribute students in classes
        for i, (tz, name, grades, absence, late, dist, neg, pos) in enumerate(PROFILES):
            cls = class_a if i < 4 else class_b
            
            s.add(Student(
                student_tz=tz, 
                student_name=name, 
                class_id=cls.id, # Link by ID
                class_name=cls.class_name # Denormalized field if used
            ))
            s.flush()

            for j, g in enumerate(grades):
                # Distribute subjects like "Math", "English", "History" etc.
                subject_name = f"Subject-{j+1}" 
                s.add(Grade(
                    student_tz=tz, 
                    subject=subject_name,
                    teacher_name=f"Teacher-{j+1}",
                    grade=float(g), 
                    period="Q1"
                ))

            s.add(AttendanceRecord(
                student_tz=tz,
                absence=absence,
                absence_justified=1,
                late=late,
                disturbance=dist,
                total_absences=absence + 1,
                total_negative_events=neg,
                total_positive_events=pos,
                period="Q1",
                lessons_reported=100
            ))

        s.commit()

@pytest.fixture(scope="session")
def seeded_engine():
    """In-memory SQLite engine with seeded students."""
    eng = _create_engine()
    SQLModel.metadata.create_all(eng)
    _seed_db(eng)
    return eng

@pytest.fixture(scope="function")
def seeded_session(seeded_engine):
    """Session bound to the seeded engine.
    
    Using a transaction-based approach would be better for isolation if we were modifying data,
    but since we are mostly reading in these tests, sharing the engine is fine.
    """
    with Session(seeded_engine) as s:
        yield s

@pytest.fixture(scope="function")
def empty_session():
    """Session bound to an empty DB (tables exist, no rows)."""
    eng = _create_engine()
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        yield s
