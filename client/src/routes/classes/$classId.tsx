import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
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
import { ArrowRight, Users, Trophy, AlertCircle, Eye } from "lucide-react";
import { useFilters } from "@/components/FilterContext";
import type { HeatmapStudent, StudentRanking } from "@/lib/types";
import { analyticsApi, studentsApi } from "@/lib/api";

export const Route = createFileRoute("/classes/$classId")({
    component: ClassDetailPage,
});

function ClassDetailPage() {
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
            {/* Back Button */}
            <Link to="/classes">
                <Button variant="ghost" className="gap-2">
                    <ArrowRight className="size-4" />
                    חזרה לרשימת הכיתות
                </Button>
            </Link>

            {/* Header */}
            <div className="flex justify-between items-start">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">{classInfo?.class_name || `כיתה ${classId}`}</h2>
                    <p className="text-muted-foreground">
                        {classInfo?.student_count || 0} תלמידים | שכבה {classInfo?.grade_level || ""}
                    </p>
                </div>
                <div className="flex gap-4">
                    <Card className="px-4 py-2">
                        <div className="text-center">
                            <div className="text-2xl font-bold text-primary">
                                {classInfo?.average_grade?.toFixed(1) || "—"}
                            </div>
                            <div className="text-xs text-muted-foreground">ממוצע</div>
                        </div>
                    </Card>
                    <Card className="px-4 py-2">
                        <div className="text-center">
                            <div className="text-2xl font-bold text-red-600">{classInfo?.at_risk_count || 0}</div>
                            <div className="text-xs text-muted-foreground">בסיכון</div>
                        </div>
                    </Card>
                </div>
            </div>

            {/* Heatmap */}
            <Card>
                <CardContent className="p-6">
                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                        <Users className="size-5 text-primary" />
                        מפת חום: תלמידים × מקצועות
                    </h3>
                    {isLoadingHeatmap ? (
                        <Skeleton className="h-96" />
                    ) : heatmapData?.students.length ? (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr>
                                        <th className="text-right p-2 font-semibold sticky right-0 bg-background">
                                            תלמיד
                                        </th>
                                        {heatmapData.subjects.map((subject: string) => (
                                            <th key={subject} className="p-2 font-semibold text-center min-w-[60px]">
                                                {subject}
                                            </th>
                                        ))}
                                        <th className="p-2 font-semibold text-center">ממוצע</th>
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
                        <div className="text-center py-12 text-muted-foreground">אין נתונים להצגה</div>
                    )}
                    {/* ... legend ... */}
                </CardContent>
            </Card>

            {/* Top/Bottom Rankings */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Top Students */}
                <Card>
                    <CardContent className="p-6">
                        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <Trophy className="size-5 text-yellow-500" />
                            מצטיינים
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
                                        <TableHead className="text-right">מקום</TableHead>
                                        <TableHead className="text-right">שם</TableHead>
                                        <TableHead className="text-right">ממוצע</TableHead>
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
                                                    <Button variant="ghost" size="icon">
                                                        <Eye className="size-4" />
                                                    </Button>
                                                </Link>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">אין נתונים</div>
                        )}
                    </CardContent>
                </Card>

                {/* Bottom Students */}
                <Card>
                    <CardContent className="p-6">
                        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <AlertCircle className="size-5 text-red-500" />
                            דורשים תשומת לב
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
                                        <TableHead className="text-right">שם</TableHead>
                                        <TableHead className="text-right">ממוצע</TableHead>
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
                                                    <Button variant="ghost" size="icon">
                                                        <Eye className="size-4" />
                                                    </Button>
                                                </Link>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">אין נתונים</div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
