import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Users, Trophy, AlertCircle, Eye } from "lucide-react";
import { useFilters } from "@/components/FilterContext";
import { PageHeader } from "@/components/PageHeader";
import type { HeatmapStudent, StudentRanking } from "@/lib/types";
import { analyticsApi, studentsApi } from "@/lib/api";

export const Route = createFileRoute("/classes/$classId")(
    { component: ClassDetailPage },
);

function ClassDetailPage() {
    const { t } = useTranslation("classes");
    const { t: tc } = useTranslation();
    const { classId } = Route.useParams();
    const { filters } = useFilters();

    const { data: classes } = useQuery({
        queryKey: ["classes", filters.period],
        queryFn: () => studentsApi.getClasses({ period: filters.period }),
    });

    const classInfo = classes?.find((c) => c.id === classId);

    const { data: heatmapData, isLoading: isLoadingHeatmap } = useQuery({
        queryKey: ["class-heatmap", classId, filters.period],
        queryFn: () => analyticsApi.getClassHeatmap(classId, { period: filters.period }),
    });

    const { data: rankings, isLoading: isLoadingRankings } = useQuery({
        queryKey: ["class-rankings", classId, filters.period],
        queryFn: () => analyticsApi.getClassRankings(classId, { period: filters.period }),
    });

    const getGradeColor = (grade: number | null) => {
        if (grade === null) return "bg-gray-100";
        if (grade >= 85) return "bg-green-500 text-white";
        if (grade >= 70) return "bg-green-300";
        if (grade >= 55) return "bg-yellow-300";
        return "bg-red-400 text-white";
    };

    return (
        <div className="space-y-6">
            <PageHeader
                backTo="/classes"
                backLabel={t("detail.backToList")}
                title={classInfo?.class_name || t("detail.classTitle", { id: classId })}
                subtitle={t("detail.studentsAndLevel", { count: classInfo?.student_count || 0, level: classInfo?.grade_level || "" })}
                stats={[
                    { value: classInfo?.average_grade?.toFixed(1) || "—", label: t("detail.average") },
                    { value: classInfo?.at_risk_count || 0, label: t("detail.atRisk"), valueClassName: "text-red-600" },
                ]}
            />

            {/* Heatmap */}
            <Card>
                <CardContent className="p-6">
                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                        <Users className="size-5 text-primary" />
                        {t("detail.heatmapTitle")}
                    </h3>
                    {isLoadingHeatmap ? (
                        <Skeleton className="h-96" />
                    ) : heatmapData?.students.length ? (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr>
                                        <th className="text-right p-2 font-semibold sticky right-0 bg-background">
                                            {tc("table.student")}
                                        </th>
                                        {heatmapData.subjects.map((subject: string) => (
                                            <th key={subject} className="p-2 font-semibold text-center min-w-[60px]">
                                                {subject}
                                            </th>
                                        ))}
                                        <th className="p-2 font-semibold text-center">{tc("table.average")}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {heatmapData.students.map((student: HeatmapStudent) => (
                                        <tr key={student.student_tz} className="border-t">
                                            <td className="p-2 sticky right-0 bg-background">
                                                <Link
                                                    to="/students/$studentTz"
                                                    params={{ studentTz: student.student_tz }}
                                                    className="hover:text-primary hover:underline"
                                                >
                                                    {student.student_name}
                                                </Link>
                                            </td>
                                            {heatmapData.subjects.map((subject: string) => (
                                                <td key={subject} className="p-1 text-center">
                                                    <div
                                                        className={`rounded px-2 py-1 text-xs font-medium ${getGradeColor(
                                                            student.grades[subject] ?? null
                                                        )}`}
                                                    >
                                                        {student.grades[subject]?.toFixed(0) || "—"}
                                                    </div>
                                                </td>
                                            ))}
                                            <td className="p-1 text-center">
                                                <div className="font-bold">{student.average.toFixed(1)}</div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="text-center py-12 text-muted-foreground">{tc("noData")}</div>
                    )}
                </CardContent>
            </Card>

            {/* Top/Bottom Rankings */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Top Students */}
                <Card>
                    <CardContent className="p-6">
                        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <Trophy className="size-5 text-yellow-500" />
                            {t("detail.topStudents")}
                        </h3>
                        {isLoadingRankings ? (
                            <div className="space-y-2">
                                {Array.from({ length: 5 }).map((_, i) => (
                                    <Skeleton key={i} className="h-12" />
                                ))}
                            </div>
                        ) : rankings?.top.length ? (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="text-right">{tc("table.rank")}</TableHead>
                                        <TableHead className="text-right">{tc("table.name")}</TableHead>
                                        <TableHead className="text-right">{tc("table.average")}</TableHead>
                                        <TableHead></TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {rankings.top.map((student: StudentRanking, index: number) => (
                                        <TableRow key={student.student_tz}>
                                            <TableCell>
                                                <Badge variant="outline" className="font-bold">
                                                    #{index + 1}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="font-medium">{student.student_name}</TableCell>
                                            <TableCell className="font-bold text-green-600">
                                                {student.average.toFixed(1)}
                                            </TableCell>
                                            <TableCell>
                                                <Link to="/students/$studentTz" params={{ studentTz: student.student_tz }}>
                                                    <Button variant="ghost" size="icon" aria-label={tc("viewStudent")}>
                                                        <Eye className="size-4" />
                                                    </Button>
                                                </Link>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">{t("detail.noData")}</div>
                        )}
                    </CardContent>
                </Card>

                {/* Bottom Students */}
                <Card>
                    <CardContent className="p-6">
                        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <AlertCircle className="size-5 text-red-500" />
                            {t("detail.bottomStudents")}
                        </h3>
                        {isLoadingRankings ? (
                            <div className="space-y-2">
                                {Array.from({ length: 5 }).map((_, i) => (
                                    <Skeleton key={i} className="h-12" />
                                ))}
                            </div>
                        ) : rankings?.bottom.length ? (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="text-right">{tc("table.name")}</TableHead>
                                        <TableHead className="text-right">{tc("table.average")}</TableHead>
                                        <TableHead></TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {rankings.bottom.map((student: StudentRanking) => (
                                        <TableRow key={student.student_tz}>
                                            <TableCell className="font-medium">{student.student_name}</TableCell>
                                            <TableCell
                                                className={`font-bold ${student.average < 55 ? "text-red-600" : "text-orange-600"}`}
                                            >
                                                {student.average.toFixed(1)}
                                            </TableCell>
                                            <TableCell>
                                                <Link to="/students/$studentTz" params={{ studentTz: student.student_tz }}>
                                                    <Button variant="ghost" size="icon" aria-label={tc("viewStudent")}>
                                                        <Eye className="size-4" />
                                                    </Button>
                                                </Link>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">{t("detail.noData")}</div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
