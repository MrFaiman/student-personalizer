import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
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
      return <Badge className="bg-red-100 text-red-700">בסיכון</Badge>;
    }
    return <Badge className="bg-green-100 text-green-700">תקין</Badge>;
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
        <h2 className="text-xl font-bold mb-2">התלמיד לא נמצא</h2>
        <Link to="/students">
          <Button>חזור לרשימת התלמידים</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with back button */}
      <div className="flex items-center gap-4">
        <Link to="/students">
          <Button variant="ghost" size="icon">
            <ArrowRight className="size-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{student.student_name}</h1>
          <p className="text-muted-foreground">
            כיתה {student.class_name} | ת.ז: {student.student_tz}
          </p>
        </div>
        {getStatusBadge(student.is_at_risk)}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="bg-primary/10 rounded-lg p-2">
              <GraduationCap className="size-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {student.average_grade?.toFixed(1) ?? "—"}
              </p>
              <p className="text-sm text-muted-foreground">ממוצע ציונים</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="bg-green-100 rounded-lg p-2">
              <Calendar className="size-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{attendanceRate.toFixed(0)}%</p>
              <p className="text-sm text-muted-foreground">נוכחות</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="bg-blue-100 rounded-lg p-2">
              <BookOpen className="size-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{grades?.length || 0}</p>
              <p className="text-sm text-muted-foreground">מבחנים</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="bg-orange-100 rounded-lg p-2">
              <AlertTriangle className="size-5 text-orange-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{student.total_absences || 0}</p>
              <p className="text-sm text-muted-foreground">היעדרויות</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Radar Chart - Performance by Subject */}
        <Card>
          <div className="p-4 border-b">
            <h3 className="font-bold flex items-center gap-2">
              <TrendingUp className="size-4 text-muted-foreground" />
              ביצועים לפי מקצוע
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
                    name="ציון"
                    dataKey="grade"
                    stroke="hsl(var(--primary))"
                    fill="hsl(var(--primary))"
                    fillOpacity={0.3}
                  />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-muted-foreground">
                אין נתוני ציונים
              </div>
            )}
          </CardContent>
        </Card>

        {/* Line Chart - Grade Trend */}
        <Card>
          <div className="p-4 border-b">
            <h3 className="font-bold flex items-center gap-2">
              <TrendingDown className="size-4 text-muted-foreground" />
              מגמת ציונים
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
                    formatter={(value) => [Number(value ?? 0).toFixed(0), "ציון"]}
                    labelFormatter={(label) => `מבחן ${label}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="grade"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={{ fill: "hsl(var(--primary))" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-muted-foreground">
                אין נתוני מגמה
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Attendance Gauge */}
      <Card>
        <div className="p-4 border-b">
          <h3 className="font-bold flex items-center gap-2">
            <Clock className="size-4 text-muted-foreground" />
            אחוז נוכחות
          </h3>
        </div>
        <CardContent className="p-6">
          <div className="flex items-center gap-6">
            <div className="flex-1">
              <Progress value={attendanceRate} className="h-4" />
            </div>
            <div className="text-2xl font-bold min-w-[80px] text-left">
              {attendanceRate.toFixed(1)}%
            </div>
          </div>
          <div className="flex justify-between mt-4 text-sm text-muted-foreground">
            <span>סה״כ: {totalSessions} שיעורים</span>
            <span>נוכח: {presentCount}</span>
            <span>נעדר: {totalSessions - presentCount}</span>
          </div>
        </CardContent>
      </Card>

      {/* Grades Table */}
      <Card>
        <div className="p-4 border-b">
          <h3 className="font-bold flex items-center gap-2">
            <BookOpen className="size-4 text-muted-foreground" />
            היסטוריית ציונים
          </h3>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="bg-accent/50">
              <TableHead className="text-right font-bold w-12">#</TableHead>
              <TableHead className="text-right font-bold">מקצוע</TableHead>
              <TableHead className="text-right font-bold">מורה</TableHead>
              <TableHead className="text-right font-bold">ציון</TableHead>
              <TableHead className="text-right font-bold">תאריך</TableHead>
              <TableHead className="text-right font-bold">תקופה</TableHead>
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
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                  אין נתוני ציונים
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Attendance Table */}
      <Card>
        <div className="p-4 border-b">
          <h3 className="font-bold flex items-center gap-2">
            <Calendar className="size-4 text-muted-foreground" />
            היסטוריית נוכחות
          </h3>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="bg-accent/50">
              <TableHead className="text-right font-bold w-12">#</TableHead>
              <TableHead className="text-right font-bold">תאריך</TableHead>
              <TableHead className="text-right font-bold">שעה</TableHead>
              <TableHead className="text-right font-bold">מקצוע</TableHead>
              <TableHead className="text-right font-bold">סטטוס</TableHead>
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
                      <Badge className="bg-green-100 text-green-700">נוכח</Badge>
                    ) : (
                      <Badge className="bg-red-100 text-red-700">נעדר</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                  אין נתוני נוכחות
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
