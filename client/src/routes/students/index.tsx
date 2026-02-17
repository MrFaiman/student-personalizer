import { createFileRoute } from "@tanstack/react-router";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { Search, Users, AlertTriangle } from "lucide-react";
import { useFilters } from "@/components/FilterContext";
import { TablePagination } from "@/components/TablePagination";
import { StatCard } from "@/components/StatCard";
import { StudentLink } from "@/components/StudentLink";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { type StudentListItem } from "@/lib/types";
import { studentsApi } from "@/lib/api";
import { DEBOUNCE_DELAY_MS } from "@/lib/constants";
import { useConfigStore } from "@/lib/config-store";

export const Route = createFileRoute("/students/")(
    { component: StudentsListPage },
);

function useDebouncedValue<T>(value: T, delay: number): T {
    const [debounced, setDebounced] = useState(value);
    useEffect(() => {
        const timer = setTimeout(() => setDebounced(value), delay);
        return () => clearTimeout(timer);
    }, [value, delay]);
    return debounced;
}

function StudentsListPage() {
    const { t } = useTranslation("students");
    const { t: tc } = useTranslation();
    const { filters } = useFilters();
    const atRiskGradeThreshold = useConfigStore((s) => s.atRiskGradeThreshold);
    const defaultPageSize = useConfigStore((s) => s.defaultPageSize);
    const [search, setSearch] = useState("");
    const debouncedSearch = useDebouncedValue(search, DEBOUNCE_DELAY_MS);
    const [selectedClassId, setSelectedClassId] = useState<string>("__all__");
    const [showAtRiskOnly, setShowAtRiskOnly] = useState(false);
    const [page, setPage] = useState(1);
    const pageSize = defaultPageSize;


    const [prevPeriod, setPrevPeriod] = useState(filters.period);
    if (prevPeriod !== filters.period) {
        setPrevPeriod(filters.period);
        setPage(1);
    }

    const { data: classes } = useQuery({
        queryKey: ["classes", filters.period],
        queryFn: () => studentsApi.getClasses({ period: filters.period }),
    });

    const { data: dashboardStats } = useQuery({
        queryKey: ["dashboard-stats", filters.period, selectedClassId],
        queryFn: () =>
            studentsApi.getDashboardStats({
                period: filters.period,
                class_id: selectedClassId === "__all__" ? undefined : selectedClassId,
            }),
    });

    const { data: students, isLoading } = useQuery({
        queryKey: ["students", filters.period, selectedClassId, debouncedSearch, showAtRiskOnly, page],
        queryFn: () =>
            studentsApi.list({
                period: filters.period,
                class_id: selectedClassId === "__all__" ? undefined : selectedClassId,
                search: debouncedSearch || undefined,
                at_risk_only: showAtRiskOnly,
                page,
                page_size: pageSize,
            }),
        placeholderData: keepPreviousData,
    });

    const resetPage = () => setPage(1);

    const studentsList = students?.items || [];

    return (
        <div className="space-y-4">
            <Helmet>
                <title>{`${t("list.title")} | ${tc("appName")}`}</title>
            </Helmet>
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold">{t("list.title")}</h1>
                    <p className="text-muted-foreground">{t("list.subtitle")}</p>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard
                    icon={Users}
                    iconClassName="text-primary"
                    iconBgClassName="bg-primary/10"
                    value={dashboardStats?.total_students ?? students?.total ?? 0}
                    label={t("list.totalStudents")}
                />
                <StatCard
                    icon={AlertTriangle}
                    iconClassName="text-red-600"
                    iconBgClassName="bg-red-100"
                    value={dashboardStats?.at_risk_count ?? 0}
                    valueClassName="text-red-600"
                    label={t("list.atRiskStudents")}
                />
                <StatCard
                    icon={Users}
                    iconClassName="text-orange-600"
                    iconBgClassName="bg-orange-100"
                    value={classes?.length || 0}
                    label={t("list.classes")}
                />
            </div>

            {/* Filters */}
            <Card>
                <CardContent className="p-4">
                    <div className="flex flex-wrap gap-4 items-center">
                        <div className="relative flex-1 min-w-[200px]">
                            <Search className="absolute right-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                            <Input
                                className="pr-10"
                                aria-label={tc("filters.searchByStudentName")}
                                placeholder={tc("filters.searchByStudentName")}
                                value={search}
                                onChange={(e) => { setSearch(e.target.value); resetPage(); }}
                            />
                        </div>
                        <Select value={selectedClassId} onValueChange={(v) => { setSelectedClassId(v); resetPage(); }}>
                            <SelectTrigger className="w-40">
                                <SelectValue placeholder={tc("filters.allClasses")} />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="__all__">{tc("filters.allClasses")}</SelectItem>
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
                            {tc("filters.atRiskOnly")}
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
                            <TableHead className="text-right font-bold">{tc("table.studentName")}</TableHead>
                            <TableHead className="text-right font-bold">{tc("table.idNumber")}</TableHead>
                            <TableHead className="text-right font-bold">{tc("table.class")}</TableHead>
                            <TableHead className="text-right font-bold">{tc("table.averageGrade")}</TableHead>
                            <TableHead className="text-right font-bold">{tc("table.absences")}</TableHead>
                            <TableHead className="text-right font-bold">{tc("table.status")}</TableHead>

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

                                </TableRow>
                            ))
                        ) : studentsList.length ? (
                            studentsList.map((student: StudentListItem, index: number) => (
                                <TableRow key={student.student_tz} className="hover:bg-accent/30 transition-colors">
                                    <TableCell className="text-muted-foreground">{(page - 1) * pageSize + index + 1}</TableCell>
                                    <TableCell className="font-semibold">
                                        <StudentLink
                                            studentTz={student.student_tz}
                                            studentName={student.student_name}
                                        />
                                    </TableCell>
                                    <TableCell className="font-mono text-sm">{student.student_tz}</TableCell>
                                    <TableCell>{student.class_name}</TableCell>
                                    <TableCell
                                        className={`font-bold ${student.average_grade && student.average_grade < atRiskGradeThreshold ? "text-red-600" : ""}`}
                                    >
                                        {student.average_grade?.toFixed(1) || "—"}
                                    </TableCell>
                                    <TableCell>{student.total_absences}</TableCell>
                                    <TableCell><StatusBadge isAtRisk={student.is_at_risk} /></TableCell>

                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell colSpan={7} className="text-center text-muted-foreground py-12">
                                    {t("list.noStudents")}
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
