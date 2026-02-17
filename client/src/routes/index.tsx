import { Star, CalendarCheck, AlertTriangle, Eye } from "lucide-react";

import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { useFilters } from "@/components/FilterContext";
import { type StudentListItem } from "@/lib/types";
import { analyticsApi, studentsApi } from "@/lib/api";
import { AT_RISK_PREVIEW_COUNT } from "@/lib/constants";
import { useConfigStore } from "@/lib/config-store";
import {
  KPICard,
  DashboardBarChart,
  EmptyState,
  StatusBadge,
} from "@/components/dashboard";

export const Route = createFileRoute("/")({ component: HomePage });

function HomePage() {
  const { t } = useTranslation();
  const { filters } = useFilters();

  const { data: kpis, isLoading } = useQuery({
    queryKey: ["kpis", filters.period, filters.gradeLevel],
    queryFn: () =>
      analyticsApi.getKPIs({
        period: filters.period,
        grade_level: filters.gradeLevel,
      }),
  });

  if (!isLoading && kpis?.total_students === 0) {
    return <EmptyState />;
  }

  return (
    <>
      <Helmet>
        <title>{`${t("nav.dashboard")} | ${t("appName")}`}</title>
      </Helmet>
      <KPISection />
      <ChartsSection />
      <StudentsTable />
    </>
  );
}

function KPISection() {
  const { t } = useTranslation("dashboard");
  const { filters } = useFilters();

  const { data: kpis, isLoading } = useQuery({
    queryKey: ["kpis", filters.period, filters.gradeLevel],
    queryFn: () =>
      analyticsApi.getKPIs({
        period: filters.period,
        grade_level: filters.gradeLevel,
      }),
  });

  const kpiCards = [
    {
      title: t("kpi.layerAverage"),
      value: kpis?.layer_average?.toFixed(1) || "—",
      icon: Star,
      iconColor: "text-primary bg-primary/10",
    },
    {
      title: t("kpi.avgAbsences"),
      value: kpis?.avg_absences?.toFixed(1) || "—",
      icon: CalendarCheck,
      iconColor: "text-orange-500 bg-orange-500/10",
    },
    {
      title: t("kpi.atRiskStudents"),
      value: kpis?.at_risk_students?.toString() || "0",
      icon: AlertTriangle,
      iconColor: "text-red-600 bg-red-600/10",
    },
  ] as const;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {kpiCards.map((kpi) => (
        <KPICard
          key={kpi.title}
          title={kpi.title}
          value={kpi.value}
          isLoading={isLoading}
          icon={kpi.icon}
          iconColor={kpi.iconColor}
          footer={
            kpis?.total_students &&
            t("kpi.totalStudents", { count: kpis.total_students })
          }
        />
      ))}
    </div>
  );
}

function ChartsSection() {
  const { t } = useTranslation("dashboard");
  const { t: tc } = useTranslation();
  const { filters } = useFilters();

  const { data: classComparison, isLoading } = useQuery({
    queryKey: ["class-comparison", filters.period, filters.gradeLevel],
    queryFn: () =>
      analyticsApi.getClassComparison({
        period: filters.period,
        grade_level: filters.gradeLevel,
      }),
  });

  const chartData =
    classComparison?.map((c) => ({
      name: c.class_name,
      average: c.average_grade,
      students: c.student_count,
    })) || [];

  const avgGrade = classComparison?.length
    ? (
        classComparison.reduce((sum, c) => sum + c.average_grade, 0) /
        classComparison.length
      ).toFixed(1)
    : "—";

  const filterSubtitle = `${filters.period || tc("filters.allPeriods")} | ${
    filters.gradeLevel
      ? tc("filters.gradeLevel", { level: filters.gradeLevel })
      : tc("filters.allGradeLevels")
  }`;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <DashboardBarChart
        title={t("charts.studentsByClass")}
        subtitle={t("charts.studentsByClassDesc")}
        highlightValue={String(
          chartData.reduce((sum, c) => sum + c.students, 0),
        )}
        highlightLabel={t("charts.students")}
        isLoading={isLoading}
        data={chartData}
        dataKey="students"
        tooltipLabel={t("charts.students")}
      />
      <DashboardBarChart
        title={t("charts.gradeComparisonTitle")}
        subtitle={filterSubtitle}
        highlightValue={avgGrade}
        highlightLabel={t("charts.overallAverage")}
        isLoading={isLoading}
        data={chartData}
        dataKey="average"
        tooltipLabel={t("charts.average")}
        yDomain={[0, 100]}
        formatTooltip={(v) => v.toFixed(1)}
      />
    </div>
  );
}

