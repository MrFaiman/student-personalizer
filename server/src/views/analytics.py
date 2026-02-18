import numpy as np

from ..schemas.analytics import (
    CascadingFilterOptions,
    ClassComparisonItem,
    LayerKPIsResponse,
    MetadataResponse,
    PeriodComparisonResponse,
    RedStudentListResponse,
    RedStudentSegmentation,
    SubjectGradeItem,
    VersusChartData,
)
from .base import BaseView


class AnalyticsDefaultView(BaseView):
    """Default view presenter for Analytics data (includes advanced)."""

    def render_kpis(self, data: dict) -> LayerKPIsResponse:
        """Render Dashboard KPIs with rounding."""
        layer_avg = data["layer_average"]
        return LayerKPIsResponse(
            layer_average=round(layer_avg, 1) if layer_avg is not None else None,
            avg_absences=round(data["avg_absences"], 1),
            at_risk_students=data["at_risk_count"],
            total_students=data["total_students"],
        )

    def render_class_comparison(self, data: list[dict]) -> list[ClassComparisonItem]:
        """Render class comparison bar chart with rounding and sorting."""
        result = []
        for item in data:
            cls = item["class"]
            result.append(
                ClassComparisonItem(
                    id=cls.id,
                    class_name=cls.class_name,
                    average_grade=round(item["average_grade"], 1),
                    student_count=item["student_count"],
                )
            )

        result.sort(key=lambda x: x.class_name)
        return result

    def render_metadata(self, data: dict) -> MetadataResponse:
        """Render metadata options with sorting."""
        return MetadataResponse(
            periods=sorted(data["periods"]),
            grade_levels=sorted(data["grade_levels"]),
            teachers=sorted(data["teachers"]),
        )

    def render_student_radar(self, data: dict) -> list[SubjectGradeItem]:
        """Render student radar chart with rounding."""
        return [
            SubjectGradeItem(subject=subject, grade=round(avg, 1))
            for subject, avg in data.items()
        ]


    def _compute_period_item(self, item: dict) -> dict:
        """Compute averages, change, and change_percent from raw grade lists."""
        grades_a = item["grades_a"]
        grades_b = item["grades_b"]

        avg_a = round(float(np.mean(grades_a)), 1) if grades_a else None
        avg_b = round(float(np.mean(grades_b)), 1) if grades_b else None

        change = None
        change_percent = None
        if avg_a is not None and avg_b is not None:
            change = round(avg_b - avg_a, 1)
            if avg_a != 0:
                change_percent = round((change / avg_a) * 100, 1)

        return {
            "period_a_average": avg_a,
            "period_b_average": avg_b,
            "change": change,
            "change_percent": change_percent,
            "student_count_a": item["student_count_a"],
            "student_count_b": item["student_count_b"],
        }

    def render_period_comparison(self, data: dict) -> PeriodComparisonResponse:
        """Render period comparison: compute averages, change, sort, format names."""
        comparison_type = data["comparison_type"]
        result = []

        for item in data["data"]:
            computed = self._compute_period_item(item)

            if comparison_type == "class":
                result.append({
                    "id": item["id"],
                    "name": item["name"],
                    **computed,
                })
            elif comparison_type == "subject_teacher":
                name = f"{item['subject']} - {item['teacher_name']}"
                result.append({
                    "id": item["id"],
                    "name": name,
                    "subject": item["subject"],
                    "teacher_name": item["teacher_name"],
                    **computed,
                })
            else:  # subject
                teachers = item.get("teachers", set())
                teacher_name = ", ".join(sorted(teachers)) if teachers else None
                result.append({
                    "id": item["id"],
                    "name": item["subject"],
                    "subject": item["subject"],
                    "teacher_name": teacher_name,
                    **computed,
                })

        result.sort(key=lambda x: x["name"])

        return PeriodComparisonResponse(
            comparison_type=comparison_type,
            period_a=data["period_a"],
            period_b=data["period_b"],
            data=result,
        )

    def _format_segment(self, item: dict) -> dict:
        """Compute percentage and average_grade for a segmentation item."""
        total = item["total_student_count"]
        red_grades = item["red_grades"]
        return {
            "id": item["id"],
            "name": item["name"],
            "red_student_count": item["red_student_count"],
            "total_student_count": total,
            "percentage": round(item["red_student_count"] / total * 100, 1) if total > 0 else 0,
            "average_grade": round(sum(red_grades) / len(red_grades), 1) if red_grades else 0,
        }

    def render_red_student_segmentation(self, data: dict) -> RedStudentSegmentation:
        """Render at-risk student segmentation with rounding and sorting."""
        by_class = [self._format_segment(item) for item in data["by_class"]]
        by_layer = [self._format_segment(item) for item in data["by_layer"]]
        by_teacher = [self._format_segment(item) for item in data["by_teacher"]]
        by_subject = [self._format_segment(item) for item in data["by_subject"]]

        return RedStudentSegmentation(
            total_red_students=data["total_red_students"],
            threshold=data["threshold"],
            by_class=sorted(by_class, key=lambda x: x["name"]),
            by_layer=sorted(by_layer, key=lambda x: x["name"]),
            by_teacher=sorted(by_teacher, key=lambda x: -x["red_student_count"]),
            by_subject=sorted(by_subject, key=lambda x: -x["red_student_count"]),
        )

    def render_red_student_list(self, data: dict) -> RedStudentListResponse:
        """Render paginated at-risk student list with rounding."""
        students = [
            {**s, "average_grade": round(s["average_grade"], 1)}
            for s in data["students"]
        ]
        return RedStudentListResponse(
            total=data["total"],
            page=data["page"],
            page_size=data["page_size"],
            students=students,
        )

    def render_versus_comparison(self, data: dict) -> VersusChartData:
        """Render versus comparison chart data with rounding."""
        series = [
            {**s, "value": round(s["value"], 1)}
            for s in data["series"]
        ]
        return VersusChartData(
            comparison_type=data["comparison_type"],
            metric=data["metric"],
            series=series,
        )

    def render_cascading_filter_options(self, data: dict) -> CascadingFilterOptions:
        """Render cascading filter options with sorting."""
        return CascadingFilterOptions(
            classes=data["classes"],
            teachers=data["teachers"],
            subjects=sorted(data["subjects"]),
        )
