import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useTranslation } from "react-i18next";

import { advancedAnalyticsApi } from "@/lib/api";
import type { PeriodComparisonItem } from "@/lib/types/advanced-analytics";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TOOLTIP_STYLE } from "@/lib/chart-styles";

interface PeriodComparisonChartProps {
  periodA: string;
  periodB: string;
  comparisonType: "class" | "subject_teacher" | "subject";
  gradeLevel?: string;
  classId?: string;
}

export function PeriodComparisonChart({
  periodA,
  periodB,
  comparisonType,
  gradeLevel,
  classId,
}: PeriodComparisonChartProps) {
  const { t } = useTranslation("advancedAnalytics");

  const { data, isLoading, error } = useQuery({
    queryKey: [
      "period-comparison",
      periodA,
      periodB,
      comparisonType,
      gradeLevel,
      classId,
    ],
    queryFn: () =>
      advancedAnalyticsApi.getPeriodComparison({
        period_a: periodA,
        period_b: periodB,
        comparison_type: comparisonType,
        grade_level: gradeLevel,
        class_id: classId,
      }),
    enabled: !!periodA && !!periodB,
  });

  if (isLoading) {
    return (
      <Card className="shadow-sm">
        <CardContent className="p-6">
          <Skeleton className="h-8 w-64 mb-4" />
          <Skeleton className="h-[50vh] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="shadow-sm">
        <CardContent className="h-[50vh] flex items-center justify-center">
          <p className="text-muted-foreground">{t("errors.loadFailed")}</p>
        </CardContent>
      </Card>
    );
  }

  // Transform data for grouped bar chart
  const chartData = data.data.map((item: PeriodComparisonItem) => ({
    name: item.name,
    [periodA]: item.period_a_average,
    [periodB]: item.period_b_average,
    change: item.change,
    changePercent: item.change_percent,
    teacherName: item.teacher_name,
    subject: item.subject,
    studentCountA: item.student_count_a,
    studentCountB: item.student_count_b,
  }));

  const renderTooltip = ({
    active,
    payload,
    label,
  }: {
    active?: boolean;
    payload?: {
      dataKey: string;
      value: number | null;
      color: string;
      payload: {
        name: string;
        change: number | null;
        changePercent: number | null;
        teacherName?: string;
        subject?: string;
        studentCountA: number;
        studentCountB: number;
      };
    }[];
    label?: string;
  }) => {
    if (!active || !payload?.length) return null;

    const item = payload[0]?.payload;
    return (
      <div
        className="bg-card border rounded-lg p-3 shadow-lg"
        style={TOOLTIP_STYLE}
      >
        <p className="font-medium">{label}</p>
        {item.teacherName && (
          <p className="text-sm text-muted-foreground">
            {t("tooltip.teacher")}: {item.teacherName}
          </p>
        )}
        {item.subject && (
          <p className="text-sm text-muted-foreground">
            {t("tooltip.subject")}: {item.subject}
          </p>
        )}
        <div className="mt-2 space-y-1">
          {payload.map((entry) => (
            <p key={entry.dataKey} style={{ color: entry.color }}>
              {entry.dataKey}: {entry.value?.toFixed(1) ?? "—"}
            </p>
          ))}
        </div>
        {item.change !== null && (
          <p
            className={`mt-2 font-medium ${
              item.change >= 0 ? "text-green-600" : "text-red-600"
            }`}
          >
            {t("tooltip.change")}: {item.change >= 0 ? "+" : ""}
            {item.change.toFixed(1)} ({item.changePercent?.toFixed(1)}%)
          </p>
        )}
      </div>
    );
  };

  return (
    <Card className="shadow-sm">
      <CardContent className="p-6">
        <div className="mb-4">
          <h3 className="text-lg font-bold">
            {t("periodComparison.title")}: {periodA} vs {periodB}
          </h3>
          <p className="text-sm text-muted-foreground">
            {t(`periodComparison.types.${comparisonType}`)}
          </p>
        </div>
        {chartData.length === 0 ? (
          <div className="h-[50vh] flex items-center justify-center text-muted-foreground">
            {t("noData")}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%" className="min-h-[50vh]">
            <BarChart
              data={chartData}
              margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="name"
                angle={-45}
                textAnchor="end"
                interval={0}
                height={80}
                tick={{ fontSize: 11 }}
              />
              <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
              <Tooltip content={renderTooltip} />
              <Legend />
              <Bar
                dataKey={periodA}
                fill="#3b82f6"
                name={periodA}
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey={periodB}
                fill="#10b981"
                name={periodB}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
