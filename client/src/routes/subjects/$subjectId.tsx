import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BarChart3, School } from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  CartesianGrid,
  Rectangle,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useFilters } from "@/components/FilterContext";
import { PageHeader } from "@/components/PageHeader";
import { getBarColor } from "@/lib/utils";
import { TOOLTIP_STYLE } from "@/lib/chart-styles";
import { analyticsApi } from "@/lib/api";
import { useConfigStore } from "@/lib/config-store";

export const Route = createFileRoute("/subjects/$subjectId")({
  component: SubjectDetailPage,
});

function SubjectDetailPage() {
  const { t } = useTranslation("subjects");
  const { t: tc } = useTranslation();
  const { subjectId } = Route.useParams();
  const { filters } = useFilters();
  const gradeRange = useConfigStore((s) => s.gradeRange);

  const { data: subject, isLoading } = useQuery({
    queryKey: ["subject-detail", filters.year, subjectId, filters.period],
    queryFn: () =>
      analyticsApi.getSubjectDetail(subjectId, {
        year: filters.year,
        period: filters.period,
      }),
  });

  const classChartData =
    subject?.classes.map((cls) => ({
      name: cls.name,
      average: cls.average_grade,
      students: cls.student_count,
      id: cls.id,
    })) ?? [];

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-40" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-[30vh] w-full" />
      </div>
    );
  }

  if (!subject) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        {t("detail.notFound")}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Helmet>
        <title>{`${subject.name} | ${tc("appName")}`}</title>
      </Helmet>
      <PageHeader
        backTo="/subjects"
        backLabel={t("detail.backToList")}
        title={subject.name}
        subtitle={t("detail.subtitle", {
          teachers: subject.teachers.length,
          classes: subject.classes.length,
        })}
        stats={[
          {
            value: subject.stats.average_grade?.toFixed(1) || "-",
            label: tc("table.average"),
          },
          { value: subject.stats.student_count, label: tc("general.students") },
        ]}
      />

      {/* Grade Distribution */}
      <Card>
        <CardContent className="p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <BarChart3 className="size-5 text-primary" />
            {t("detail.gradeDistribution")}
          </h3>
          <div className="h-[30vh]">
            {subject.grade_histogram.some((d) => d.count > 0) ? (
              <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                <AreaChart data={subject.grade_histogram}>
                  <defs>
                    <linearGradient
                      id="distributionGrad"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis
                    dataKey="grade"
                    type="number"
                    domain={gradeRange}
                    tick={{ fontSize: 12 }}
                    label={{
                      value: t("detail.gradeAxis"),
                      position: "insideBottom",
                      offset: -2,
                      fontSize: 12,
                    }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    allowDecimals={false}
                    label={{
                      value: t("detail.studentCount"),
                      angle: -90,
                      position: "insideLeft",
                      fontSize: 12,
                    }}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    labelFormatter={(label) =>
                      `${t("detail.gradeAxis")}: ${label}`
                    }
                    formatter={(value) => [
                      `${value}`,
                      t("detail.studentCount"),
                    ]}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#22c55e"
                    strokeWidth={2}
                    fill="url(#distributionGrad)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                {tc("noData")}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Per-Class Performance */}
      <Card>
        <CardContent className="p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <School className="size-5 text-primary" />
            {t("detail.classPerformance")}
          </h3>
          <div className="h-[30vh]">
            {classChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                <BarChart data={classChartData}>
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis domain={gradeRange} tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    formatter={(value) => [
                      `${Number(value).toFixed(1)}`,
                      tc("table.average"),
                    ]}
                  />
                  <Bar
                    dataKey="average"
                    radius={[4, 4, 0, 0]}
                    shape={(props) => (
                      <Rectangle {...props} fill={getBarColor(props.index)} />
                    )}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                {tc("noData")}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
