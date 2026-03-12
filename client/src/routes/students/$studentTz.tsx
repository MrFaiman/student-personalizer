import { useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
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
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import {
  ArrowRight,
  ArrowLeftRight,
  User,
  GraduationCap,
  Calendar,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  BookOpen,
  Clock,
  History,
} from "lucide-react";
import { studentsApi } from "@/lib/api";
import { StatCard } from "@/components/StatCard";
import { SortableTableHead } from "@/components/SortableTableHead";
import { TablePagination } from "@/components/TablePagination";
import { useTableSort, useClientSort } from "@/hooks/useTableSort";
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent, type ChartConfig } from "@/components/ui/chart";
import { BAR_COLORS, getBarColor } from "@/lib/utils";
import { RECENT_GRADES_COUNT } from "@/lib/constants";
import { useConfigStore } from "@/lib/config-store";
import type {
  GradeResponse,
  AttendanceResponse,
  StudentTimelinePoint,
} from "@/lib/types";
import { useFilters } from "@/components/FilterContext";

export const Route = createFileRoute("/students/$studentTz")({
  component: RouteComponent,
});

function formatPeriodWithYear(period?: string | null, year?: string | null) {
  const safePeriod = period || "-";
  if (!year) return safePeriod;
  return `${safePeriod} - ${year}`;
}

