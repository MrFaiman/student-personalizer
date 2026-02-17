import { useState, useEffect, useMemo } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import { BarChart3 } from "lucide-react";

import { analyticsApi } from "@/lib/api";
import { useCascadingFilters } from "@/hooks/useCascadingFilters";
import {
  PeriodComparisonChart,
  RedStudentBreakdown,
  VersusComparisonChart,
} from "@/components/advanced-analytics";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/advanced-analytics")({
  component: AdvancedAnalyticsPage,
});

function AdvancedAnalyticsPage() {
  const { t, i18n } = useTranslation("advancedAnalytics");
  const { t: tc } = useTranslation();
  const isRTL = i18n.language === "he";

  const { data: metadata } = useQuery({
    queryKey: ["metadata"],
    queryFn: () => analyticsApi.getMetadata(),
  });

  const periods = useMemo(() => metadata?.periods || [], [metadata?.periods]);

  const {
    filters,
    options,
    setGradeLevel,
    setClassId,
    setPeriodA,
    setPeriodB,
    resetFilters,
  } = useCascadingFilters(periods);

  // Set initial periods when metadata loads
  useEffect(() => {
    if (periods.length >= 2 && !filters.periodA && !filters.periodB) {
      setPeriodA(periods[0]);
      setPeriodB(periods[1]);
    } else if (periods.length === 1 && !filters.periodA) {
      setPeriodA(periods[0]);
    }
  }, [periods, filters.periodA, filters.periodB, setPeriodA, setPeriodB]);

  const [comparisonType, setComparisonType] = useState<
    "class" | "subject_teacher" | "subject"
  >("class");

  return (
    <>
      <Helmet>
        <title>{`${t("pageTitle")} | ${tc("appName")}`}</title>
      </Helmet>

      <div className="space-y-4">
        {/* Page Header */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <BarChart3 className="size-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">{t("pageTitle")}</h1>
            <p className="text-muted-foreground">{t("pageDescription")}</p>
          </div>
        </div>

        {/* Filter Bar */}
        <Card className="shadow-sm">
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4 items-end">
              {/* Grade Level Filter */}
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium">
                  {t("filters.gradeLevel")}
                </label>
                <Select
                  value={filters.gradeLevel || "all"}
                  onValueChange={(v) =>
                    setGradeLevel(v === "all" ? undefined : v)
                  }
                >
                  <SelectTrigger className="w-36">
                    <SelectValue placeholder={tc("filters.allGradeLevels")} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">
                      {tc("filters.allGradeLevels")}
                    </SelectItem>
                    {metadata?.grade_levels.map((level) => (
                      <SelectItem key={level} value={level}>
                        {tc("filters.gradeLevel", { level })}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Class Filter (cascading) */}
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium">
                  {t("filters.class")}
                </label>
                <Select
                  value={filters.classId || "all"}
                  onValueChange={(v) => setClassId(v === "all" ? undefined : v)}
                >
                  <SelectTrigger className="w-36">
                    <SelectValue placeholder={tc("filters.allClasses")} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">
                      {tc("filters.allClasses")}
                    </SelectItem>
                    {options?.classes.map((cls) => (
                      <SelectItem key={cls.id} value={cls.id}>
                        {cls.class_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Period A */}
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium">
                  {t("filters.periodA")}
                </label>
                <Select
                  value={filters.periodA || ""}
                  onValueChange={setPeriodA}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder={t("filters.selectPeriod")} />
                  </SelectTrigger>
                  <SelectContent>
                    {periods.map((period) => (
                      <SelectItem key={period} value={period}>
                        {period}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Period B */}
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium">
                  {t("filters.periodB")}
                </label>
                <Select
                  value={filters.periodB || ""}
                  onValueChange={setPeriodB}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder={t("filters.selectPeriod")} />
                  </SelectTrigger>
                  <SelectContent>
                    {periods
                      .filter((p) => p !== filters.periodA)
                      .map((period) => (
                        <SelectItem key={period} value={period}>
                          {period}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Reset Filters */}
              <Button variant="outline" onClick={resetFilters}>
                {t("filters.reset")}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Main Content Tabs */}
        <Tabs
          defaultValue="versus"
          className="space-y-4"
          dir={isRTL ? "rtl" : "ltr"}
        >
          <TabsList className={isRTL ? "flex-row-reverse" : ""}>
            <TabsTrigger value="comparison">
              {t("tabs.periodComparison")}
            </TabsTrigger>
            <TabsTrigger value="at-risk">
              {t("tabs.atRiskStudents")}
            </TabsTrigger>
            <TabsTrigger value="versus">
              {t("tabs.versusComparison")}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="comparison" className="space-y-4">
            {/* Comparison Type Selector */}
            <div className="flex gap-2">
              <Select
                value={comparisonType}
                onValueChange={(v) =>
                  setComparisonType(
                    v as "class" | "subject_teacher" | "subject",
                  )
                }
              >
                <SelectTrigger className="w-56">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="class">
                    {t("periodComparison.types.class")}
                  </SelectItem>
                  <SelectItem value="subject_teacher">
                    {t("periodComparison.types.subject_teacher")}
                  </SelectItem>
                  <SelectItem value="subject">
                    {t("periodComparison.types.subject")}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Period Comparison Chart */}
            {filters.periodA && filters.periodB ? (
              <PeriodComparisonChart
                periodA={filters.periodA}
                periodB={filters.periodB}
                comparisonType={comparisonType}
                gradeLevel={filters.gradeLevel}
                classId={filters.classId}
              />
            ) : (
              <Card className="shadow-sm">
                <CardContent className="h-[30vh] flex items-center justify-center">
                  <p className="text-muted-foreground">
                    {t("periodComparison.selectTwoPeriods")}
                  </p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="at-risk">
            <RedStudentBreakdown
              period={filters.periodA}
              gradeLevel={filters.gradeLevel}
            />
          </TabsContent>

          <TabsContent value="versus">
            <VersusComparisonChart period={filters.periodA} />
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}
