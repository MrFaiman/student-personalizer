from ..schemas.analytics import (
    ClassComparisonItem,
    LayerKPIsResponse,
    MetadataResponse,
    SubjectGradeItem,
)
from ..schemas.advanced_analytics import (
    CascadingFilterOptions,
    PeriodComparisonResponse,
    RedStudentListResponse,
    RedStudentSegmentation,
    VersusChartData,
)


class AnalyticsDefaultView:
    """Default view presenter for Analytics data (includes advanced)."""

    def render_kpis(self, data: dict) -> LayerKPIsResponse:
        """Render Dashboard KPIs from pre-calculated data."""
        return LayerKPIsResponse(
            layer_average=data["layer_average"],
            avg_absences=data["avg_absences"],
            at_risk_students=data["at_risk_count"],
            total_students=data["total_students"],
        )

    def render_class_comparison(self, data: list[dict]) -> list[ClassComparisonItem]:
        """Render class comparison bar chart from pre-calculated data."""
        result = []
        for item in data:
            cls = item["class"]
            result.append(
                ClassComparisonItem(
                    id=cls.id,
                    class_name=cls.class_name,
                    average_grade=item["average_grade"],
                    student_count=item["student_count"],
                )
            )

        result.sort(key=lambda x: x.class_name)
        return result

    def render_metadata(self, data: dict) -> MetadataResponse:
        """Render metadata options."""
        return MetadataResponse(
            periods=data["periods"],
            grade_levels=data["grade_levels"],
            teachers=data["teachers"],
        )

    def render_student_radar(self, data: dict) -> list[SubjectGradeItem]:
        """Render student radar chart from pre-calculated averages."""
        return [
            SubjectGradeItem(subject=subject, grade=avg)
            for subject, avg in data.items()
        ]

    # --- Advanced Analytics Views ---

    def render_period_comparison(self, data: dict) -> PeriodComparisonResponse:
        """Render period comparison response."""
        return PeriodComparisonResponse(
            comparison_type=data["comparison_type"],
            period_a=data["period_a"],
            period_b=data["period_b"],
            data=data["data"],
        )

    def render_red_student_segmentation(self, data: dict) -> RedStudentSegmentation:
        """Render at-risk student segmentation."""
        return RedStudentSegmentation(
            total_red_students=data["total_red_students"],
            threshold=data["threshold"],
            by_class=data["by_class"],
            by_layer=data["by_layer"],
            by_teacher=data["by_teacher"],
            by_subject=data["by_subject"],
        )

    def render_red_student_list(self, data: dict) -> RedStudentListResponse:
        """Render paginated at-risk student list."""
        return RedStudentListResponse(
            total=data["total"],
            page=data["page"],
            page_size=data["page_size"],
            students=data["students"],
        )

    def render_versus_comparison(self, data: dict) -> VersusChartData:
        """Render versus comparison chart data."""
        return VersusChartData(
            comparison_type=data["comparison_type"],
            metric=data["metric"],
            series=data["series"],
        )

    def render_cascading_filter_options(self, data: dict) -> CascadingFilterOptions:
        """Render cascading filter options."""
        return CascadingFilterOptions(
            classes=data["classes"],
            teachers=data["teachers"],
            subjects=data["subjects"],
        )
