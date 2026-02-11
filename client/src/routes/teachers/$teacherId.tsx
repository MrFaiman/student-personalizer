import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { ArrowRight, BookOpen, School, BarChart3 } from "lucide-react";
import {
    AreaChart,
    Area,
    BarChart,
    Bar,
    Cell,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    CartesianGrid,
} from "recharts";
import { useFilters } from "@/components/FilterContext";
import { CLASS_COLORS } from "@/lib/utils";
import { analyticsApi } from "@/lib/api";
import { useState } from "react";

export const Route = createFileRoute("/teachers/$teacherId")({
    component: TeacherDetailPage,
});

const TOOLTIP_STYLE = {
    direction: "rtl" as const,
    textAlign: "right" as const,
    background: "hsl(var(--card))",
    border: "1px solid hsl(var(--border))",
    borderRadius: "8px",
};

function TeacherDetailPage() {
    const { t } = useTranslation("teachers");
    const { t: tc } = useTranslation();
    const { teacherId } = Route.useParams();
    const { filters } = useFilters();
    const [selectedClassId, setSelectedClassId] = useState<string>("__all__");

    const { data: teacher, isLoading } = useQuery({
        queryKey: ["teacher-detail", teacherId, filters.period],
        queryFn: () => analyticsApi.getTeacherDetail(teacherId, { period: filters.period }),
    });

    const selectedClassData = teacher?.class_performance.find((c) => c.class_id === selectedClassId);
    const activeHistogram = (
        selectedClassId === "__all__"
            ? teacher?.grade_histogram
            : selectedClassData?.grade_histogram
    ) ?? [];

    const classChartData = teacher?.class_performance.map((cls) => ({
        name: cls.class_name,
        average: cls.average_grade,
        students: cls.student_count,
        id: cls.class_id,
    })) ?? [];

    const subjectChartData = teacher?.subject_performance.map((s) => ({
        name: s.subject,
        average: s.average_grade,
        students: s.student_count,
    })) ?? [];

    if (isLoading) {
        return (
            <div className="space-y-6">
                <Skeleton className="h-10 w-40" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    if (!teacher) {
        return (
            <div className="text-center py-12 text-muted-foreground">
                {t("detail.notFound")}
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Back Button */}
            <Link to="/teachers">
                <Button variant="ghost" className="gap-2">
                    <ArrowRight className="size-4" />
                    {t("detail.backToList")}
                </Button>
            </Link>

            {/* Header */}
            <div className="flex justify-between items-start">
                <div>
                    <h1 className="text-2xl font-bold">{teacher.name}</h1>
                    <p className="text-muted-foreground">
                        {t("detail.subtitle", {
                            subjects: teacher.subjects.length,
                            classes: teacher.classes.length,
                        })}
                    </p>
                </div>
                <div className="flex gap-4">
                    <Card className="px-4 py-2">
                        <div className="text-center">
                            <div className="text-2xl font-bold text-primary tabular-nums">
                                {teacher.average_grade?.toFixed(1) || "—"}
                            </div>
                            <div className="text-xs text-muted-foreground">{tc("table.average")}</div>
                        </div>
                    </Card>
                    <Card className="px-4 py-2">
                        <div className="text-center">
                            <div className="text-2xl font-bold tabular-nums">{teacher.student_count}</div>
                            <div className="text-xs text-muted-foreground">{tc("general.students")}</div>
                        </div>
                    </Card>
                </div>
            </div>

            {/* Grade Distribution with Class Selector */}
            <Card>
                <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-bold flex items-center gap-2">
                            <BarChart3 className="size-5 text-primary" />
                            {t("detail.gradeDistribution")}
                        </h3>
                        {teacher.class_performance.length > 1 && (
                            <Select value={selectedClassId} onValueChange={setSelectedClassId}>
                                <SelectTrigger className="w-40 h-9 text-sm">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__all__">{t("detail.allClasses")}</SelectItem>
                                    {teacher.class_performance.map((cls) => (
                                        <SelectItem key={cls.class_id} value={cls.class_id}>
                                            {cls.class_name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        )}
                    </div>
                    <div className="h-64">
                        {activeHistogram.some((d) => d.count > 0) ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={activeHistogram}>
                                    <defs>
                                        <linearGradient id="distributionGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                    <XAxis
                                        dataKey="grade"
                                        type="number"
                                        domain={[0, 100]}
                                        tick={{ fontSize: 12 }}
                                        label={{ value: t("detail.gradeAxis"), position: "insideBottom", offset: -2, fontSize: 12 }}
                                    />
                                    <YAxis
                                        tick={{ fontSize: 12 }}
                                        allowDecimals={false}
                                        label={{ value: t("detail.studentCount"), angle: -90, position: "insideLeft", fontSize: 12 }}
                                    />
                                    <Tooltip
                                        contentStyle={TOOLTIP_STYLE}
                                        labelFormatter={(label) => `${t("detail.gradeAxis")}: ${label}`}
                                        formatter={(value) => [`${value}`, t("detail.studentCount")]}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="count"
                                        stroke="#6366f1"
                                        strokeWidth={2}
                                        fill="url(#distributionGrad)"
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex items-center justify-center h-full text-muted-foreground">
                                {tc("noData")}
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Per-Class Performance */}
            <Card>
                <CardContent className="p-6">
                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                        <School className="size-5 text-primary" />
                        {t("detail.classPerformance")}
                    </h3>
                    <div className="h-64">
                        {classChartData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={classChartData}>
                                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                                    <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                                    <Tooltip
                                        contentStyle={TOOLTIP_STYLE}
                                        formatter={(value) => [
                                            `${Number(value).toFixed(1)}`,
                                            tc("table.average"),
                                        ]}
                                    />
                                    <Bar dataKey="average" radius={[4, 4, 0, 0]}>
                                        {classChartData.map((_, i) => (
                                            <Cell key={i} fill={CLASS_COLORS[i % CLASS_COLORS.length]} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex items-center justify-center h-full text-muted-foreground">
                                {tc("noData")}
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Per-Subject Performance */}
            <Card>
                <CardContent className="p-6">
                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                        <BookOpen className="size-5 text-primary" />
                        {t("detail.subjectPerformance")}
                    </h3>
                    <div className="h-64">
                        {subjectChartData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={subjectChartData}>
                                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                                    <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                                    <Tooltip
                                        contentStyle={TOOLTIP_STYLE}
                                        formatter={(value) => [
                                            `${Number(value).toFixed(1)}`,
                                            tc("table.average"),
                                        ]}
                                    />
                                    <Bar dataKey="average" radius={[4, 4, 0, 0]}>
                                        {subjectChartData.map((_, i) => (
                                            <Cell key={i} fill={CLASS_COLORS[i % CLASS_COLORS.length]} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex items-center justify-center h-full text-muted-foreground">
                                {tc("noData")}
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