function StudentsTable() {
  const { t } = useTranslation("dashboard");
  const { t: tc } = useTranslation();
  const { filters } = useFilters();
  const atRiskGradeThreshold = useConfigStore((s) => s.atRiskGradeThreshold);

  const { data: students, isLoading } = useQuery({
    queryKey: ["at-risk-students", filters.period, filters.classId],
    queryFn: () =>
      studentsApi.list({
        at_risk_only: true,
        period: filters.period,
        class_id: filters.classId || undefined,
      }),
  });

  return (
    <Card className="shadow-sm overflow-hidden">
      <div className="p-6 border-b border-border flex justify-between items-center">
        <h3 className="text-lg font-bold">{t("urgentStudents.title")}</h3>
        <Link to="/students" search={{ at_risk: true }}>
          <Button variant="link" className="text-primary p-0 h-auto">
            {t("urgentStudents.viewAll")}
          </Button>
        </Link>
      </div>
      <Table>
        <TableHeader>
          <TableRow className="bg-accent/50">
            <TableHead className="text-right font-bold w-12">#</TableHead>
            <TableHead className="text-right font-bold">
              {tc("table.studentName")}
            </TableHead>
            <TableHead className="text-right font-bold">
              {tc("table.class")}
            </TableHead>
            <TableHead className="text-right font-bold">
              {tc("table.averageGrade")}
            </TableHead>
            <TableHead className="text-right font-bold">
              {tc("table.absences")}
            </TableHead>
            <TableHead className="text-right font-bold">
              {tc("table.status")}
            </TableHead>
            <TableHead className="text-right font-bold">
              {tc("table.actions")}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <TableRow key={i}>
                <TableCell>
                  <Skeleton className="h-5 w-8" />
                </TableCell>
                <TableCell>
                  <Skeleton className="h-5 w-32" />
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
                <TableCell>
                  <Skeleton className="h-8 w-8" />
                </TableCell>
              </TableRow>
            ))
          ) : students?.items?.length ? (
            students.items
              .slice(0, AT_RISK_PREVIEW_COUNT)
              .map((student: StudentListItem, index: number) => (
                <TableRow
                  key={student.student_tz}
                  className="hover:bg-accent/30 transition-colors"
                >
                  <TableCell className="text-muted-foreground">
                    {index + 1}
                  </TableCell>
                  <TableCell className="font-semibold">
                    {student.student_name}
                  </TableCell>
                  <TableCell>{student.class_name}</TableCell>
                  <TableCell
                    className={`font-bold ${student.average_grade && student.average_grade < atRiskGradeThreshold ? "text-red-600" : ""}`}
                  >
                    {student.average_grade?.toFixed(1) || "—"}
                  </TableCell>
                  <TableCell>{student.total_absences}</TableCell>
                  <TableCell>
                    <StatusBadge isAtRisk={student.is_at_risk} />
                  </TableCell>
                  <TableCell>
                    <Link
                      to="/students/$studentTz"
                      params={{ studentTz: student.student_tz }}
                    >
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={tc("viewStudent")}
                        className="text-primary hover:text-primary"
                      >
                        <Eye className="size-5" />
                      </Button>
                    </Link>
                  </TableCell>
                </TableRow>
              ))
          ) : (
            <TableRow>
              <TableCell
                colSpan={7}
                className="text-center text-muted-foreground py-12"
              >
                {t("urgentStudents.noAtRisk")}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Card>
  );
}
