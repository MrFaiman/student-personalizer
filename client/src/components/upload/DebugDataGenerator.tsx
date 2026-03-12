import { useState, useMemo, useCallback } from "react";
import { CheckCircle2, FlaskConical } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { ingestionApi } from "@/lib/api";
import { formatHebrewYear } from "@/lib/hebrew-year";

export function DebugDataGenerator() {
  const { t } = useTranslation("upload");
  const queryClient = useQueryClient();

  const [isGenerating, setIsGenerating] = useState(false);
  const [generateResult, setGenerateResult] = useState<{
    rows: number;
    students: number;
  } | null>(null);
  const [debugStudents, setDebugStudents] = useState(120);
  const [debugStartYear, setDebugStartYear] = useState(2024);
  const [debugEndYear, setDebugEndYear] = useState(2025);

  const debugYearOptions = useMemo<number[]>(
    () => Array.from({ length: 15 }, (_, i) => 2021 + i),
    [],
  );
  const debugYears = useMemo(() => {
    const start = Math.min(debugStartYear, debugEndYear);
    const end = Math.max(debugStartYear, debugEndYear);
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }, [debugStartYear, debugEndYear]);

  const handleGenerate = useCallback(async () => {
    setIsGenerating(true);
    setGenerateResult(null);
    try {
      const result = await ingestionApi.generateDebugData({
        students: debugStudents,
        years: debugYears,
      });
      setGenerateResult({
        rows: result.total_rows_imported,
        students: result.total_students_created,
      });
      queryClient.invalidateQueries({ queryKey: ["import-logs"] });
      queryClient.invalidateQueries({ queryKey: ["students"] });
      queryClient.invalidateQueries({ queryKey: ["classes"] });
      queryClient.invalidateQueries({ queryKey: ["kpis"] });
    } catch {
      setGenerateResult(null);
    } finally {
      setIsGenerating(false);
    }
  }, [debugStudents, debugYears, queryClient]);

  return (
    <Card className="border-dashed border-yellow-300 bg-yellow-50/50">
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <FlaskConical className="size-4 text-yellow-600" />
            <div>
              <p className="text-sm font-medium text-yellow-800">
                {t("debug.title")}
              </p>
              <p className="text-xs text-yellow-700">
                {t("debug.subtitle", {
                  students: debugStudents,
                  startYear: Math.min(debugStartYear, debugEndYear),
                  endYear: Math.max(debugStartYear, debugEndYear),
                })}
              </p>
            </div>
          </div>
          <div className="flex items-end gap-3 flex-wrap">
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-yellow-800">
                {t("debug.studentsLabel")}
              </Label>
              <Input
                type="number"
                min={1}
                max={500}
                value={debugStudents}
                onChange={(e) => {
                  const next = Number(e.target.value);
                  if (Number.isNaN(next)) return;
                  setDebugStudents(Math.max(1, Math.min(500, next)));
                }}
                className="w-34 h-8 bg-white"
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-yellow-800">
                {t("debug.startYearLabel")}
              </Label>
              <Select
                value={String(debugStartYear)}
                onValueChange={(v) => setDebugStartYear(Number(v))}
              >
                <SelectTrigger className="w-34 h-8 bg-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {debugYearOptions.map((y) => {
                    const year = `${y}-${y + 1}`;
                    return (
                      <SelectItem key={y} value={String(y)}>
                        {formatHebrewYear(year)}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-yellow-800">
                {t("debug.endYearLabel")}
              </Label>
              <Select
                value={String(debugEndYear)}
                onValueChange={(v) => setDebugEndYear(Number(v))}
              >
                <SelectTrigger className="w-34 h-8 bg-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {debugYearOptions.map((y) => {
                    const year = `${y}-${y + 1}`;
                    return (
                      <SelectItem key={y} value={String(y)}>
                        {formatHebrewYear(year)}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {generateResult && (
              <span className="text-xs text-green-700 flex items-center gap-1">
                <CheckCircle2 className="size-3.5" />
                {t("debug.success", {
                  rows: generateResult.rows,
                  students: generateResult.students,
                })}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerate}
              disabled={isGenerating || debugStudents < 1}
              className="border-yellow-400 text-yellow-800 hover:bg-yellow-100"
            >
              <FlaskConical className="size-3.5 ml-1.5" />
              {isGenerating ? t("debug.generating") : t("debug.button")}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
