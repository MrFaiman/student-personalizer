from ..schemas.student import (
    AttendanceResponse,
    ClassResponse,
    DashboardStats,
    GradeResponse,
    StudentDetailResponse,
    StudentListResponse,
)


class StudentDefaultView:
    """Default view presenter for Student data."""

    def render_list(self, data: dict) -> StudentListResponse:
        """Render the student list response from pre-calculated data."""
        return StudentListResponse(
            items=[
                StudentDetailResponse(**item) for item in data["items"]
            ],
            total=data["total"],
            page=data["page"],
            page_size=data["page_size"],
        )

    def render_detail(self, data: dict) -> StudentDetailResponse:
        """Render the student detail response from pre-calculated data."""
        return StudentDetailResponse(**data)

    def render_dashboard(self, data: dict) -> DashboardStats:
        """Render dashboard stats from pre-calculated data."""
        return DashboardStats(
            total_students=data["total_students"],
            average_grade=data["average_grade"],
            at_risk_count=data["at_risk_count"],
            total_classes=data["total_classes"],
            classes=[
                ClassResponse(**c) for c in data["classes"]
            ],
        )

    def render_grades(self, data: list[dict]) -> list[GradeResponse]:
        """Render grade list from pre-calculated data."""
        return [GradeResponse(**g) for g in data]

    def render_attendance(self, data: list[dict]) -> list[AttendanceResponse]:
        """Render attendance list from pre-calculated data."""
        return [AttendanceResponse(**a) for a in data]
