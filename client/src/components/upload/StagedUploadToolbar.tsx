import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { formatHebrewYear } from "@/lib/hebrew-year";
import { YEAR_SELECT_START, YEAR_SELECT_COUNT } from "@/lib/constants";
import type { FileTypeValue, StagedFile } from "@/lib/upload-detect";

interface StagedUploadToolbarProps {
  files: StagedFile[];
  onUpload: () => void;
  onClearAll: () => void;
  onBulkApply: (patch: {
    overrideFileType?: FileTypeValue | "__auto__";
    overridePeriod?: string;
    overrideYear?: string;
  }) => void;
  isUploading: boolean;
}

export function StagedUploadToolbar({
  files,
  onUpload,
  onClearAll,
  onBulkApply,
  isUploading,
}: StagedUploadToolbarProps) {
  const { t } = useTranslation("upload");
  const [bulkFileType, setBulkFileType] = useState<FileTypeValue | "__auto__">(
    "__auto__",
  );
  const [bulkPeriod, setBulkPeriod] = useState("");
  const [bulkYear, setBulkYear] = useState("");

  const readyCount = files.filter(
    (f) => f.validationStatus === "ready" && f.uploadStatus === "pending",
  ).length;
  const pendingCount = files.filter((f) => f.uploadStatus === "pending").length;

  const handleApply = () => {
    const patch: Parameters<typeof onBulkApply>[0] = {};
    patch.overrideFileType = bulkFileType;
    if (bulkPeriod) patch.overridePeriod = bulkPeriod;
    if (bulkYear) patch.overrideYear = bulkYear;
    if (Object.keys(patch).length > 0) onBulkApply(patch);
  };

  return (
    <div className="flex flex-wrap items-end gap-3 p-3 bg-muted/30 rounded-lg border">
      {/* Bulk selectors */}
      <div className="flex items-end gap-2 flex-wrap">
        <div>
          <Label className="text-xs mb-1">{t("bulk.fileType")}</Label>
          <Select
            value={bulkFileType}
            onValueChange={(v) => setBulkFileType(v as typeof bulkFileType)}
            disabled={pendingCount === 0}
          >
            <SelectTrigger className="h-8 text-xs w-[120px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__auto__">-</SelectItem>
              <SelectItem value="grades">{t("fileType.grades")}</SelectItem>
              <SelectItem value="events">{t("fileType.events")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs mb-1">{t("bulk.period")}</Label>
          <Select
            value={bulkPeriod}
            onValueChange={setBulkPeriod}
            disabled={pendingCount === 0}
          >
            <SelectTrigger className="h-8 text-xs w-[100px]">
              <SelectValue placeholder="-" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Q1">
                {t("period.quarter", { number: 1 })}
              </SelectItem>
              <SelectItem value="Q2">
                {t("period.quarter", { number: 2 })}
              </SelectItem>
              <SelectItem value="Q3">
                {t("period.quarter", { number: 3 })}
              </SelectItem>
              <SelectItem value="Q4">
                {t("period.quarter", { number: 4 })}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs mb-1">{t("bulk.year")}</Label>
          <Select
            value={bulkYear}
            onValueChange={setBulkYear}
            disabled={pendingCount === 0}
            dir="rtl"
          >
            <SelectTrigger className="h-8 text-xs w-[140px]">
              <SelectValue placeholder="-" />
            </SelectTrigger>
            <SelectContent>
              {Array.from(
                { length: YEAR_SELECT_COUNT },
                (_, i) => YEAR_SELECT_START + i,
              ).map((y) => {
                const yearStr = `${y}-${y + 1}`;
                return (
                  <SelectItem key={yearStr} value={yearStr}>
                    {formatHebrewYear(yearStr)}
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="h-8 text-xs"
          disabled={pendingCount === 0}
          onClick={handleApply}
        >
          {t("bulk.apply")}
        </Button>
      </div>

      <div className="flex-1" />

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="h-8 text-xs text-muted-foreground"
          onClick={onClearAll}
          disabled={isUploading}
        >
          {t("staging.clearAll")}
        </Button>
        <Button
          size="sm"
          className="h-8 text-xs"
          onClick={onUpload}
          disabled={readyCount === 0 || isUploading}
        >
          {t("staging.uploadReady", { count: readyCount })}
        </Button>
      </div>
    </div>
  );
}
