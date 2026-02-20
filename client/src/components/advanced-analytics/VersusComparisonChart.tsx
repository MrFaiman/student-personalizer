import { useState } from "react";
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
import { X } from "lucide-react";
import { useTranslation } from "react-i18next";

import { analyticsApi, studentsApi } from "@/lib/api";
import type { VersusSeriesItem } from "@/lib/types/analytics";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { TOOLTIP_STYLE } from "@/lib/chart-styles";
import { getBarColor } from "@/lib/utils";

type ComparisonType = "class" | "teacher" | "layer";

interface VersusComparisonChartProps {
  period?: string;
}

export function VersusComparisonChart({ period }: VersusComparisonChartProps) {
  const { t } = useTranslation("advancedAnalytics");
  const [comparisonType, setComparisonType] = useState<ComparisonType>("class");
  const [selectedEntities, setSelectedEntities] = useState<string[]>([]);

  // Fetch available entities based on comparison type
  const { data: metadata } = useQuery({
    queryKey: ["metadata"],
    queryFn: () => analyticsApi.getMetadata(),
  });

  const { data: classes } = useQuery({
    queryKey: ["classes", period],
    queryFn: () => studentsApi.getClasses({ period }),
    enabled: comparisonType === "class",
  });

  const { data: teachers } = useQuery({
    queryKey: ["teachers-list", period],
    queryFn: () => analyticsApi.getTeachersList({ period }),
    enabled: comparisonType === "teacher",
  });

  // Get available options based on type
  const getOptions = (): { id: string; name: string }[] => {
    if (comparisonType === "class" && classes) {
      return classes.map((c) => ({ id: c.id, name: c.class_name }));
    }
    if (comparisonType === "teacher" && teachers) {
      return teachers.map((t) => ({ id: t.id, name: t.name }));
    }
    if (comparisonType === "layer" && metadata) {
      return metadata.grade_levels.map((l) => ({
        id: l,
        name: `${t("versus.grade")} ${l}`,
      }));
    }
    return [];
  };

  const options = getOptions();

  // Fetch comparison data
  const { data: chartData, isLoading } = useQuery({
    queryKey: ["versus-comparison", comparisonType, selectedEntities, period],
    queryFn: () =>
      analyticsApi.getVersusComparison({
        comparison_type: comparisonType,
        entity_ids: selectedEntities.join(","),
        period,
      }),
    enabled: selectedEntities.length >= 2,
  });

  const handleEntitySelect = (entityId: string) => {
    if (!selectedEntities.includes(entityId) && selectedEntities.length < 6) {
      setSelectedEntities([...selectedEntities, entityId]);
    }
  };

  const handleEntityRemove = (entityId: string) => {
    setSelectedEntities(selectedEntities.filter((id) => id !== entityId));
  };

  const handleTypeChange = (type: ComparisonType) => {
    setComparisonType(type);
    setSelectedEntities([]);
  };

  const renderTooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: readonly { payload: VersusSeriesItem }[];
  }) => {
    if (!active || !payload?.length) return null;

    const item = payload[0].payload;
    return (
      <div
        className="bg-card border rounded-lg p-3 shadow-lg"
        style={TOOLTIP_STYLE}
      >
        <p className="font-medium">{item.name}</p>
        <p className="text-lg font-bold">{item.value.toFixed(1)}</p>
        <p className="text-sm text-muted-foreground">
          {t("tooltip.students")}: {item.student_count}
        </p>
      </div>
    );
  };

  return (
    <Card className="shadow-sm">
      <CardContent className="p-6">
        <div className="mb-4">
          <h3 className="text-lg font-bold">{t("versus.title")}</h3>
        </div>

        <div className="flex flex-wrap gap-2 mb-4">
          {/* Comparison Type Selector */}
          <Select
            value={comparisonType}
            onValueChange={(v) => handleTypeChange(v as ComparisonType)}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder={t("versus.compareBy")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="class">{t("versus.classVsClass")}</SelectItem>
              <SelectItem value="teacher">
                {t("versus.teacherVsTeacher")}
              </SelectItem>
              <SelectItem value="layer">{t("versus.gradeVsGrade")}</SelectItem>
            </SelectContent>
          </Select>

          {/* Entity Selector */}
          <Select onValueChange={handleEntitySelect}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder={t(`versus.select.${comparisonType}`)} />
            </SelectTrigger>
            <SelectContent>
              {options
                .filter((opt) => !selectedEntities.includes(opt.id))
                .map((opt) => (
                  <SelectItem key={opt.id} value={opt.id}>
                    {opt.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>

        {/* Selected Entities */}
        <div className="flex flex-wrap gap-2 mb-4">
          {selectedEntities.map((entityId, index) => {
            const entity = options.find((o) => o.id === entityId);
            return (
              <Badge
                key={entityId}
                variant="outline"
                style={{
                  borderColor: getBarColor(index),
                }}
                className="flex items-center gap-1"
              >
                {entity?.name || entityId}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-4 w-4 p-0 hover:bg-transparent"
                  onClick={() => handleEntityRemove(entityId)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            );
          })}
        </div>

        {/* Chart */}
        {selectedEntities.length < 2 ? (
          <div className="h-[35vh] flex items-center justify-center text-muted-foreground">
            {t("versus.selectAtLeast2")}
          </div>
        ) : isLoading ? (
          <Skeleton className="h-[35vh] w-full" />
        ) : chartData ? (
          <ResponsiveContainer width="100%" height="100%" className="min-h-[35vh]">
            <BarChart data={chartData.series}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
              <Tooltip content={renderTooltip} />
              <Bar
                dataKey="value"
                name={t("chart.averageGrade")}
                radius={[4, 4, 0, 0]}
                shape={(props) => (
                  <Rectangle
                    {...props}
                    fill={getBarColor(props.index)}
                  />
                )}
              />
            </BarChart>
          </ResponsiveContainer>
        ) : null}
      </CardContent>
    </Card>
  );
}