function RouteComponent() {
  const { t } = useTranslation("students");
  const { t: tc } = useTranslation();
  const { studentTz } = Route.useParams();
  const { filters, setFilter } = useFilters();
  const atRiskGradeThreshold = useConfigStore((s) => s.atRiskGradeThreshold);
  const goodGradeThreshold = useConfigStore((s) => s.goodGradeThreshold);
  const performanceGoodThreshold = useConfigStore(
    (s) => s.performanceGoodThreshold,
  );
  const performanceMediumThreshold = useConfigStore(
    (s) => s.performanceMediumThreshold,
  );
  const gradeRange = useConfigStore((s) => s.gradeRange);
  const pageSize = useConfigStore((s) => s.defaultPageSize);
  const [gradePage, setGradePage] = useState(1);
  const [attendancePage, setAttendancePage] = useState(1);

  const { data: student, isLoading } = useQuery({
    queryKey: ["student", filters.year, studentTz],
    queryFn: () => studentsApi.get(studentTz, { year: filters.year }),
  });

  const { data: grades } = useQuery({
    queryKey: ["student-grades", filters.year, studentTz],
    queryFn: () => studentsApi.getGrades(studentTz, { year: filters.year }),
  });

  const { data: attendance } = useQuery({
    queryKey: ["student-attendance", filters.year, studentTz],
    queryFn: () => studentsApi.getAttendance(studentTz, { year: filters.year }),
  });

  const { data: timelineData } = useQuery({
    queryKey: ["student-timeline", studentTz],
    queryFn: () => studentsApi.getTimeline(studentTz),
  });

  // All-year data for the period comparison section (no year filter)
  const { data: allGrades } = useQuery({
    queryKey: ["student-grades-all", studentTz],
    queryFn: () => studentsApi.getGrades(studentTz),
  });

  const { data: allAttendance } = useQuery({
    queryKey: ["student-attendance-all", studentTz],
    queryFn: () => studentsApi.getAttendance(studentTz),
  });

  const { subjectData } = useMemo(() => {
    if (!grades?.length) return { subjectData: [] };

    const periodsSet = new Set<string>();
    const bySubject = new Map<
      string,
      { sum: number; count: number; teachers: Set<string> }
    >();

    for (const g of grades) {
      const p = g.period || "-";
      periodsSet.add(p);

      const entry = bySubject.get(g.subject);
      const teacherName = g.teacher_name || "-";
      if (entry) {
        entry.sum += g.grade;
        entry.count += 1;
        if (teacherName !== "-") entry.teachers.add(teacherName);
      } else {
        bySubject.set(g.subject, {
          sum: g.grade,
          count: 1,
          teachers: new Set(teacherName !== "-" ? [teacherName] : []),
        });
      }
    }

    const subjectData = Array.from(bySubject.entries()).map(
      ([subject, { sum, count, teachers }]) => ({
        subject,
        average: Math.round(sum / count),
        teachers: teachers.size > 0 ? Array.from(teachers).join(", ") : "-",
      }),
    );

    return { subjectData };
  }, [grades]);

  const totalLessons =
    attendance?.reduce((sum, a) => sum + a.lessons_reported, 0) || 0;
  const totalAttendance =
    attendance?.reduce((sum, a) => sum + a.attendance, 0) || 0;
  const attendanceRate =
    totalLessons > 0 ? (totalAttendance / totalLessons) * 100 : 0;

  const gradeTrend =
    grades?.slice(-RECENT_GRADES_COUNT).map((g, i) => ({
      index: i + 1,
      grade: g.grade,
      subject: g.subject,
      teacher: g.teacher_name || "-",
    })) || [];

  const { sort: gradeSort, toggleSort: toggleGradeSort } =
    useTableSort<string>();
  const gradeAccessors = useMemo(
    () => ({
      subject: (g: GradeResponse) => g.subject,
      teacher_name: (g: GradeResponse) => g.teacher_name || "",
      grade: (g: GradeResponse) => g.grade,
      period: (g: GradeResponse) => `${g.year || ""}-${g.period || ""}`,
    }),
    [],
  );
  const sortedGrades = useClientSort(grades || [], gradeSort, gradeAccessors);
  const gradeTotalPages = Math.max(
    1,
    Math.ceil(sortedGrades.length / pageSize),
  );
  const pagedGrades = sortedGrades.slice(
    (gradePage - 1) * pageSize,
    gradePage * pageSize,
  );

  const { sort: attSort, toggleSort: toggleAttSort } = useTableSort<string>();
  const attAccessors = useMemo(
    () => ({
      period: (a: AttendanceResponse) => `${a.year || ""}-${a.period || ""}`,
      total_absences: (a: AttendanceResponse) => a.total_absences,
      attendance: (a: AttendanceResponse) =>
        a.lessons_reported > 0 ? a.attendance / a.lessons_reported : 0,
    }),
    [],
  );
  const sortedAttendance = useClientSort(
    attendance || [],
    attSort,
    attAccessors,
  );
  const attendanceTotalPages = Math.max(
    1,
    Math.ceil(sortedAttendance.length / pageSize),
  );
  const pagedAttendance = sortedAttendance.slice(
    (attendancePage - 1) * pageSize,
    attendancePage * pageSize,
  );

  // Reset page to 1 when key deps change (state-during-render pattern)
  const gradeResetKey = `${filters.year}-${studentTz}-${gradeSort.column}-${gradeSort.direction}`;
  const [prevGradeResetKey, setPrevGradeResetKey] = useState(gradeResetKey);
  if (gradeResetKey !== prevGradeResetKey) {
    setPrevGradeResetKey(gradeResetKey);
    if (gradePage !== 1) setGradePage(1);
  } else if (gradePage > gradeTotalPages) {
    setGradePage(gradeTotalPages);
  }

  const attResetKey = `${filters.year}-${studentTz}-${attSort.column}-${attSort.direction}`;
  const [prevAttResetKey, setPrevAttResetKey] = useState(attResetKey);
  if (attResetKey !== prevAttResetKey) {
    setPrevAttResetKey(attResetKey);
    if (attendancePage !== 1) setAttendancePage(1);
  } else if (attendancePage > attendanceTotalPages) {
    setAttendancePage(attendanceTotalPages);
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Skeleton className="h-[30vh]" />
          <Skeleton className="h-[30vh]" />
          <Skeleton className="h-[30vh]" />
        </div>
      </div>
    );
  }

  if (!student) {
    return (
      <div className="text-center py-12">
        <User className="size-16 text-muted-foreground mx-auto mb-4" />
        <h2 className="text-xl font-bold mb-2">{t("detail.notFound")}</h2>
        <Link to="/students">
          <Button>{t("detail.backToList")}</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Helmet>
        <title>{`${student.student_name} | ${tc("appName")}`}</title>
      </Helmet>
      {/* Header with back button */}
      <div className="flex items-center gap-4">
        <Link to="/students">
          <Button
            variant="ghost"
            size="icon"
            aria-label={t("detail.backToListAria")}
          >
            <ArrowRight className="size-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{student.student_name}</h1>
          <p className="text-muted-foreground">
            {t("detail.classAndId", {
              className: student.class_name,
              tz: student.student_tz,
            })}
          </p>
        </div>
        {student.is_at_risk ? (
          <Badge className="bg-red-100 text-red-700">
            {tc("status.atRisk")}
          </Badge>
        ) : (
          <Badge className="bg-green-100 text-green-700">
            {tc("status.normal")}
          </Badge>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {/* Performance Score Gauge */}
        <Card className="md:row-span-1">
          <CardContent className="p-4 flex flex-col items-center justify-center gap-1">
            {student.performance_score != null ? (
              <>
                <div className="relative size-20">
                  <svg viewBox="0 0 36 36" className="size-20 -rotate-90">
                    <circle
                      cx="18"
                      cy="18"
                      r="15.5"
                      fill="none"
                      stroke="hsl(var(--muted))"
                      strokeWidth="3"
                    />
                    <circle
                      cx="18"
                      cy="18"
                      r="15.5"
                      fill="none"
                      stroke={
                        student.performance_score >= performanceGoodThreshold
                          ? "#22c55e"
                          : student.performance_score >=
                              performanceMediumThreshold
                            ? "#f59e0b"
                            : "#ef4444"
                      }
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeDasharray={`${student.performance_score * 0.9738} 97.38`}
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-lg font-bold tabular-nums">
                    {student.performance_score.toFixed(0)}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground text-center">
                  {t("detail.performanceScore")}
                </p>
              </>
            ) : (
              <>
                <div className="relative size-20 flex items-center justify-center">
                  <span className="text-2xl font-bold text-muted-foreground">
                    -
                  </span>
                </div>
                <p className="text-sm text-muted-foreground text-center">
                  {t("detail.performanceScore")}
                </p>
              </>
            )}
          </CardContent>
        </Card>
        <StatCard
          icon={GraduationCap}
          iconClassName="text-primary"
          iconBgClassName="bg-primary/10"
          value={student.average_grade?.toFixed(1) ?? "-"}
          label={tc("general.averageGrade")}
        />
        <StatCard
          icon={Calendar}
          iconClassName="text-green-600"
          iconBgClassName="bg-green-100"
          value={`${attendanceRate.toFixed(0)}%`}
          label={tc("general.attendance")}
        />
        <StatCard
          icon={BookOpen}
          iconClassName="text-blue-600"
          iconBgClassName="bg-blue-100"
          value={grades?.length || 0}
          label={t("detail.gradesCount")}
        />
        <StatCard
          icon={AlertTriangle}
          iconClassName="text-orange-600"
          iconBgClassName="bg-orange-100"
          value={student.total_absences || 0}
          label={tc("general.absences")}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <SubjectBarChart data={subjectData} />

        {/* Line Chart - Grade Trend */}
        <Card>
          <div className="p-6 border-b">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <TrendingDown className="size-4 text-muted-foreground" />
              {t("detail.gradeTrend")}
            </h3>
          </div>
          <CardContent className="p-4">
            {gradeTrend.length > 0 ? (
              <ChartContainer config={{ grade: { label: tc("table.grade"), color: "#6366f1" } } satisfies ChartConfig} className="h-[35vh] w-full">
                <LineChart
                  data={gradeTrend}
                  margin={{ top: 20, right: 30, bottom: 20, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="index" />
                  <YAxis domain={gradeRange} />
                  <ChartTooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="bg-background border rounded-lg p-3 shadow-md text-sm border-border max-w-[250px]">
                            <p className="font-bold mb-2 pb-1 border-b">
                              {t("detail.examTooltip", { label: data.index })}
                            </p>
                            <div className="flex flex-col gap-1">
                              <div className="flex justify-between gap-4">
                                <span className="text-muted-foreground">
                                  {tc("table.subject")}:
                                </span>
                                <span className="font-medium">
                                  {data.subject}
                                </span>
                              </div>
                              <div className="flex justify-between gap-4">
                                <span className="text-muted-foreground">
                                  {tc("table.teacher")}:
                                </span>
                                <span className="font-medium">
                                  {data.teacher}
                                </span>
                              </div>
                              <div className="flex justify-between gap-4 mt-1 pt-1 border-t">
                                <span className="text-muted-foreground">
                                  {tc("table.grade")}:
                                </span>
                                <span className="font-bold text-primary">
                                  {data.grade}
                                </span>
                              </div>
                            </div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="grade"
                    stroke="var(--color-grade)"
                    strokeWidth={2.5}
                    dot={{ fill: "#6366f1", r: 4 }}
                    activeDot={{ r: 6 }}
                    connectNulls
                  />
                </LineChart>
              </ChartContainer>
            ) : (
              <div className="h-[35vh] flex items-center justify-center text-muted-foreground">
                {t("detail.noTrendData")}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Multi-Year Timeline */}
      {timelineData && timelineData.timeline.length > 0 && (
        <StudentTimelineSection
          points={timelineData.timeline}
          onYearClick={(year) => setFilter("year", year)}
        />
      )}

      {timelineData && timelineData.timeline.length > 0 && (
        <SubjectGradeTimelineSection points={timelineData.timeline} />
      )}

      {/* Period Comparison */}
      <PeriodComparisonSection
        allGrades={allGrades}
        allAttendance={allAttendance}
      />

      {/* Attendance Gauge */}
      <Card>
        <div className="p-6 border-b">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Clock className="size-4 text-muted-foreground" />
            {tc("general.attendanceRate")}
          </h3>
        </div>
        <CardContent className="p-6">
          <div className="flex items-center gap-6">
            <div className="flex-1">
              <Progress value={attendanceRate} className="h-4" />
            </div>
            <div className="text-2xl font-bold tabular-nums min-w-[80px] text-left">
              {attendanceRate.toFixed(1)}%
            </div>
          </div>
          <div className="flex justify-between mt-4 text-sm text-muted-foreground">
            <span>{t("detail.totalLessons", { count: totalLessons })}</span>
            <span>{t("detail.presentCount", { count: totalAttendance })}</span>
            <span>
              {t("detail.absentCount", {
                count: totalLessons - totalAttendance,
              })}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Grades Table */}
      <Card>
        <div className="p-6 border-b">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <BookOpen className="size-4 text-muted-foreground" />
            {t("detail.gradeHistory")}
          </h3>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="bg-accent/50">
              <TableHead className="text-right font-bold w-12">#</TableHead>
              <SortableTableHead
                column="subject"
                sort={gradeSort}
                onSort={toggleGradeSort}
              >
                {tc("table.subject")}
              </SortableTableHead>
              <SortableTableHead
                column="teacher_name"
                sort={gradeSort}
                onSort={toggleGradeSort}
              >
                {tc("table.teacher")}
              </SortableTableHead>
              <SortableTableHead
                column="grade"
                sort={gradeSort}
                onSort={toggleGradeSort}
              >
                {tc("table.grade")}
              </SortableTableHead>
              <SortableTableHead
                column="period"
                sort={gradeSort}
                onSort={toggleGradeSort}
              >
                {tc("table.period")}
              </SortableTableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pagedGrades.length ? (
              pagedGrades.map((grade, i) => (
                <TableRow key={i}>
                  <TableCell className="text-muted-foreground">
                    {(gradePage - 1) * pageSize + i + 1}
                  </TableCell>
                  <TableCell className="font-medium">{grade.subject}</TableCell>
                  <TableCell>{grade.teacher_name || "-"}</TableCell>
                  <TableCell
                    className={`font-bold ${grade.grade < atRiskGradeThreshold ? "text-red-600" : grade.grade >= goodGradeThreshold ? "text-green-600" : ""}`}
                  >
                    {grade.grade}
                  </TableCell>
                  <TableCell>
                    {formatPeriodWithYear(grade.period, grade.year)}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="text-center text-muted-foreground py-12"
                >
                  {t("detail.noGrades")}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <TablePagination
          page={gradePage}
          totalPages={gradeTotalPages}
          onPageChange={setGradePage}
        />
      </Card>

      {/* Attendance Table */}
      <Card>
        <div className="p-6 border-b">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Calendar className="size-4 text-muted-foreground" />
            {t("detail.attendanceHistory")}
          </h3>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="bg-accent/50">
              <TableHead className="text-right font-bold w-12">#</TableHead>
              <SortableTableHead
                column="period"
                sort={attSort}
                onSort={toggleAttSort}
              >
                {tc("table.period")}
              </SortableTableHead>
              <SortableTableHead
                column="total_absences"
                sort={attSort}
                onSort={toggleAttSort}
              >
                {tc("table.absences")}
              </SortableTableHead>
              <SortableTableHead
                column="attendance"
                sort={attSort}
                onSort={toggleAttSort}
              >
                {tc("general.attendance")}
              </SortableTableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pagedAttendance.length ? (
              pagedAttendance.map((record, i) => (
                <TableRow key={record.id}>
                  <TableCell className="text-muted-foreground">
                    {(attendancePage - 1) * pageSize + i + 1}
                  </TableCell>
                  <TableCell>
                    {formatPeriodWithYear(record.period, record.year)}
                  </TableCell>
                  <TableCell>{record.total_absences}</TableCell>
                  <TableCell>
                    {record.lessons_reported > 0
                      ? `${record.attendance}/${record.lessons_reported}`
                      : "-"}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={4}
                  className="text-center text-muted-foreground py-12"
                >
                  {t("detail.noAttendance")}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <TablePagination
          page={attendancePage}
          totalPages={attendanceTotalPages}
          onPageChange={setAttendancePage}
        />
      </Card>
    </div>
  );
}

function PeriodComparisonSection({
  allGrades,
  allAttendance,
}: {
  allGrades?: GradeResponse[];
  allAttendance?: AttendanceResponse[];
}) {
  const { t } = useTranslation("students");
  const { t: tc } = useTranslation();

  // Derive available years, periods, subjects from all data
  const { years, periods, allSubjects } = useMemo(() => {
    const yearsSet = new Set<string>();
    const periodsSet = new Set<string>();
    const subjectsSet = new Set<string>();
    for (const g of allGrades ?? []) {
      if (g.year) yearsSet.add(g.year);
      if (g.period) periodsSet.add(g.period);
      if (g.subject) subjectsSet.add(g.subject);
    }
    for (const a of allAttendance ?? []) {
      if (a.year) yearsSet.add(a.year);
      if (a.period) periodsSet.add(a.period);
    }
    return {
      years: Array.from(yearsSet).sort(),
      periods: Array.from(periodsSet).sort(),
      allSubjects: Array.from(subjectsSet).sort(),
    };
  }, [allGrades, allAttendance]);

  const [period1, setPeriod1] = useState("");
  const [year1, setYear1] = useState("");
  const [period2, setPeriod2] = useState("");
  const [year2, setYear2] = useState("");

  // Initialise selects once data arrives (state-during-render pattern)
  const [periodsInitialized, setPeriodsInitialized] = useState(false);
  if (
    !periodsInitialized &&
    periods.length > 0 &&
    years.length > 0 &&
    period1 === "" &&
    year1 === ""
  ) {
    setPeriodsInitialized(true);
    setPeriod1(periods[0]);
    setPeriod2(periods[1] ?? periods[0]);
    setYear1(years[0]);
    setYear2(years[0]);
  }

  // Subject filter - empty set means "all subjects"
  const [selectedSubjects, setSelectedSubjects] = useState<Set<string>>(
    new Set(),
  );

  const toggleSubject = (subject: string) => {
    setSelectedSubjects((prev) => {
      const next = new Set(prev);
      if (next.has(subject)) next.delete(subject);
      else next.add(subject);
      return next;
    });
  };

  if (!periods.length) return null;

  function computePeriodStats(period: string, year: string) {
    const activeSubjects = selectedSubjects.size > 0 ? selectedSubjects : null;

    const periodGrades = (allGrades ?? []).filter(
      (g) =>
        g.period === period &&
        g.year === year &&
        (activeSubjects === null || activeSubjects.has(g.subject)),
    );
    const periodAttendance = (allAttendance ?? []).filter(
      (a) => a.period === period && a.year === year,
    );

    const avgGrade =
      periodGrades.length > 0
        ? periodGrades.reduce((s, g) => s + g.grade, 0) / periodGrades.length
        : null;

    const totalLessons = periodAttendance.reduce(
      (s, a) => s + a.lessons_reported,
      0,
    );
    const totalPresent = periodAttendance.reduce((s, a) => s + a.attendance, 0);
    const attRate =
      totalLessons > 0 ? (totalPresent / totalLessons) * 100 : null;
    const totalAbsences = periodAttendance.reduce(
      (s, a) => s + a.total_absences,
      0,
    );

    const bySubject = new Map<string, { sum: number; count: number }>();
    for (const g of periodGrades) {
      const entry = bySubject.get(g.subject);
      if (entry) {
        entry.sum += g.grade;
        entry.count += 1;
      } else bySubject.set(g.subject, { sum: g.grade, count: 1 });
    }
    const subjectAvgs = Array.from(bySubject, ([subject, { sum, count }]) => ({
      subject,
      avg: Math.round(sum / count),
    }));

    return { avgGrade, attRate, totalAbsences, subjectAvgs };
  }

  const slot1Ready = !!period1 && !!year1;
  const slot2Ready = !!period2 && !!year2;
  const slot1Label = slot1Ready ? `${period1} - ${year1}` : "";
  const slot2Label = slot2Ready ? `${period2} - ${year2}` : "";

  const period1Stats = slot1Ready ? computePeriodStats(period1, year1) : null;
  const period2Stats = slot2Ready ? computePeriodStats(period2, year2) : null;

  return (
    <Card>
      <div className="p-6 border-b">
        <h3 className="text-lg font-bold flex items-center gap-2">
          <ArrowLeftRight className="size-4 text-muted-foreground" />
          {t("detail.periodComparison")}
        </h3>
      </div>
      <CardContent className="p-6 space-y-6">
        {/* Slot selectors */}
        <div className="grid grid-cols-2 gap-6">
          {/* Slot 1 */}
          <div className="space-y-2">
            <p className="text-sm font-medium">{t("detail.period1")}</p>
            <div className="grid grid-cols-2 gap-2">
              <Select value={period1} onValueChange={setPeriod1}>
                <SelectTrigger>
                  <SelectValue placeholder={t("detail.selectPeriod")} />
                </SelectTrigger>
                <SelectContent>
                  {periods.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={year1} onValueChange={setYear1}>
                <SelectTrigger>
                  <SelectValue placeholder={t("detail.selectYear")} />
                </SelectTrigger>
                <SelectContent>
                  {years.map((y) => (
                    <SelectItem key={y} value={y}>
                      {y}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Slot 2 */}
          <div className="space-y-2">
            <p className="text-sm font-medium">{t("detail.period2")}</p>
            <div className="grid grid-cols-2 gap-2">
              <Select value={period2} onValueChange={setPeriod2}>
                <SelectTrigger>
                  <SelectValue placeholder={t("detail.selectPeriod")} />
                </SelectTrigger>
                <SelectContent>
                  {periods.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={year2} onValueChange={setYear2}>
                <SelectTrigger>
                  <SelectValue placeholder={t("detail.selectYear")} />
                </SelectTrigger>
                <SelectContent>
                  {years.map((y) => (
                    <SelectItem key={y} value={y}>
                      {y}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {/* Subject filter chips */}
        {allSubjects.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium">{t("detail.filterBySubject")}</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setSelectedSubjects(new Set())}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  selectedSubjects.size === 0
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-background text-muted-foreground border-border hover:border-primary/50"
                }`}
              >
                {tc("general.all")}
              </button>
              {allSubjects.map((subject) => (
                <button
                  key={subject}
                  type="button"
                  onClick={() => toggleSubject(subject)}
                  className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                    selectedSubjects.has(subject)
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-background text-muted-foreground border-border hover:border-primary/50"
                  }`}
                >
                  {subject}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Comparison columns */}
        {slot1Ready && slot2Ready && period1Stats && period2Stats ? (
          <div className="grid grid-cols-[1fr_auto_1fr] gap-6">
            <Card>
              <div className="p-4 border-b">
                <h4 className="font-bold text-center">{slot1Label}</h4>
              </div>
              <CardContent className="p-4">
                <PeriodCard stats={period1Stats} otherStats={period2Stats} />
              </CardContent>
            </Card>
            <div className="w-px bg-border self-stretch" />
            <Card>
              <div className="p-4 border-b">
                <h4 className="font-bold text-center">{slot2Label}</h4>
              </div>
              <CardContent className="p-4">
                <PeriodCard stats={period2Stats} otherStats={period1Stats} />
              </CardContent>
            </Card>
          </div>
        ) : (
          <div className="text-center text-muted-foreground py-8">
            {t("detail.selectTwoPeriods")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

type PeriodStats = {
  avgGrade: number | null;
  attRate: number | null;
  totalAbsences: number;
  subjectAvgs: { subject: string; avg: number }[];
};

function PeriodCard({
  stats,
  otherStats,
}: {
  stats: PeriodStats;
  otherStats: PeriodStats;
}) {
  const { t } = useTranslation("students");
  const { t: tc } = useTranslation();
  const atRiskGradeThreshold = useConfigStore((s) => s.atRiskGradeThreshold);
  const goodGradeThreshold = useConfigStore((s) => s.goodGradeThreshold);

  if (stats.avgGrade === null && stats.attRate === null) {
    return (
      <div className="flex items-center justify-center h-40 text-muted-foreground">
        {t("detail.noPeriodData")}
      </div>
    );
  }

  const getColorScore = (
    val: number | null,
    other: number | null,
    lowerIsBetter = false,
  ) => {
    if (val === null || other === null) return "";
    if (val === other) return "";
    if (val > other) return lowerIsBetter ? "text-red-500" : "text-green-500";
    return lowerIsBetter ? "text-green-500" : "text-red-500";
  };

  return (
    <div className="space-y-4">
      {/* Mini stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="text-center p-2 bg-accent/30 rounded-lg">
          <p
            className={`text-lg font-bold tabular-nums ${getColorScore(stats.avgGrade, otherStats.avgGrade)}`}
          >
            {stats.avgGrade !== null ? stats.avgGrade.toFixed(1) : "-"}
          </p>
          <p className="text-xs text-muted-foreground">
            {tc("general.averageGrade")}
          </p>
        </div>
        <div className="text-center p-2 bg-accent/30 rounded-lg">
          <p
            className={`text-lg font-bold tabular-nums ${getColorScore(stats.attRate, otherStats.attRate)}`}
          >
            {stats.attRate !== null ? `${stats.attRate.toFixed(0)}%` : "-"}
          </p>
          <p className="text-xs text-muted-foreground">
            {tc("general.attendanceRate")}
          </p>
        </div>
        <div className="text-center p-2 bg-accent/30 rounded-lg">
          <p
            className={`text-lg font-bold tabular-nums ${getColorScore(stats.totalAbsences, otherStats.totalAbsences, true)}`}
          >
            {stats.totalAbsences}
          </p>
          <p className="text-xs text-muted-foreground">
            {tc("general.absences")}
          </p>
        </div>
      </div>

      {/* Subject grades table */}
      {stats.subjectAvgs.length > 0 && (
        <div>
          <p className="text-sm font-medium mb-2">
            {t("detail.gradesBySubject")}
          </p>
          <Table>
            <TableBody>
              {stats.subjectAvgs.map((s) => {
                const otherSubject = otherStats.subjectAvgs.find(
                  (os) => os.subject === s.subject,
                );
                const colorClass = getColorScore(
                  s.avg,
                  otherSubject ? otherSubject.avg : null,
                );
                return (
                  <TableRow key={s.subject}>
                    <TableCell className="py-1.5 text-sm">
                      {s.subject}
                    </TableCell>
                    <TableCell
                      className={`py-1.5 text-sm font-bold text-left ${colorClass || (s.avg < atRiskGradeThreshold ? "text-red-600" : s.avg >= goodGradeThreshold ? "text-green-600" : "")}`}
                    >
                      {s.avg}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function SubjectBarChart({
  data,
}: {
  data: { subject: string; average: number; teachers: string }[];
}) {
  const { t } = useTranslation("students");
  const { t: tc } = useTranslation();
  const gradeRange = useConfigStore((s) => s.gradeRange);

  return (
    <Card>
      <div className="p-6 border-b">
        <h3 className="text-lg font-bold flex items-center gap-2">
          <TrendingUp className="size-4 text-muted-foreground" />
          {t("detail.performanceBySubject")}
        </h3>
      </div>
      <CardContent className="p-4">
        {data.length > 0 ? (
          <ChartContainer config={{ average: { label: tc("general.averageGrade") } } satisfies ChartConfig} className="h-[40vh] w-full">
            <BarChart
              data={data}
              margin={{ top: 20, right: 30, bottom: 20, left: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="subject" tick={{ fontSize: 12 }} />
              <YAxis domain={gradeRange} />
              <ChartTooltip
                cursor={{ fill: "var(--accent)" }}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-background border rounded-lg p-3 shadow-md text-sm border-border min-w-[200px]">
                        <p className="font-bold mb-2 pb-1 border-b">
                          {data.subject}
                        </p>
                        <div className="flex flex-col gap-1">
                          <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">
                              {tc("table.teacher")}:
                            </span>
                            <span className="font-medium text-right">
                              {data.teachers}
                            </span>
                          </div>
                          <div className="flex justify-between gap-4 mt-1 pt-1 border-t">
                            <span className="text-muted-foreground">
                              {tc("general.averageGrade")}:
                            </span>
                            <span className="font-bold text-primary">
                              {data.average}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar
                dataKey="average"
                shape={(props: {
                  x: number;
                  y: number;
                  width: number;
                  height: number;
                  index: number;
                }) => {
                  const { x, y, width, height, index } = props;
                  return (
                    <rect
                      x={x}
                      y={y}
                      width={width}
                      height={height}
                      fill={getBarColor(index)}
                      rx={4}
                      ry={4}
                    />
                  );
                }}
              />
            </BarChart>
          </ChartContainer>
        ) : (
          <div className="h-[40vh] flex items-center justify-center text-muted-foreground">
            {t("detail.noGradeData")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StudentTimelineSection({
  points,
  onYearClick,
}: {
  points: StudentTimelinePoint[];
  onYearClick?: (year: string) => void;
}) {
  const { t } = useTranslation("students");
  const { t: tc } = useTranslation();
  const gradeRange = useConfigStore((s) => s.gradeRange);

  return (
    <Card>
      <div className="p-6 border-b">
        <h3 className="text-lg font-bold flex items-center gap-2">
          <History className="size-4 text-muted-foreground" />
          {t("detail.multiYearTimeline", "Multi-Year Timeline")}
        </h3>
      </div>
      <CardContent className="p-4">
        <ChartContainer config={{ average_grade: { label: tc("general.averageGrade"), color: "#6366f1" }, attendance_rate: { label: tc("general.attendanceRate"), color: "#10b981" } } satisfies ChartConfig} className="h-[35vh] w-full">
          <LineChart
            data={points}
            margin={{ top: 20, right: 30, bottom: 20, left: 0 }}
            onClick={(e: Record<string, unknown> | null) => {
              const activePayload = (
                e as {
                  activePayload?: { payload: StudentTimelinePoint }[];
                } | null
              )?.activePayload;
              if (activePayload && activePayload.length > 0 && onYearClick) {
                const data = activePayload[0].payload;
                if (data.year) {
                  onYearClick(data.year);
                }
              }
            }}
            className={onYearClick ? "cursor-pointer" : ""}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 12 }} />
            <YAxis yAxisId="left" domain={gradeRange} />
            <YAxis yAxisId="right" orientation="right" domain={[0, 100]} />
            <ChartLegend
              verticalAlign="top"
              wrapperStyle={{ paddingBottom: 8, fontSize: 13 }}
              content={(props) => <ChartLegendContent {...props} />}
            />
            <ChartTooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload as StudentTimelinePoint;
                  return (
                    <div className="bg-background border rounded-lg p-3 shadow-md text-sm border-border min-w-[200px]">
                      <p className="font-bold mb-2 pb-1 border-b">
                        {data.label}
                      </p>
                      <div className="flex flex-col gap-1">
                        <div className="flex justify-between gap-4">
                          <span className="text-muted-foreground">
                            {tc("general.averageGrade")}:
                          </span>
                          <span className="font-bold text-primary">
                            {data.average_grade?.toFixed(1) ?? "-"}
                          </span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span className="text-muted-foreground">
                            {tc("general.attendanceRate")}:
                          </span>
                          <span className="font-bold text-green-600">
                            {data.attendance_rate
                              ? `${data.attendance_rate.toFixed(1)}%`
                              : "-"}
                          </span>
                        </div>
                        <div className="flex justify-between gap-4">
                          <span className="text-muted-foreground">
                            {tc("general.absences")}:
                          </span>
                          <span className="font-medium">
                            {data.total_absences}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="average_grade"
              name={tc("general.averageGrade")}
              stroke="var(--color-average_grade)"
              strokeWidth={2.5}
              dot={{ fill: "#6366f1", r: 4 }}
              activeDot={{ r: 6 }}
              connectNulls
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="attendance_rate"
              name={tc("general.attendanceRate")}
              stroke="var(--color-attendance_rate)"
              strokeWidth={2.5}
              dot={{ fill: "#10b981", r: 4 }}
              activeDot={{ r: 6 }}
              connectNulls
            />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}

function SubjectGradeTimelineSection({
  points,
}: {
  points: StudentTimelinePoint[];
}) {
  const { t } = useTranslation("students");
  const { t: tc } = useTranslation();
  const gradeRange = useConfigStore((s) => s.gradeRange);

  const subjects = useMemo(() => {
    const subjectSet = new Set<string>();
    for (const point of points) {
      for (const subjectEntry of point.subjects) {
        subjectSet.add(subjectEntry.subject);
      }
    }
    return Array.from(subjectSet).sort();
  }, [points]);

  const [selectedSubjects, setSelectedSubjects] = useState<string[]>([]);

  // Keep selection valid when data changes without useEffect.
  const normalizedSelectedSubjects = useMemo(() => {
    const validSelectedSubjects =
      subjects.length === 0
        ? []
        : selectedSubjects.filter((subject) => subjects.includes(subject));

    return validSelectedSubjects.length > 0
      ? validSelectedSubjects
      : [subjects[0]];
  }, [subjects, selectedSubjects]);
  const needsSelectionSync =
    normalizedSelectedSubjects.length !== selectedSubjects.length ||
    normalizedSelectedSubjects.some(
      (subject, index) => subject !== selectedSubjects[index],
    );
  if (needsSelectionSync) {
    setSelectedSubjects(normalizedSelectedSubjects);
  }

  const toggleSubject = (subject: string) => {
    setSelectedSubjects((prev) => {
      if (prev.includes(subject)) {
        return prev.filter((value) => value !== subject);
      }
      return [...prev, subject];
    });
  };

  const subjectTimeline = useMemo(() => {
    if (normalizedSelectedSubjects.length === 0) {
      return [] as Array<Record<string, string | number | null>>;
    }

    return points.map((point) => {
      const row: Record<string, string | number | null> = {
        label: point.label,
        year: point.year,
        period: point.period,
      };

      for (const subject of normalizedSelectedSubjects) {
        const subjectPoint = point.subjects.find(
          (entry) => entry.subject === subject,
        );
        row[subject] = subjectPoint?.grade ?? null;
      }

      return {
        ...row,
      };
    });
  }, [points, normalizedSelectedSubjects]);

  if (subjects.length === 0) return null;

  return (
    <Card>
      <div className="p-6 border-b">
        <div className="space-y-3">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <History className="size-4 text-muted-foreground" />
            {t("detail.subjectGradeTimeline", "Subject Grade Timeline")}
          </h3>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setSelectedSubjects(subjects)}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                normalizedSelectedSubjects.length === subjects.length
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-background text-muted-foreground border-border hover:border-primary/50"
              }`}
            >
              {tc("general.all")}
            </button>
            {subjects.map((subject) => (
              <button
                key={subject}
                type="button"
                onClick={() => toggleSubject(subject)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  normalizedSelectedSubjects.includes(subject)
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-background text-muted-foreground border-border hover:border-primary/50"
                }`}
              >
                {subject}
              </button>
            ))}
          </div>
        </div>
      </div>
      <CardContent className="p-4">
        <ChartContainer config={Object.fromEntries(normalizedSelectedSubjects.map((subject, i) => [subject, { label: subject, color: BAR_COLORS[i % BAR_COLORS.length] }])) satisfies ChartConfig} className="h-[35vh] w-full">
          <LineChart
            data={subjectTimeline}
            margin={{ top: 20, right: 30, bottom: 20, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 12 }} />
            <YAxis domain={gradeRange} />
            <ChartLegend
              verticalAlign="top"
              wrapperStyle={{ paddingBottom: 8, fontSize: 13 }}
              content={(props) => <ChartLegendContent {...props} />}
            />
            <ChartTooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload as {
                    label: string;
                    year: string;
                    period: string;
                  };
                  return (
                    <div className="bg-background border rounded-lg p-3 shadow-md text-sm border-border min-w-[180px]">
                      <p className="font-bold mb-2 pb-1 border-b">
                        {data.label}
                      </p>
                      <div className="flex flex-col gap-1">
                        <div className="flex justify-between gap-4">
                          <span className="text-muted-foreground">
                            {tc("table.period")}:
                          </span>
                          <span className="font-medium">{`${data.period} - ${data.year}`}</span>
                        </div>
                        {payload.map((entry) => (
                          <div
                            key={entry.dataKey as string}
                            className="flex justify-between gap-4 mt-1 pt-1 border-t"
                          >
                            <span
                              className="text-muted-foreground"
                              style={{ color: entry.color }}
                            >
                              {entry.name || entry.dataKey}:
                            </span>
                            <span className="font-bold">
                              {entry.value ?? "-"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            {normalizedSelectedSubjects.map((subject, index) => {
              const color = BAR_COLORS[index % BAR_COLORS.length];
              return (
                <Line
                  key={subject}
                  type="monotone"
                  dataKey={subject}
                  name={subject}
                  stroke={color}
                  strokeWidth={2.5}
                  dot={{ fill: color, r: 4 }}
                  activeDot={{ r: 6 }}
                  connectNulls
                />
              );
            })}
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
