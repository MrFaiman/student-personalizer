
from ..constants import AT_RISK_GRADE_THRESHOLD
from ..models import AttendanceRecord


def calculate_average(grades: list[float]) -> float | None:
    """Calculate the average of a list of grades."""
    if not grades:
        return None
    return sum(grades) / len(grades)


def calculate_at_risk_status(average: float | None) -> bool:
    """Determine if a student is at risk based on their average grade."""
    if average is None:
        return False
    return average < AT_RISK_GRADE_THRESHOLD


def sum_attendance_stats(records: list[AttendanceRecord]) -> dict[str, int]:
    """Sum attendance statistics from a list of records."""
    summary = {
        "absence": 0,
        "late": 0,
        "disturbance": 0,
        "total_negative_events": 0,
        "total_positive_events": 0,
        "total_absences": 0,
    }
    for record in records:
        summary["absence"] += record.absence
        summary["late"] += record.late
        summary["disturbance"] += record.disturbance
        summary["total_negative_events"] += record.total_negative_events
        summary["total_positive_events"] += record.total_positive_events
        summary["total_absences"] += record.total_absences

    return summary
