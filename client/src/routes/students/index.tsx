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
import { formatHebrewYear } from "@/lib/hebrew-year";
import { TablePagination } from "@/components/TablePagination";
import { SortableTableHead } from "@/components/SortableTableHead";
import { useTableSort } from "@/hooks/useTableSort";
import { StatCard } from "@/components/StatCard";
import { StudentLink } from "@/components/StudentLink";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { type StudentListItem } from "@/lib/types";
import { studentsApi, analyticsApi } from "@/lib/api";
import { DEBOUNCE_DELAY_MS } from "@/lib/constants";
import { useConfigStore } from "@/lib/config-store";
import { useAppForm } from "@/lib/form";
import { requireStudentData } from "@/lib/guards/require-student-data";

export const Route = createFileRoute("/students/")({
  beforeLoad: async () => {
    await requireStudentData();
  },
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
  const { t } = useTranslation("students");
  const { t: tc } = useTranslation();
  const { filters } = useFilters();
  const atRiskGradeThreshold = useConfigStore((s) => s.atRiskGradeThreshold);
  const defaultPageSize = useConfigStore((s) => s.defaultPageSize);
  const form = useAppForm({
    defaultValues: {
      search: "",
      selectedClassId: "__all__",
      showAtRiskOnly: false,
    },
  });
  const debouncedSearch = useDebouncedValue(
    form.state.values.search,
    DEBOUNCE_DELAY_MS,
  );
  const selectedClassId = form.state.values.selectedClassId;
  const showAtRiskOnly = form.state.values.showAtRiskOnly;
  const [page, setPage] = useState(1);
  const pageSize = defaultPageSize;
  const { sort, toggleSort } = useTableSort<string>();

  const [prevPeriod, setPrevPeriod] = useState(filters.period);
  const [prevYear, setPrevYear] = useState(filters.year);
  if (prevPeriod !== filters.period || prevYear !== filters.year) {
    setPrevPeriod(filters.period);
    setPrevYear(filters.year);
    setPage(1);
  }

  const { data: classes } = useQuery({
    queryKey: ["classes", filters.year, filters.period],
    queryFn: () =>
      studentsApi.getClasses({ year: filters.year, period: filters.period }),
  });

  const { data: dashboardStats } = useQuery({
    queryKey: [
      "dashboard-stats",
      filters.year,
      filters.period,
      selectedClassId,
    ],
    queryFn: () =>
      studentsApi.getDashboardStats({
        year: filters.year,
        period: filters.period,
        class_id: selectedClassId === "__all__" ? undefined : selectedClassId,
      }),
  });

  const { data: metadata } = useQuery({
    queryKey: ["metadata"],
    queryFn: () => analyticsApi.getMetadata(),
    staleTime: 5 * 60 * 1000,
  });

  const activeYear =
    filters.year || (metadata?.years.length ? metadata.years[0] : undefined);
  const sortedYears = [...(metadata?.years || [])].sort((a, b) => {
    const numA = parseInt(a) || 0;
    const numB = parseInt(b) || 0;
    return numB - numA;
  });
  const activeYearIndex = sortedYears.indexOf(activeYear || "");
  const prevYearStr =
    activeYearIndex >= 0 && activeYearIndex < sortedYears.length - 1
      ? sortedYears[activeYearIndex + 1]
      : undefined;

  const { data: prevDashboardStats } = useQuery({
    queryKey: ["dashboard-stats", prevYearStr, filters.period, selectedClassId],
    queryFn: () =>
      studentsApi.getDashboardStats({
        year: prevYearStr,
        period: filters.period,
        class_id: selectedClassId === "__all__" ? undefined : selectedClassId,
      }),
    enabled: !!prevYearStr,
  });

  const calculateTrend = (current: number, previous: number | undefined) => {
    if (previous === undefined) return undefined;
    if (previous === 0) return current > 0 ? 100 : undefined;
    return ((current - previous) / previous) * 100;
  };

  const { data: students, isLoading } = useQuery({
    queryKey: [
      "students",
      filters.year,
      filters.period,
      selectedClassId,
      debouncedSearch,
      showAtRiskOnly,
      page,
      sort.column,
      sort.direction,
    ],
    queryFn: () =>
      studentsApi.list({
        year: filters.year,
        period: filters.period,
        class_id: selectedClassId === "__all__" ? undefined : selectedClassId,
        search: debouncedSearch || undefined,
        at_risk_only: showAtRiskOnly,
        page,
        page_size: pageSize,
        sort_by: sort.column || undefined,
        sort_order: sort.direction,
      }),
    placeholderData: keepPreviousData,
  });

  const studentTrend = calculateTrend(
    dashboardStats?.total_students ?? students?.total ?? 0,
    prevDashboardStats?.total_students,
  );
  const atRiskTrend = calculateTrend(
    dashboardStats?.at_risk_count ?? 0,
    prevDashboardStats?.at_risk_count,
  );

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
          <p className="text-sm text-muted-foreground">
            {t("list.subtitle")}{" "}
            {activeYear ? `(${formatHebrewYear(activeYear)})` : ""}
          </p>
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
          trend={
            studentTrend !== undefined
              ? {
                  value: studentTrend,
                  label: tc("general.vsLastYear", "vs last year"),
                }
              : undefined
          }
        />
        <StatCard
          icon={AlertTriangle}
          iconClassName="text-red-600"
          iconBgClassName="bg-red-100"
          value={dashboardStats?.at_risk_count ?? 0}
          valueClassName="text-red-600"
          label={t("list.atRiskStudents")}
          trend={
            atRiskTrend !== undefined
              ? {
                  value: atRiskTrend,
                  label: tc("general.vsLastYear", "vs last year"),
                  invertColors: true,
                }
              : undefined
          }
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
            <form.Field name="search">
              {(field) => (
                <div className="relative flex-1 min-w-[200px]">
                  <Search className="absolute right-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                  <Input
                    className="pr-10"
                    aria-label={tc("filters.searchByStudentName")}
                    placeholder={tc("filters.searchByStudentName")}
                    value={field.state.value}
                    onChange={(e) => {
                      field.handleChange(e.target.value);
                      resetPage();
                    }}
                  />
                </div>
              )}
            </form.Field>
            <form.Field name="selectedClassId">
              {(field) => (
                <Select
                  value={field.state.value}
                  onValueChange={(v) => {
                    field.handleChange(v as typeof field.state.value);
                    resetPage();
                  }}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder={tc("filters.allClasses")} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">
                      {tc("filters.allClasses")}
                    </SelectItem>
                    {classes?.map((c) => (
                      <SelectItem
                        key={`class-select-${c.id}`}
                        value={String(c.id)}
                      >
                        {c.class_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </form.Field>
            <form.Field name="showAtRiskOnly">
              {(field) => (
                <Button
                  variant={field.state.value ? "default" : "outline"}
                  onClick={() => {
                    field.handleChange(!field.state.value);
                    resetPage();
                  }}
                >
                  <AlertTriangle className="size-4 ml-2" />
                  {tc("filters.atRiskOnly")}
                </Button>
              )}
            </form.Field>
          </div>
        </CardContent>
      </Card>

      {/* Students Table */}
      <Card className="shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-accent/50">
              <TableHead className="text-right font-bold w-12">#</TableHead>
              <SortableTableHead
                column="student_name"
                sort={sort}
                onSort={toggleSort}
              >
                {tc("table.studentName")}
              </SortableTableHead>
              <TableHead className="text-right font-bold">
                {tc("table.idNumber")}
              </TableHead>
              <SortableTableHead
                column="class_name"
                sort={sort}
                onSort={toggleSort}
              >
                {tc("table.class")}
              </SortableTableHead>
              <SortableTableHead
                column="average_grade"
                sort={sort}
                onSort={toggleSort}
              >
                {tc("table.averageGrade")}
              </SortableTableHead>
              <SortableTableHead
                column="total_absences"
                sort={sort}
                onSort={toggleSort}
              >
                {tc("table.absences")}
              </SortableTableHead>
              <TableHead className="text-right font-bold">
                {tc("table.status")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <Skeleton className="h-5 w-8" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-32" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-24" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-16" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-12" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-12" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-20" />
                  </TableCell>
                </TableRow>
              ))
            ) : studentsList.length ? (
              studentsList.map((student: StudentListItem, index: number) => (
                <TableRow
                  key={student.student_tz}
                  className="hover:bg-accent/30 transition-colors"
                >
                  <TableCell className="text-muted-foreground">
                    {(page - 1) * pageSize + index + 1}
                  </TableCell>
                  <TableCell className="font-semibold">
                    <StudentLink
                      studentTz={student.student_tz}
                      studentName={student.student_name}
                    />
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    {student.student_tz}
                  </TableCell>
                  <TableCell>{student.class_name}</TableCell>
                  <TableCell
                    className={`font-bold ${student.average_grade && student.average_grade < atRiskGradeThreshold ? "text-red-600" : ""}`}
                  >
                    {student.average_grade?.toFixed(1) || "-"}
                  </TableCell>
                  <TableCell>{student.total_absences}</TableCell>
                  <TableCell>
                    <StatusBadge isAtRisk={student.is_at_risk} />
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="text-center text-muted-foreground py-12"
                >
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
