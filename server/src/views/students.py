from ..schemas.student import (
    AttendanceResponse,
    ClassResponse,
    DashboardStats,
    GradeResponse,
    StudentDetailResponse,
    StudentListResponse,
)


def _round_grade(val: float | None) -> float | None:
    return round(val, 1) if val is not None else None


class StudentDefaultView:
    """Default view presenter for Student data."""

    def render_list(self, data: dict) -> StudentListResponse:
        """Render the student list response with rounding."""
        items = [
            StudentDetailResponse(**{**item, "average_grade": _round_grade(item["average_grade"])})
            for item in data["items"]
        ]
        return StudentListResponse(
            items=items,
            total=data["total"],
            page=data["page"],
            page_size=data["page_size"],
        )

    def render_detail(self, data: dict) -> StudentDetailResponse:
        """Render the student detail response with rounding."""
        return StudentDetailResponse(**{**data, "average_grade": _round_grade(data["average_grade"])})

    def render_dashboard(self, data: dict) -> DashboardStats:
        """Render dashboard stats with rounding and sorting."""
        classes = sorted(
            [
                ClassResponse(**{**c, "average_grade": _round_grade(c["average_grade"])})
                for c in data["classes"]
            ],
            key=lambda x: x.class_name,
        )
        return DashboardStats(
            total_students=data["total_students"],
            average_grade=_round_grade(data["average_grade"]),
            at_risk_count=data["at_risk_count"],
            total_classes=data["total_classes"],
            classes=classes,
        )

    def render_grades(self, data: list[dict]) -> list[GradeResponse]:
        """Render grade list from pre-calculated data."""
        return [GradeResponse(**g) for g in data]

    def render_attendance(self, data: list[dict]) -> list[AttendanceResponse]:
        """Render attendance list from pre-calculated data."""
        return [AttendanceResponse(**a) for a in data]
