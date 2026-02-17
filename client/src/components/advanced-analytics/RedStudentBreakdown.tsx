import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Rectangle,
} from "recharts";
import { useTranslation } from "react-i18next";

import { analyticsApi } from "@/lib/api";
import type { RedStudentGroup } from "@/lib/types/analytics";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { TOOLTIP_STYLE } from "@/lib/chart-styles";

// Shades of red for at-risk student visualization
const RED_SHADES = [
  "#fecaca", // red-200
  "#fca5a5", // red-300
  "#f87171", // red-400
  "#ef4444", // red-500
  "#dc2626", // red-600
  "#b91c1c", // red-700
  "#991b1b", // red-800
  "#7f1d1d", // red-900
];

interface SegmentationTableProps {
  items: RedStudentGroup[];
  title: string;
}

function SegmentationTable({ items, title }: SegmentationTableProps) {
  const { t } = useTranslation("advancedAnalytics");

  return (
    <div>
      <h4 className="font-medium mb-2">{title}</h4>
      <Table>
        <TableHeader>
          <TableRow className="bg-accent/50">
            <TableHead className="text-right font-bold">
              {t("table.name")}
            </TableHead>
            <TableHead className="text-center font-bold">
              {t("table.atRisk")}
            </TableHead>
            <TableHead className="text-center font-bold">
              {t("table.total")}
            </TableHead>
            <TableHead className="text-center font-bold">
              {t("table.percentage")}
            </TableHead>
            <TableHead className="text-center font-bold">
              {t("table.avgGrade")}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={5}
                className="text-center text-muted-foreground py-8"
              >
                {t("noData")}
              </TableCell>
            </TableRow>
          ) : (
            items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="text-right font-medium">
                  {item.name}
                </TableCell>
                <TableCell className="text-center text-red-600 font-bold">
                  {item.red_student_count}
                </TableCell>
                <TableCell className="text-center">
                  {item.total_student_count}
                </TableCell>
                <TableCell className="text-center">
                  {item.percentage.toFixed(1)}%
                </TableCell>
                <TableCell className="text-center">
                  {item.average_grade.toFixed(1)}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}

interface SegmentationBarChartProps {
  items: RedStudentGroup[];
}

function SegmentationBarChart({ items }: SegmentationBarChartProps) {
  const { t } = useTranslation("advancedAnalytics");

  const maxValue = Math.max(
    ...items.map((item) => item.red_student_count),
    1,
  );

  const getShadeByValue = (value: number) => {
    const ratio = value / maxValue;
    const index = Math.min(
      Math.floor(ratio * (RED_SHADES.length - 1)),
      RED_SHADES.length - 1,
    );
    return RED_SHADES[index];
  };

  const renderTooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: readonly { payload: RedStudentGroup }[];
  }) => {
    if (!active || !payload?.length) return null;
    const item = payload[0].payload;
    return (
      <div className="bg-card border rounded-lg p-3 shadow-lg" style={TOOLTIP_STYLE}>
        <p className="font-medium">{item.name}</p>
        <p className="text-red-600">
          {t("tooltip.atRisk")}: {item.red_student_count} /{" "}
          {item.total_student_count}
        </p>
        <p className="text-muted-foreground">
          {item.percentage.toFixed(1)}%
        </p>
        <p className="text-muted-foreground">
          {t("tooltip.avgGrade")}: {item.average_grade.toFixed(1)}
        </p>
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height="100%" className="min-h-[35vh]">
      <BarChart
        data={items}
        layout="vertical"
        margin={{ left: 100, right: 30 }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" tick={{ fontSize: 12 }} />
        <YAxis
          dataKey="name"
          type="category"
          width={90}
          tick={{ fontSize: 11 }}
        />
        <Tooltip content={renderTooltip} />
        <Bar
          dataKey="red_student_count"
          name={t("chart.atRiskStudents")}
          radius={[0, 4, 4, 0]}
          shape={(props) => {
            const p = props as unknown as Record<string, unknown>;
            return (
              <Rectangle
                {...props}
                fill={getShadeByValue(p.red_student_count as number)}
              />
            );
          }}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

interface RedStudentBreakdownProps {
  period?: string;
  gradeLevel?: string;
}

export function RedStudentBreakdown({
  period,
  gradeLevel,
}: RedStudentBreakdownProps) {
  const { t, i18n } = useTranslation("advancedAnalytics");
  const isRTL = i18n.language === "he";

  const { data, isLoading, error } = useQuery({
    queryKey: ["red-student-segmentation", period, gradeLevel],
    queryFn: () =>
      analyticsApi.getRedStudentSegmentation({
        period,
        grade_level: gradeLevel,
      }),
  });

  if (isLoading) {
    return (
      <Card className="shadow-sm">
        <CardContent className="p-6">
          <Skeleton className="h-8 w-48 mb-4" />
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

  return (
    <Card className="shadow-sm">
      <CardContent className="p-6">
        <div className="mb-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <span className="text-red-600">{t("redStudents.title")}</span>
            <span className="text-sm font-normal text-muted-foreground">
              ({t("redStudents.threshold", { value: data.threshold })})
            </span>
          </h3>
          <div className="text-2xl font-bold text-red-600 mt-1">
            {data.total_red_students} {t("redStudents.students")}
          </div>
        </div>

        <Tabs defaultValue="class" dir={isRTL ? "rtl" : "ltr"}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="class">{t("tabs.byClass")}</TabsTrigger>
            <TabsTrigger value="layer">{t("tabs.byGradeLevel")}</TabsTrigger>
            <TabsTrigger value="teacher">{t("tabs.byTeacher")}</TabsTrigger>
            <TabsTrigger value="subject">{t("tabs.bySubject")}</TabsTrigger>
          </TabsList>

          <TabsContent value="class" className="space-y-4 mt-4">
            <SegmentationBarChart items={data.by_class} />
            <SegmentationTable
              items={data.by_class}
              title={t("redStudents.breakdownByClass")}
            />
          </TabsContent>

          <TabsContent value="layer" className="space-y-4 mt-4">
            <SegmentationBarChart items={data.by_layer} />
            <SegmentationTable
              items={data.by_layer}
              title={t("redStudents.breakdownByGradeLevel")}
            />
          </TabsContent>

          <TabsContent value="teacher" className="space-y-4 mt-4">
            <SegmentationBarChart items={data.by_teacher} />
            <SegmentationTable
              items={data.by_teacher}
              title={t("redStudents.breakdownByTeacher")}
            />
          </TabsContent>

          <TabsContent value="subject" className="space-y-4 mt-4">
            <SegmentationBarChart items={data.by_subject} />
            <SegmentationTable
              items={data.by_subject}
              title={t("redStudents.breakdownBySubject")}
            />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
