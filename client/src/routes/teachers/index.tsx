import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { UserCheck, Users, BookOpen, TrendingUp } from "lucide-react";
import { useFilters } from "@/components/FilterContext";
import { analyticsApi } from "@/lib/api";

export const Route = createFileRoute("/teachers/")({
    component: TeachersListPage,
});

function TeachersListPage() {
    const { t } = useTranslation("teachers");
    const { t: tc } = useTranslation();
    const { filters } = useFilters();

    const { data: teachers, isLoading } = useQuery({
        queryKey: ["teachers-list", filters.period, filters.gradeLevel],
        queryFn: () =>
            analyticsApi.getTeachersList({
                period: filters.period,
                grade_level: filters.gradeLevel,
            }),
    });

    const totalTeachers = teachers?.length || 0;
    const overallAverage =
        teachers && teachers.length > 0
            ? (
                  teachers.reduce((sum, t) => sum + (t.average_grade || 0), 0) /
                  teachers.filter((t) => t.average_grade !== null).length
              ).toFixed(1)
            : "—";

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold">{t("list.title")}</h1>
                <p className="text-muted-foreground">{t("list.subtitle")}</p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="bg-primary/10 rounded-lg p-2">
                            <UserCheck className="size-5 text-primary" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold">{totalTeachers}</p>
                            <p className="text-sm text-muted-foreground">{t("list.totalTeachers")}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="bg-blue-100 rounded-lg p-2">
                            <TrendingUp className="size-5 text-blue-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold">{overallAverage}</p>
                            <p className="text-sm text-muted-foreground">{t("list.overallAverage")}</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Teachers Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {isLoading ? (
                    Array.from({ length: 6 }).map((_, i) => (
                        <Card key={i}>
                            <CardContent className="p-6">
                                <Skeleton className="h-6 w-32 mb-4" />
                                <Skeleton className="h-12 w-16 mb-4" />
                                <Skeleton className="h-4 w-full" />
                            </CardContent>
                        </Card>
                    ))
                ) : teachers?.length ? (
                    teachers.map((teacher) => (
                        <Link
                            key={teacher.id}
                            to="/teachers/$teacherId"
                            params={{ teacherId: teacher.id }}
                        >
                            <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
                                <CardContent className="p-6">
                                    <div className="flex justify-between items-start mb-4">
                                        <h3 className="text-xl font-bold">{teacher.name}</h3>
                                        <Badge variant="secondary">
                                            {t("list.subjectCount", { count: teacher.subject_count })}
                                        </Badge>
                                    </div>

                                    <div className="flex items-baseline gap-2 mb-4">
                                        <span className="text-4xl font-bold text-primary">
                                            {teacher.average_grade?.toFixed(1) || "—"}
                                        </span>
                                        <span className="text-muted-foreground">{tc("table.average")}</span>
                                    </div>

                                    <div className="flex items-center justify-between text-sm border-t pt-4">
                                        <div className="flex items-center gap-1">
                                            <Users className="size-4 text-muted-foreground" />
                                            <span>{t("list.studentCount", { count: teacher.student_count })}</span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <BookOpen className="size-4 text-muted-foreground" />
                                            <span>{t("list.subjectCount", { count: teacher.subject_count })}</span>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </Link>
                    ))
                ) : (
                    <div className="col-span-full text-center py-12 text-muted-foreground">
                        {t("list.noTeachers")}
                    </div>
                )}
            </div>
        </div>
    );
}
