import { useState } from "react";
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
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
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
} from "lucide-react";
import { studentsApi } from "@/lib/api";
import { StatCard } from "@/components/StatCard";
import { TOOLTIP_STYLE } from "@/lib/chart-styles";
import { getBarColor } from "@/lib/utils";
import {
  RECENT_GRADES_COUNT,
  GRADE_TABLE_PREVIEW_COUNT,
} from "@/lib/constants";
import { useConfigStore } from "@/lib/config-store";
import type { GradeResponse, AttendanceResponse } from "@/lib/types";

export const Route = createFileRoute("/students/$studentTz")(
  { component: StudentDetailPage },
);

function StudentDetailPage() {
  const { t } = useTranslation("students");
  const { t: tc } = useTranslation();
  const { studentTz } = Route.useParams();
  const atRiskGradeThreshold = useConfigStore((s) => s.atRiskGradeThreshold);
  const goodGradeThreshold = useConfigStore((s) => s.goodGradeThreshold);
  const performanceGoodThreshold = useConfigStore((s) => s.performanceGoodThreshold);
  const performanceMediumThreshold = useConfigStore((s) => s.performanceMediumThreshold);
  const gradeRange = useConfigStore((s) => s.gradeRange);

  const { data: student, isLoading } = useQuery({
    queryKey: ["student", studentTz],
    queryFn: () => studentsApi.get(studentTz),
  });

  const { data: grades } = useQuery({
    queryKey: ["student-grades", studentTz],
    queryFn: () => studentsApi.getGrades(studentTz),
  });

  const { data: attendance } = useQuery({
    queryKey: ["student-attendance", studentTz],
    queryFn: () => studentsApi.getAttendance(studentTz),
  });

  const { subjectData, periods } = (() => {
    if (!grades?.length) return { subjectData: [], periods: [] as string[] };
    
    const periodsSet = new Set<string>();
    const bySubject = new Map<string, { sum: number; count: number; teachers: Set<string> }>();
    
    for (const g of grades) {
      const p = g.period || "—";
      periodsSet.add(p);
      
      const entry = bySubject.get(g.subject);
      const teacherName = g.teacher_name || "—";
      if (entry) {
        entry.sum += g.grade;
        entry.count += 1;
        if (teacherName !== "—") entry.teachers.add(teacherName);
      } else {
        bySubject.set(g.subject, { 
          sum: g.grade, 
          count: 1, 
          teachers: new Set(teacherName !== "—" ? [teacherName] : []) 
        });
      }
    }
    
    const subjectData = Array.from(bySubject.entries()).map(([subject, { sum, count, teachers }]) => ({
      subject,
      average: Math.round(sum / count),
      teachers: teachers.size > 0 ? Array.from(teachers).join(", ") : "—",
    }));

    return { subjectData, periods: Array.from(periodsSet) };
  })();

  const totalLessons = attendance?.reduce((sum, a) => sum + a.lessons_reported, 0) || 0;
  const totalAttendance = attendance?.reduce((sum, a) => sum + a.attendance, 0) || 0;
  const attendanceRate = totalLessons > 0 ? (totalAttendance / totalLessons) * 100 : 0;

  const gradeTrend =
    grades
      ?.slice(-RECENT_GRADES_COUNT)
      .map((g, i) => ({
        index: i + 1,
        grade: g.grade,
        subject: g.subject,
        teacher: g.teacher_name || "—",
      })) || [];

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
          <Button variant="ghost" size="icon" aria-label={t("detail.backToListAria")}>
            <ArrowRight className="size-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{student.student_name}</h1>
          <p className="text-muted-foreground">
            {t("detail.classAndId", { className: student.class_name, tz: student.student_tz })}
          </p>
        </div>
        {student.is_at_risk ? (
          <Badge className="bg-red-100 text-red-700">{tc("status.atRisk")}</Badge>
        ) : (
          <Badge className="bg-green-100 text-green-700">{tc("status.normal")}</Badge>
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
                    <circle cx="18" cy="18" r="15.5" fill="none" stroke="hsl(var(--muted))" strokeWidth="3" />
                    <circle
                      cx="18" cy="18" r="15.5" fill="none"
                      stroke={
                        student.performance_score >= performanceGoodThreshold ? "#22c55e"
                          : student.performance_score >= performanceMediumThreshold ? "#f59e0b"
                            : "#ef4444"
                      }
                      strokeWidth="3" strokeLinecap="round"
                      strokeDasharray={`${student.performance_score * 0.9738} 97.38`}
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-lg font-bold tabular-nums">
                    {student.performance_score.toFixed(0)}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground text-center">{t("detail.performanceScore")}</p>
              </>
            ) : (
              <>
                <div className="relative size-20 flex items-center justify-center">
                  <span className="text-2xl font-bold text-muted-foreground">—</span>
                </div>
                <p className="text-sm text-muted-foreground text-center">{t("detail.performanceScore")}</p>
              </>
            )}
          </CardContent>
        </Card>
        <StatCard
          icon={GraduationCap}
          iconClassName="text-primary"
          iconBgClassName="bg-primary/10"
          value={student.average_grade?.toFixed(1) ?? "—"}
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
              <ResponsiveContainer width="100%" height="100%" className="min-h-[35vh]">
                <LineChart data={gradeTrend} margin={{ top: 20, right: 30, bottom: 20, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="index" />
                  <YAxis domain={gradeRange} />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="bg-background border rounded-lg p-3 shadow-md text-sm border-border max-w-[250px]">
                            <p className="font-bold mb-2 pb-1 border-b">{t("detail.examTooltip", { label: data.index })}</p>
                            <div className="flex flex-col gap-1">
                              <div className="flex justify-between gap-4">
                                <span className="text-muted-foreground">{tc("table.subject")}:</span>
                                <span className="font-medium">{data.subject}</span>
                              </div>
                              <div className="flex justify-between gap-4">
                                <span className="text-muted-foreground">{tc("table.teacher")}:</span>
                                <span className="font-medium">{data.teacher}</span>
                              </div>
                              <div className="flex justify-between gap-4 mt-1 pt-1 border-t">
                                <span className="text-muted-foreground">{tc("table.grade")}:</span>
                                <span className="font-bold text-primary">{data.grade}</span>
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
                    stroke="#6366f1"
                    strokeWidth={2.5}
                    dot={{ fill: "#6366f1", r: 4 }}
                    activeDot={{ r: 6 }}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[35vh] flex items-center justify-center text-muted-foreground">
                {t("detail.noTrendData")}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Period Comparison */}
      <PeriodComparisonSection grades={grades} attendance={attendance} periods={periods} />

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
            <span>{t("detail.absentCount", { count: totalLessons - totalAttendance })}</span>
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
              <TableHead className="text-right font-bold">{tc("table.subject")}</TableHead>
              <TableHead className="text-right font-bold">{tc("table.teacher")}</TableHead>
              <TableHead className="text-right font-bold">{tc("table.grade")}</TableHead>
              <TableHead className="text-right font-bold">{tc("table.period")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {grades?.length ? (
              grades.slice(0, GRADE_TABLE_PREVIEW_COUNT).map((grade, i) => (
                <TableRow key={i}>
                  <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                  <TableCell className="font-medium">{grade.subject}</TableCell>
                  <TableCell>{grade.teacher_name || "—"}</TableCell>
                  <TableCell
                    className={`font-bold ${grade.grade < atRiskGradeThreshold ? "text-red-600" : grade.grade >= goodGradeThreshold ? "text-green-600" : ""}`}
                  >
                    {grade.grade}
                  </TableCell>
                  <TableCell>{grade.period || "—"}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-12">
                  {t("detail.noGrades")}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
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
              <TableHead className="text-right font-bold">{tc("table.period")}</TableHead>
              <TableHead className="text-right font-bold">{tc("table.absences")}</TableHead>
              <TableHead className="text-right font-bold">{tc("general.attendance")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {attendance?.length ? (
              attendance.map((record, i) => (
                <TableRow key={record.id}>
                  <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                  <TableCell>{record.period}</TableCell>
                  <TableCell>{record.total_absences}</TableCell>
                  <TableCell>
                    {record.lessons_reported > 0
                      ? `${record.attendance}/${record.lessons_reported}`
                      : "—"}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground py-12">
                  {t("detail.noAttendance")}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

function PeriodComparisonSection({
  grades,
  attendance,
  periods,
}: {
  grades?: GradeResponse[];
  attendance?: AttendanceResponse[];
  periods: string[];
}) {
  const { t } = useTranslation("students");
  const [period1, setPeriod1] = useState<string>(periods[0] ?? "");
  const [period2, setPeriod2] = useState<string>(periods[1] ?? periods[0] ?? "");

  if (!periods.length) return null;

  function computePeriodStats(period: string) {
    const periodGrades = grades?.filter((g) => g.period === period) ?? [];
    const periodAttendance = attendance?.filter((a) => a.period === period) ?? [];

    const avgGrade =
      periodGrades.length > 0
        ? periodGrades.reduce((s, g) => s + g.grade, 0) / periodGrades.length
        : null;

    const totalLessons = periodAttendance.reduce((s, a) => s + a.lessons_reported, 0);
    const totalPresent = periodAttendance.reduce((s, a) => s + a.attendance, 0);
    const attRate = totalLessons > 0 ? (totalPresent / totalLessons) * 100 : null;
    const totalAbsences = periodAttendance.reduce((s, a) => s + a.total_absences, 0);

    const bySubject = new Map<string, { sum: number; count: number }>();
    for (const g of periodGrades) {
      const entry = bySubject.get(g.subject);
      if (entry) {
        entry.sum += g.grade;
        entry.count += 1;
      } else {
        bySubject.set(g.subject, { sum: g.grade, count: 1 });
      }
    }
    const subjectAvgs = Array.from(bySubject, ([subject, { sum, count }]) => ({
      subject,
      avg: Math.round(sum / count),
    }));

    return { avgGrade, attRate, totalAbsences, subjectAvgs };
  }

  const period1Stats = computePeriodStats(period1);
  const period2Stats = computePeriodStats(period2);

  return (
    <Card>
      <div className="p-6 border-b">
        <h3 className="text-lg font-bold flex items-center gap-2">
          <ArrowLeftRight className="size-4 text-muted-foreground" />
          {t("detail.periodComparison")}
        </h3>
      </div>
      <CardContent className="p-6">
        {/* Period selectors */}
        <div className="grid grid-cols-2 gap-6 mb-6">
          <div className="space-y-1">
            <label className="text-sm font-medium">{t("detail.period1")}</label>
            <Select value={period1} onValueChange={setPeriod1}>
              <SelectTrigger>
                <SelectValue placeholder={t("detail.selectPeriod")} />
              </SelectTrigger>
              <SelectContent>
                {periods.map((p) => (
                  <SelectItem key={p} value={p}>{p}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">{t("detail.period2")}</label>
            <Select value={period2} onValueChange={setPeriod2}>
              <SelectTrigger>
                <SelectValue placeholder={t("detail.selectPeriod")} />
              </SelectTrigger>
              <SelectContent>
                {periods.map((p) => (
                  <SelectItem key={p} value={p}>{p}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Comparison columns */}
        {period1 && period2 ? (
          <div className="grid grid-cols-[1fr_auto_1fr] gap-6">
            <Card>
              <div className="p-4 border-b">
                <h4 className="font-bold text-center">{period1}</h4>
              </div>
              <CardContent className="p-4"><PeriodCard stats={period1Stats} otherStats={period2Stats} /></CardContent>
            </Card>
            <div className="w-px bg-border self-stretch" />
            <Card>
              <div className="p-4 border-b">
                <h4 className="font-bold text-center">{period2}</h4>
              </div>
              <CardContent className="p-4"><PeriodCard stats={period2Stats} otherStats={period1Stats} /></CardContent>
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

  const getColorScore = (val: number | null, other: number | null, lowerIsBetter = false) => {
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
          <p className={`text-lg font-bold tabular-nums ${getColorScore(stats.avgGrade, otherStats.avgGrade)}`}>
            {stats.avgGrade !== null ? stats.avgGrade.toFixed(1) : "—"}
          </p>
          <p className="text-xs text-muted-foreground">{tc("general.averageGrade")}</p>
        </div>
        <div className="text-center p-2 bg-accent/30 rounded-lg">
          <p className={`text-lg font-bold tabular-nums ${getColorScore(stats.attRate, otherStats.attRate)}`}>
            {stats.attRate !== null ? `${stats.attRate.toFixed(0)}%` : "—"}
          </p>
          <p className="text-xs text-muted-foreground">{tc("general.attendanceRate")}</p>
        </div>
        <div className="text-center p-2 bg-accent/30 rounded-lg">
          <p className={`text-lg font-bold tabular-nums ${getColorScore(stats.totalAbsences, otherStats.totalAbsences, true)}`}>
            {stats.totalAbsences}
          </p>
          <p className="text-xs text-muted-foreground">{tc("general.absences")}</p>
        </div>
      </div>

      {/* Subject grades table */}
      {stats.subjectAvgs.length > 0 && (
        <div>
          <p className="text-sm font-medium mb-2">{t("detail.gradesBySubject")}</p>
          <Table>
            <TableBody>
              {stats.subjectAvgs.map((s) => {
                const otherSubject = otherStats.subjectAvgs.find(os => os.subject === s.subject);
                const colorClass = getColorScore(s.avg, otherSubject ? otherSubject.avg : null);
                return (
                  <TableRow key={s.subject}>
                    <TableCell className="py-1.5 text-sm">{s.subject}</TableCell>
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
          <ResponsiveContainer width="100%" height="100%" className="min-h-[40vh]">
            <BarChart data={data} margin={{ top: 20, right: 30, bottom: 20, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="subject" tick={{ fontSize: 12 }} />
              <YAxis domain={gradeRange} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                cursor={{ fill: "var(--accent)" }}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-background border rounded-lg p-3 shadow-md text-sm border-border min-w-[200px]">
                        <p className="font-bold mb-2 pb-1 border-b">{data.subject}</p>
                        <div className="flex flex-col gap-1">
                          <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">{tc("table.teacher")}:</span>
                            <span className="font-medium text-right">{data.teachers}</span>
                          </div>
                          <div className="flex justify-between gap-4 mt-1 pt-1 border-t">
                            <span className="text-muted-foreground">{tc("general.averageGrade")}:</span>
                            <span className="font-bold text-primary">{data.average}</span>
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
                shape={(props: { x: number; y: number; width: number; height: number; index: number }) => {
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
          </ResponsiveContainer>
        ) : (
          <div className="h-[40vh] flex items-center justify-center text-muted-foreground">
            {t("detail.noGradeData")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
