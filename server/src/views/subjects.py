from collections import Counter
from collections.abc import Iterable

from ..schemas.analytics import GradeHistogramBin
from ..schemas.subject import (
    SubjectClassDetail,
    SubjectDetailResponse,
    SubjectDetailStats,
    SubjectListItem,
    SubjectStatsResponse,
)


class SubjectDefaultView:
    """Default view presenter for Subject data."""

    def render_list(self, data: list[dict]) -> list[SubjectListItem]:
        """Render subject list with rounding and sorting."""
        items = []
        for item in data:
            avg = item["average_grade"]
            sid = str(item["id"]) if item["id"] else None

            # Sort teachers for stable output, filtering out None values
            teachers_sorted = sorted([t for t in item["teachers"] if t]) if item["teachers"] else []

            items.append(
                SubjectListItem(
                    id=sid,
                    name=item["name"],
                    student_count=item["student_count"],
                    average_grade=round(avg, 1) if avg else None,
                    teachers=teachers_sorted,
                )
            )

        # Sort by subject name by default
        return sorted(items, key=lambda x: x.name)

    def _create_histogram(self, grades: Iterable[float], bin_size: int = 10) -> list[GradeHistogramBin]:
        """Create histogram bins for grades."""
        bins = Counter()
        for grade in grades:
            # Group into bins, e.g., 90-100, 80-89
            bin_start = int(grade // bin_size) * bin_size
            if bin_start == 100:
                bin_start = 90  # Include 100 in the 90-100 bin
            bins[bin_start] += 1

        # Ensure all standard bins exist (0-10, 10-20,... 90-100)
        formatted_bins = []
        for i in range(0, 100, bin_size):
            formatted_bins.append(GradeHistogramBin(grade=i, count=bins.get(i, 0)))

        return formatted_bins

    def render_stats(self, data: dict) -> SubjectStatsResponse:
        """Render subject grade distribution."""
        grades = data.get("grades", [])
        total_students = data.get("total_students", 0)

        distribution = {
            "0-54": 0,
            "55-64": 0,
            "65-74": 0,
            "75-84": 0,
            "85-94": 0,
            "95-100": 0,
        }

        average_grade = None
        if grades:
            average_grade = round(sum(grades) / len(grades), 1)
            for g in grades:
                if g < 55:
                    distribution["0-54"] += 1
                elif g < 65:
                    distribution["55-64"] += 1
                elif g < 75:
                    distribution["65-74"] += 1
                elif g < 85:
                    distribution["75-84"] += 1
                elif g < 95:
                    distribution["85-94"] += 1
                else:
                    distribution["95-100"] += 1

        teachers_sorted = sorted([t for t in data.get("teachers", []) if t])

        return SubjectStatsResponse(
            subject_name=data["subject_name"],
            distribution=distribution,
            total_students=total_students,
            average_grade=average_grade,
            teachers=teachers_sorted,
        )

    def render_detail(self, data: dict) -> SubjectDetailResponse:
        """Render detailed subject view."""
        subject = data["subject"]
        stats = data["stats"]

        # Parse classes
        classes = sorted(
            [SubjectClassDetail(**c) for c in data["classes"]],
            key=lambda x: x.name,
        )

        # Parse histogram
        grades = [g.grade for g in data.get("grades", [])]
        histogram = self._create_histogram(grades)
        
        teachers_sorted = sorted([t for t in data.get("teachers", []) if t])

        return SubjectDetailResponse(
            id=str(subject.id),
            name=subject.subject_name,
            stats=SubjectDetailStats(**stats),
            teachers=teachers_sorted,
            classes=classes,
            grade_histogram=histogram,
        )
