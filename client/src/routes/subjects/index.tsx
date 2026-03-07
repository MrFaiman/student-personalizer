import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen, Users, TrendingUp } from "lucide-react";
import { useFilters } from "@/components/FilterContext";
import { StatCard } from "@/components/StatCard";
import { analyticsApi } from "@/lib/api";

export const Route = createFileRoute("/subjects/")(
    { component: SubjectsListPage },
);

function SubjectsListPage() {
    const { t } = useTranslation("subjects");
    const { t: tc } = useTranslation();
    const { filters } = useFilters();

    const { data: subjects, isLoading } = useQuery({
        queryKey: ["subjects-list", filters.year, filters.period, filters.gradeLevel],
        queryFn: () =>
            analyticsApi.getSubjectsList({
                year: filters.year,
                period: filters.period,
                grade_level: filters.gradeLevel,
            }),
    });

    const totalSubjects = subjects?.length || 0;
    const overallAverage =
        subjects && subjects.length > 0
            ? (
                subjects.reduce((sum, s) => sum + (s.average_grade || 0), 0) /
                subjects.filter((s) => s.average_grade !== null).length
            ).toFixed(1)
            : "—";

    return (
        <div className="space-y-4">
            <Helmet>
                <title>{`${t("list.title")} | ${tc("appName")}`}</title>
            </Helmet>
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold">{t("list.title")}</h1>
                <p className="text-muted-foreground">{t("list.subtitle")}</p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <StatCard
                    icon={BookOpen}
                    iconClassName="text-primary"
                    iconBgClassName="bg-primary/10"
                    value={totalSubjects}
                    label={t("list.totalSubjects")}
                />
                <StatCard
                    icon={TrendingUp}
                    iconClassName="text-blue-600"
                    iconBgClassName="bg-blue-100"
                    value={overallAverage}
                    label={t("list.overallAverage")}
                />
            </div>

            {/* Subjects Grid */}
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
                ) : subjects?.length ? (
                    subjects.map((subject) => (
                        <Link
                            key={subject.id || subject.name}
                            to="/subjects/$subjectId"
                            params={{ subjectId: subject.id || subject.name }}
                        >
                            <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
                                <CardContent className="p-6">
                                    <div className="flex justify-between items-start mb-4">
                                        <h3 className="text-xl font-bold">{subject.name}</h3>
                                        <Badge variant="secondary">
                                            {t("list.teacherCount", { count: subject.teachers.length })}
                                        </Badge>
                                    </div>

                                    <div className="flex items-baseline gap-2 mb-4">
                                        <span className="text-4xl font-bold text-primary">
                                            {subject.average_grade?.toFixed(1) || "—"}
                                        </span>
                                        <span className="text-muted-foreground">{tc("table.average")}</span>
                                    </div>

                                    <div className="flex items-center justify-between text-sm border-t pt-4">
                                        <div className="flex items-center gap-1">
                                            <Users className="size-4 text-muted-foreground" />
                                            <span>{t("list.studentCount", { count: subject.student_count })}</span>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </Link>
                    ))
                ) : (
                    <div className="col-span-full text-center py-12 text-muted-foreground">
                        {t("list.noSubjects")}
                    </div>
                )}
            </div>
        </div>
    );
}
