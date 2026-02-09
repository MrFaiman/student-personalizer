import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { School, Users, AlertTriangle, TrendingUp } from "lucide-react";
import { useFilters } from "@/components/FilterContext";
import { studentsApi } from "@/lib/api";

export const Route = createFileRoute("/classes/")({
    component: ClassesListPage,
});

function ClassesListPage() {
    const { filters } = useFilters();

    const { data: classes, isLoading } = useQuery({
        queryKey: ["classes", filters.period],
        queryFn: () => studentsApi.getClasses({ period: filters.period }),
    });

    const totalStudents = classes?.reduce((sum, c) => sum + c.student_count, 0) || 0;
    const totalAtRisk = classes?.reduce((sum, c) => sum + c.at_risk_count, 0) || 0;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold">כיתות</h1>
                <p className="text-muted-foreground">צפייה וניתוח נתונים לפי כיתות</p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="bg-primary/10 rounded-lg p-2">
                            <School className="size-5 text-primary" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold">{classes?.length || 0}</p>
                            <p className="text-sm text-muted-foreground">כיתות</p>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="bg-blue-100 rounded-lg p-2">
                            <Users className="size-5 text-blue-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold">{totalStudents}</p>
                            <p className="text-sm text-muted-foreground">תלמידים</p>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="bg-red-100 rounded-lg p-2">
                            <AlertTriangle className="size-5 text-red-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-red-600">{totalAtRisk}</p>
                            <p className="text-sm text-muted-foreground">תלמידים בסיכון</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Classes Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {isLoading ? (
                    Array.from({ length: 6 }).map((_, i) => (
                        <Card key={i}>
                            <CardContent className="p-6">
                                <Skeleton className="h-6 w-20 mb-4" />
                                <Skeleton className="h-12 w-16 mb-4" />
                                <Skeleton className="h-4 w-full" />
                            </CardContent>
                        </Card>
                    ))
                ) : classes?.length ? (
                    classes.map((cls) => (
                        <Link key={`class-${cls.id}`} to="/classes/$classId" params={{ classId: String(cls.id) }}>
                            <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
                                <CardContent className="p-6">
                                    <div className="flex justify-between items-start mb-4">
                                        <div>
                                            <h3 className="text-xl font-bold">{cls.class_name}</h3>
                                            <p className="text-sm text-muted-foreground">שכבה {cls.grade_level}</p>
                                        </div>
                                        {cls.at_risk_count > 0 && (
                                            <Badge className="bg-red-100 text-red-700">
                                                {cls.at_risk_count} בסיכון
                                            </Badge>
                                        )}
                                    </div>

                                    <div className="flex items-baseline gap-2 mb-4">
                                        <span className="text-4xl font-bold text-primary">
                                            {cls.average_grade?.toFixed(1) || "—"}
                                        </span>
                                        <span className="text-muted-foreground">ממוצע</span>
                                    </div>

                                    <div className="flex items-center justify-between text-sm border-t pt-4">
                                        <div className="flex items-center gap-1">
                                            <Users className="size-4 text-muted-foreground" />
                                            <span>{cls.student_count} תלמידים</span>
                                        </div>
                                        <div className="flex items-center gap-1 text-primary">
                                            <TrendingUp className="size-4" />
                                            <span>צפה בפרטים</span>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </Link>
                    ))
                ) : (
                    <div className="col-span-full text-center py-12 text-muted-foreground">
                        לא נמצאו כיתות
                    </div>
                )}
            </div>
        </div>
    );
}
