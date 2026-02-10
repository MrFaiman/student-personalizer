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
import {
  Star,
  CalendarCheck,
  AlertTriangle,
  Eye,
  type LucideIcon,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const CLASS_COLORS = [
  "#6366f1", // indigo
  "#f59e0b", // amber
  "#10b981", // emerald
  "#ef4444", // red
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#84cc16", // lime
  "#f97316", // orange
  "#14b8a6", // teal
];
import { useFilters } from "@/components/FilterContext";
import { type StudentListItem } from "@/lib/types";
import { analyticsApi, studentsApi } from "@/lib/api";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  return (
    <>
      <KPISection />
      <ChartsSection />
      <StudentsTable />
    </>
  );
}

function KPISection() {
  const { filters } = useFilters();

  const { data: kpis, isLoading } = useQuery({
    queryKey: ["kpis", filters.period, filters.gradeLevel],
    queryFn: () =>
      analyticsApi.getKPIs({
        period: filters.period,
        grade_level: filters.gradeLevel,
      }),
  });

  const kpiCards: {
    title: string;
    value: string;
    isLoading: boolean;
    icon: LucideIcon;
    iconColor: string;
    showTrend?: boolean;
  }[] = [
      {
        title: "ממוצע ציונים שכבתי",
        value: kpis?.layer_average?.toFixed(1) || "—",
        isLoading,
        icon: Star,
        iconColor: "text-primary bg-primary/10",
      },
      {
        title: "ממוצע חיסורים לתלמיד",
        value: kpis?.avg_absences?.toFixed(1) || "—",
        isLoading,
        icon: CalendarCheck,
        iconColor: "text-orange-500 bg-orange-500/10",
      },
      {
        title: "תלמידים בסיכון (מתחת ל-55)",
        value: kpis?.at_risk_students?.toString() || "0",
        isLoading,
        icon: AlertTriangle,
        iconColor: "text-red-600 bg-red-600/10",
      },
    ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {kpiCards.map((kpi) => (
        <Card key={kpi.title} className="shadow-sm">
          <CardContent className="p-6">
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-start">
                <p className="text-muted-foreground text-sm font-semibold">{kpi.title}</p>
                <div className={`${kpi.iconColor} rounded-lg p-1`}>
                  <kpi.icon className="size-5" />
                </div>
              </div>
              {kpi.isLoading ? (
                <Skeleton className="h-9 w-20" />
              ) : (
                <p className="text-3xl font-bold leading-tight">{kpi.value}</p>
              )}
              <div className="flex items-center gap-1 mt-1 text-muted-foreground text-xs">
                {kpis?.total_students && `${kpis.total_students} תלמידים בסה"כ`}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ChartsSection() {
  const { filters } = useFilters();

  const { data: classComparison, isLoading } = useQuery({
    queryKey: ["class-comparison", filters.period, filters.gradeLevel],
    queryFn: () =>
      analyticsApi.getClassComparison({
        period: filters.period,
        grade_level: filters.gradeLevel,
      }),
  });

  const chartData = classComparison?.map((c) => ({
    name: c.class_name,
    average: c.average_grade,
    students: c.student_count,
  })) || [];

  const avgGrade = classComparison?.length
    ? (classComparison.reduce((sum, c) => sum + c.average_grade, 0) / classComparison.length).toFixed(1)
    : "—";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card className="shadow-sm">
        <CardContent className="p-8">
          <div className="flex flex-col gap-6">
            <div>
              <h3 className="text-lg font-bold">השוואת ממוצע ציונים לפי כיתות</h3>
              <p className="text-muted-foreground text-sm">
                {filters.period || "כל התקופות"} | {filters.gradeLevel ? `שכבה ${filters.gradeLevel}` : "כל השכבות"}
              </p>
            </div>
            <div className="flex items-baseline gap-2">
              {isLoading ? (
                <Skeleton className="h-10 w-24" />
              ) : (
                <>
                  <p className="text-4xl font-bold">{avgGrade}</p>
                  <p className="text-muted-foreground text-base">ממוצע כללי</p>
                </>
              )}
            </div>
            <div className="h-64">
              {isLoading ? (
                <Skeleton className="h-full w-full" />
              ) : chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} layout="horizontal">
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        direction: "rtl",
                        textAlign: "right",
                        background: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                      }}
                      formatter={(value) => [`${Number(value).toFixed(1)}`, "ממוצע"]}
                    />
                    <Bar dataKey="average" radius={[4, 4, 0, 0]}>
                      {chartData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={CLASS_COLORS[index % CLASS_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  אין נתונים להצגה
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardContent className="p-8">
          <div className="flex flex-col gap-6">
            <div>
              <h3 className="text-lg font-bold">תלמידים לפי כיתה</h3>
              <p className="text-muted-foreground text-sm">כמות תלמידים בכל כיתה</p>
            </div>
            <div className="flex items-baseline gap-2">
              {isLoading ? (
                <Skeleton className="h-10 w-24" />
              ) : (
                <>
                  <p className="text-4xl font-bold">
                    {chartData.reduce((sum, c) => sum + c.students, 0)}
                  </p>
                  <p className="text-muted-foreground text-base">תלמידים</p>
                </>
              )}
            </div>
            <div className="h-64">
              {isLoading ? (
                <Skeleton className="h-full w-full" />
              ) : chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} layout="horizontal">
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        direction: "rtl",
                        textAlign: "right",
                        background: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                      }}
                      formatter={(value) => [value, "תלמידים"]}
                    />
                    <Bar dataKey="students" radius={[4, 4, 0, 0]}>
                      {chartData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={CLASS_COLORS[index % CLASS_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  אין נתונים להצגה
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StudentsTable() {
  const { filters } = useFilters();

  const { data: students, isLoading } = useQuery({
    queryKey: ["at-risk-students", filters.period, filters.classId],
    queryFn: () =>
      studentsApi.list({
        at_risk_only: true,
        period: filters.period,
        class_id: filters.classId || undefined,
      }),
  });

  const getStatusBadge = (isAtRisk: boolean) => {
    if (isAtRisk) {
      return (
        <Badge className="bg-red-100 text-red-700 hover:bg-red-100">סיכון גבוה</Badge>
      );
    }
    return <Badge variant="secondary">תקין</Badge>;
  };

  return (
    <Card className="shadow-sm overflow-hidden">
      <div className="p-6 border-b border-border flex justify-between items-center">
        <h3 className="text-lg font-bold">תלמידים בטיפול דחוף</h3>
        <Link to="/students" search={{ at_risk: true }}>
          <Button variant="link" className="text-primary p-0 h-auto">
            צפה בכל התלמידים
          </Button>
        </Link>
      </div>
      <Table>
        <TableHeader>
          <TableRow className="bg-accent/50">
            <TableHead className="text-right font-bold w-12">#</TableHead>
            <TableHead className="text-right font-bold">שם התלמיד</TableHead>
            <TableHead className="text-right font-bold">כיתה</TableHead>
            <TableHead className="text-right font-bold">ממוצע ציונים</TableHead>
            <TableHead className="text-right font-bold">חיסורים</TableHead>
            <TableHead className="text-right font-bold">סטטוס</TableHead>
            <TableHead className="text-right font-bold">פעולות</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <TableRow key={i}>
                <TableCell><Skeleton className="h-5 w-8" /></TableCell>
                <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                <TableCell><Skeleton className="h-8 w-8" /></TableCell>
              </TableRow>
            ))
          ) : students?.items?.length ? (
            students.items.slice(0, 10).map((student: StudentListItem, index: number) => (
              <TableRow key={student.student_tz} className="hover:bg-accent/30 transition-colors">
                <TableCell className="text-muted-foreground">{index + 1}</TableCell>
                <TableCell className="font-semibold">{student.student_name}</TableCell>
                <TableCell>{student.class_name}</TableCell>
                <TableCell className={`font-bold ${student.average_grade && student.average_grade < 55 ? "text-red-600" : ""}`}>
                  {student.average_grade?.toFixed(1) || "—"}
                </TableCell>
                <TableCell>{student.total_absences}</TableCell>
                <TableCell>{getStatusBadge(student.is_at_risk)}</TableCell>
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
              <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                אין תלמידים בסיכון
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Card>
  );
}
