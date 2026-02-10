import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import {
  ArrowRight,
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

export const Route = createFileRoute("/students/$studentTz")({
  component: StudentDetailPage,
});

function StudentDetailPage() {
  const { t } = useTranslation("students");
  const { t: tc } = useTranslation();
  const { studentTz } = Route.useParams();

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

  // Prepare radar chart data from grades by subject
  const radarData =
    grades?.reduce((acc: { subject: string; grade: number }[], grade) => {
      const existing = acc.find((a) => a.subject === grade.subject);
      if (existing) {
        existing.grade = (existing.grade + grade.grade) / 2;
      } else {
        acc.push({ subject: grade.subject, grade: grade.grade });
      }
      return acc;
    }, []) || [];

  // Calculate attendance rate
  const totalSessions = attendance?.length || 0;
  const presentCount = attendance?.filter((a) => a.event_type === "נוכח" || a.event_type === "present").length || 0;
  const attendanceRate = totalSessions > 0 ? (presentCount / totalSessions) * 100 : 0;

  // Prepare grade trend data
  const gradeTrend =
    grades
      ?.sort((a, b) => new Date(a.date ?? "").getTime() - new Date(b.date ?? "").getTime())
      .slice(-10)
      .map((g, i) => ({
        index: i + 1,
        grade: g.grade,
        subject: g.subject,
      })) || [];

  const getStatusBadge = (isAtRisk?: boolean) => {
    if (isAtRisk) {
      return <Badge className="bg-red-100 text-red-700">{tc("status.atRisk")}</Badge>;
    }
    return <Badge className="bg-green-100 text-green-700">{tc("status.normal")}</Badge>;
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
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
    <div className="space-y-6">
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
        {getStatusBadge(student.is_at_risk)}
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
                      cx="18" cy="18" r="15.5"
                      fill="none"
                      stroke="hsl(var(--muted))"
                      strokeWidth="3"
                    />
                    <circle
                      cx="18" cy="18" r="15.5"
                      fill="none"
                      stroke={
                        student.performance_score >= 70
                          ? "#22c55e"
                          : student.performance_score >= 40
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
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="bg-primary/10 rounded-lg p-2">
              <GraduationCap className="size-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold tabular-nums">
                {student.average_grade?.toFixed(1) ?? "—"}
              </p>
              <p className="text-sm text-muted-foreground">{t("detail.averageGrade")}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="bg-green-100 rounded-lg p-2">
              <Calendar className="size-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold tabular-nums">{attendanceRate.toFixed(0)}%</p>
              <p className="text-sm text-muted-foreground">{t("detail.attendance")}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="bg-blue-100 rounded-lg p-2">
              <BookOpen className="size-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold tabular-nums">{grades?.length || 0}</p>
              <p className="text-sm text-muted-foreground">{t("detail.exams")}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="bg-orange-100 rounded-lg p-2">
              <AlertTriangle className="size-5 text-orange-600" />
            </div>
            <div>
              <p className="text-2xl font-bold tabular-nums">{student.total_absences || 0}</p>
              <p className="text-sm text-muted-foreground">{t("detail.absences")}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Radar Chart - Performance by Subject */}
        <Card>
          <div className="p-6 border-b">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <TrendingUp className="size-4 text-muted-foreground" />
              {t("detail.performanceBySubject")}
            </h3>
          </div>
          <CardContent className="p-4">
            {radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radarData} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12 }} />
                  <PolarRadiusAxis domain={[0, 100]} />
                  <Radar
                    name={t("detail.gradeTooltip")}
                    dataKey="grade"
                    stroke="hsl(var(--primary))"
                    fill="hsl(var(--primary))"
                    fillOpacity={0.3}
                  />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-muted-foreground">
                {t("detail.noGradeData")}
              </div>
            )}
          </CardContent>
        </Card>

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
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={gradeTrend} margin={{ top: 20, right: 30, bottom: 20, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="index" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      direction: "rtl",
                      textAlign: "right",
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                    formatter={(value) => [Number(value ?? 0).toFixed(0), t("detail.gradeTooltip")]}
                    labelFormatter={(label) => t("detail.examTooltip", { label })}
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
              <div className="h-[280px] flex items-center justify-center text-muted-foreground">
                {t("detail.noTrendData")}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Attendance Gauge */}
      <Card>
        <div className="p-6 border-b">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Clock className="size-4 text-muted-foreground" />
            {t("detail.attendanceRate")}
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
            <span>{t("detail.totalLessons", { count: totalSessions })}</span>
            <span>{t("detail.presentCount", { count: presentCount })}</span>
            <span>{t("detail.absentCount", { count: totalSessions - presentCount })}</span>
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
              <TableHead className="text-right font-bold">{tc("table.date")}</TableHead>
              <TableHead className="text-right font-bold">{tc("table.period")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {grades?.length ? (
              grades.slice(0, 20).map((grade, i) => (
                <TableRow key={i}>
                  <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                  <TableCell className="font-medium">{grade.subject}</TableCell>
                  <TableCell>{grade.teacher || "—"}</TableCell>
                  <TableCell
                    className={`font-bold ${grade.grade < 55
                      ? "text-red-600"
                      : grade.grade >= 80
                        ? "text-green-600"
                        : ""
                      }`}
                  >
                    {grade.grade}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {grade.date
                      ? new Date(grade.date).toLocaleDateString("he-IL")
                      : "—"}
                  </TableCell>
                  <TableCell>{grade.period || "—"}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-12">
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
              <TableHead className="text-right font-bold">{tc("table.date")}</TableHead>
              <TableHead className="text-right font-bold">{tc("table.hour")}</TableHead>
              <TableHead className="text-right font-bold">{tc("table.subject")}</TableHead>
              <TableHead className="text-right font-bold">{tc("table.status")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {attendance?.length ? (
              attendance.slice(0, 20).map((record, i) => (
                <TableRow key={i}>
                  <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                  <TableCell>
                    {record.date
                      ? new Date(record.date).toLocaleDateString("he-IL")
                      : "—"}
                  </TableCell>
                  <TableCell>{record.hours || "—"}</TableCell>
                  <TableCell>{record.event_type || "—"}</TableCell>
                  <TableCell>
                    {record.event_type === "נוכח" || record.event_type === "present" ? (
                      <Badge className="bg-green-100 text-green-700">{tc("status.present")}</Badge>
                    ) : (
                      <Badge className="bg-red-100 text-red-700">{tc("status.absent")}</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-12">
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
