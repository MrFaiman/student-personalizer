import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { useState, useEffect, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Search, Eye, Users, AlertTriangle } from "lucide-react";
import { useFilters } from "@/components/FilterContext";
import { TablePagination } from "@/components/TablePagination";
import { type StudentListItem } from "@/lib/types";
import { studentsApi } from "@/lib/api";

export const Route = createFileRoute("/students/")({
    component: StudentsListPage,
});

function useDebouncedValue<T>(value: T, delay: number): T {
    const [debounced, setDebounced] = useState(value);
    useEffect(() => {
        const timer = setTimeout(() => setDebounced(value), delay);
        return () => clearTimeout(timer);
    }, [value, delay]);
    return debounced;
}

function StudentsListPage() {
    const { filters } = useFilters();
    const [search, setSearch] = useState("");
    const debouncedSearch = useDebouncedValue(search, 300);
    const [selectedClassId, setSelectedClassId] = useState<string>("__all__");
    const [showAtRiskOnly, setShowAtRiskOnly] = useState(false);
    const [page, setPage] = useState(1);
    const pageSize = 20;

    // Reset page to 1 when global filters change
    const prevPeriod = useRef(filters.period);
    useEffect(() => {
        if (prevPeriod.current !== filters.period) {
            prevPeriod.current = filters.period;
            setPage(1);
        }
    }, [filters.period]);

    const { data: classes } = useQuery({
        queryKey: ["classes", filters.period],
        queryFn: () => studentsApi.getClasses({ period: filters.period }),
    });

    const { data: dashboardStats } = useQuery({
        queryKey: ["dashboard-stats", filters.period, selectedClassId],
        queryFn: () =>
            studentsApi.getDashboardStats({
                period: filters.period,
                class_id: selectedClassId === "__all__" ? undefined : Number(selectedClassId),
            }),
    });

    const { data: students, isLoading } = useQuery({
        queryKey: ["students", filters.period, selectedClassId, debouncedSearch, showAtRiskOnly, page],
        queryFn: () =>
            studentsApi.list({
                period: filters.period,
                class_id: selectedClassId === "__all__" ? undefined : Number(selectedClassId),
                search: debouncedSearch || undefined,
                at_risk_only: showAtRiskOnly,
                page,
                page_size: pageSize,
            }),
        placeholderData: keepPreviousData,
    });

    // Reset page when filters change (not on page change itself)
    const resetPage = () => setPage(1);

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "at_risk":
                return <Badge className="bg-red-100 text-red-700 hover:bg-red-100">סיכון גבוה</Badge>;
            case "watch":
                return <Badge className="bg-orange-100 text-orange-700 hover:bg-orange-100">במעקב</Badge>;
            default:
                return <Badge variant="secondary" className="bg-green-100 text-green-700 hover:bg-green-100">תקין</Badge>;
        }
    };

    const studentsList = students?.items || [];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold">ניהול תלמידים</h1>
                    <p className="text-muted-foreground">צפייה ומעקב אחר כל התלמידים במערכת</p>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="bg-primary/10 rounded-lg p-2">
                            <Users className="size-5 text-primary" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold">{dashboardStats?.total_students ?? students?.total ?? 0}</p>
                            <p className="text-sm text-muted-foreground">סה"כ תלמידים</p>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="bg-red-100 rounded-lg p-2">
                            <AlertTriangle className="size-5 text-red-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-red-600">{dashboardStats?.at_risk_count ?? 0}</p>
                            <p className="text-sm text-muted-foreground">תלמידים בסיכון</p>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="bg-orange-100 rounded-lg p-2">
                            <Users className="size-5 text-orange-600" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold">{classes?.length || 0}</p>
                            <p className="text-sm text-muted-foreground">כיתות</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Filters */}
            <Card>
                <CardContent className="p-4">
                    <div className="flex flex-wrap gap-4 items-center">
                        <div className="relative flex-1 min-w-[200px]">
                            <Search className="absolute right-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                            <Input
                                className="pr-10"
                                placeholder="חיפוש לפי שם תלמיד..."
                                value={search}
                                onChange={(e) => { setSearch(e.target.value); resetPage(); }}
                            />
                        </div>
                        <Select value={selectedClassId} onValueChange={(v) => { setSelectedClassId(v); resetPage(); }}>
                            <SelectTrigger className="w-40">
                                <SelectValue placeholder="כל הכיתות" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="__all__">כל הכיתות</SelectItem>
                                {classes?.map((c) => (
                                    <SelectItem key={`class-select-${c.id}`} value={String(c.id)}>
                                        {c.class_name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <Button
                            variant={showAtRiskOnly ? "default" : "outline"}
                            onClick={() => { setShowAtRiskOnly(!showAtRiskOnly); resetPage(); }}
                        >
                            <AlertTriangle className="size-4 ml-2" />
                            תלמידים בסיכון בלבד
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Students Table */}
            <Card className="shadow-sm overflow-hidden">
                <Table>
                    <TableHeader>
                        <TableRow className="bg-accent/50">
                            <TableHead className="text-right font-bold w-12">#</TableHead>
                            <TableHead className="text-right font-bold">שם התלמיד</TableHead>
                            <TableHead className="text-right font-bold">ת.ז.</TableHead>
                            <TableHead className="text-right font-bold">כיתה</TableHead>
                            <TableHead className="text-right font-bold">ממוצע ציונים</TableHead>
                            <TableHead className="text-right font-bold">חיסורים</TableHead>
                            <TableHead className="text-right font-bold">סטטוס</TableHead>
                            <TableHead className="text-right font-bold">פעולות</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            Array.from({ length: 5 }).map((_, i) => (
                                <TableRow key={i}>
                                    <TableCell><Skeleton className="h-5 w-8" /></TableCell>
                                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                                    <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                                    <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                                    <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                                    <TableCell><Skeleton className="h-8 w-8" /></TableCell>
                                </TableRow>
                            ))
                        ) : studentsList.length ? (
                            studentsList.map((student: StudentListItem, index: number) => (
                                <TableRow key={student.student_tz} className="hover:bg-accent/30 transition-colors">
                                    <TableCell className="text-muted-foreground">{(page - 1) * pageSize + index + 1}</TableCell>
                                    <TableCell className="font-semibold">{student.student_name}</TableCell>
                                    <TableCell className="font-mono text-sm">{student.student_tz}</TableCell>
                                    <TableCell>{student.class_name}</TableCell>
                                    <TableCell
                                        className={`font-bold ${student.average_grade && student.average_grade < 55 ? "text-red-600" : ""
                                            }`}
                                    >
                                        {student.average_grade?.toFixed(1) || "—"}
                                    </TableCell>
                                    <TableCell>{student.total_absences}</TableCell>
                                    <TableCell>{getStatusBadge(student.is_at_risk ? "at_risk" : "normal")}</TableCell>
                                    <TableCell>
                                        <Link to="/students/$studentTz" params={{ studentTz: student.student_tz }}>
                                            <Button variant="ghost" size="icon" className="text-primary hover:text-primary">
                                                <Eye className="size-5" />
                                            </Button>
                                        </Link>
                                    </TableCell>
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell colSpan={8} className="text-center text-muted-foreground py-12">
                                    לא נמצאו תלמידים
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
                <TablePagination
                    page={page}
                    totalPages={Math.ceil((students?.total || 0) / pageSize)}
                    onPageChange={setPage}
                />
            </Card>
        </div>
    );
}
