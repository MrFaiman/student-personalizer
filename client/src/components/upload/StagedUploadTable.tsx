import { useTranslation } from "react-i18next";
import { X, CheckCircle2, XCircle, AlertTriangle, Loader2, Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { formatHebrewYear } from "@/lib/hebrew-year";
import { MAX_DISPLAYED_ERRORS, YEAR_SELECT_START, YEAR_SELECT_COUNT } from "@/lib/constants";
import type { StagedFile } from "@/lib/upload-detect";

interface StagedUploadTableProps {
    files: StagedFile[];
    onUpdate: (id: string, patch: Partial<StagedFile>) => void;
    onRemove: (id: string) => void;
    onRetry: (id: string) => void;
}

function rowClass(sf: StagedFile): string {
    if (sf.uploadStatus === "uploading") return "bg-blue-50";
    if (sf.uploadStatus === "success") return "bg-green-50";
    if (sf.uploadStatus === "failed") return "bg-red-50";
    if (sf.validationStatus === "duplicate") return "bg-orange-50";
    if (sf.validationStatus === "needs-input") return "bg-yellow-50";
    return "";
}

function StatusCell({ sf, onRetry }: { sf: StagedFile; onRetry: () => void }) {
    const { t } = useTranslation("upload");

    if (sf.uploadStatus === "uploading") {
        return (
            <div className="flex items-center gap-1.5 text-blue-700">
                <Loader2 className="size-3.5 animate-spin" />
                <span className="text-xs">{t("status.uploading")}</span>
            </div>
        );
    }

    if (sf.uploadStatus === "success") {
        return (
            <div className="flex flex-col gap-0.5">
                <div className="flex items-center gap-1.5 text-green-700">
                    <CheckCircle2 className="size-3.5" />
                    <span className="text-xs font-medium">{t("status.success")}</span>
                </div>
                {sf.result && (
                    <div className="text-xs text-green-700 space-y-0.5">
                        <div>{t("success.rows")}: {sf.result.rows_imported}</div>
                        {sf.result.rows_failed > 0 && (
                            <div className="flex items-center gap-1 text-yellow-700">
                                <AlertTriangle className="size-3" />
                                {t("success.partialSuccess", { count: sf.result.rows_failed })}
                            </div>
                        )}
                        {sf.result.errors.length > 0 && (
                            <ul className="text-red-600 list-disc list-inside">
                                {sf.result.errors.slice(0, MAX_DISPLAYED_ERRORS).map((e, i) => (
                                    <li key={i}>{e}</li>
                                ))}
                            </ul>
                        )}
                    </div>
                )}
            </div>
        );
    }

    if (sf.uploadStatus === "failed") {
        return (
            <div className="flex flex-col gap-0.5">
                <div className="flex items-center gap-1.5 text-red-700">
                    <XCircle className="size-3.5" />
                    <span className="text-xs font-medium">
                        {sf.validationStatus === "duplicate" ? t("errors.duplicate") : t("status.failed")}
                    </span>
                </div>
                {sf.error && <p className="text-xs text-red-600">{sf.error}</p>}
                {sf.validationStatus !== "duplicate" && (
                    <Button
                        variant="link"
                        size="sm"
                        className="h-auto p-0 text-xs text-blue-600 justify-start"
                        onClick={onRetry}
                    >
                        {t("action.retry")}
                    </Button>
                )}
            </div>
        );
    }

    // pending states
    if (sf.validationStatus === "ready") {
        return <Badge variant="outline" className="text-xs border-green-400 text-green-700 bg-green-50">{t("status.ready")}</Badge>;
    }
    if (sf.validationStatus === "duplicate") {
        return <Badge variant="outline" className="text-xs border-orange-400 text-orange-700 bg-orange-50">{t("status.duplicate")}</Badge>;
    }
    return <Badge variant="outline" className="text-xs border-yellow-400 text-yellow-700 bg-yellow-50">{t("status.needsInput")}</Badge>;
}

function FileTypeSelect({ sf, onUpdate }: { sf: StagedFile; onUpdate: (patch: Partial<StagedFile>) => void }) {
    const { t } = useTranslation("upload");
    const isPending = sf.uploadStatus === "pending";
    const currentVal = sf.overrideFileType || sf.detectedFileType || "__auto__";
    const isDetected = !sf.overrideFileType && !!sf.detectedFileType;

    return (
        <div className="flex items-center gap-1">
            <Select
                value={currentVal}
                onValueChange={(v) => onUpdate({ overrideFileType: v as StagedFile["overrideFileType"] })}
                disabled={!isPending}
            >
                <SelectTrigger className="h-7 text-xs min-w-[100px]">
                    <SelectValue />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="__auto__">{t("fileType.auto")}</SelectItem>
                    <SelectItem value="grades">{t("fileType.grades")}</SelectItem>
                    <SelectItem value="events">{t("fileType.events")}</SelectItem>
                </SelectContent>
            </Select>
            {isDetected && (
                <span title={t("detected.fromFilename")}>
                    <Wand2 className="size-3 text-muted-foreground shrink-0" />
                </span>
            )}
        </div>
    );
}

function PeriodSelect({ sf, onUpdate }: { sf: StagedFile; onUpdate: (patch: Partial<StagedFile>) => void }) {
    const { t } = useTranslation("upload");
    const isPending = sf.uploadStatus === "pending";
    const currentVal = sf.overridePeriod || sf.detectedPeriod || "";
    const isDetected = !sf.overridePeriod && !!sf.detectedPeriod;

    return (
        <div className="flex items-center gap-1">
            <Select
                value={currentVal}
                onValueChange={(v) => onUpdate({ overridePeriod: v })}
                disabled={!isPending}
            >
                <SelectTrigger className="h-7 text-xs min-w-[90px]">
                    <SelectValue placeholder={t("period.placeholder")} />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="Q1">{t("period.quarter", { number: 1 })}</SelectItem>
                    <SelectItem value="Q2">{t("period.quarter", { number: 2 })}</SelectItem>
                    <SelectItem value="Q3">{t("period.quarter", { number: 3 })}</SelectItem>
                    <SelectItem value="Q4">{t("period.quarter", { number: 4 })}</SelectItem>
                </SelectContent>
            </Select>
            {isDetected && (
                <span title={t("detected.fromFilename")}>
                    <Wand2 className="size-3 text-muted-foreground shrink-0" />
                </span>
            )}
        </div>
    );
}

function YearSelect({ sf, onUpdate }: { sf: StagedFile; onUpdate: (patch: Partial<StagedFile>) => void }) {
    const { t } = useTranslation("upload");
    const isPending = sf.uploadStatus === "pending";
    const currentVal = sf.overrideYear || sf.detectedYear || "";
    const isDetected = !sf.overrideYear && !!sf.detectedYear;

    return (
        <div className="flex items-center gap-1">
            <Select
                value={currentVal}
                onValueChange={(v) => onUpdate({ overrideYear: v })}
                disabled={!isPending}
                dir="rtl"
            >
                <SelectTrigger className="h-7 text-xs min-w-[120px]">
                    <SelectValue placeholder={t("year.placeholder")} />
                </SelectTrigger>
                <SelectContent>
                    {Array.from({ length: YEAR_SELECT_COUNT }, (_, i) => YEAR_SELECT_START + i).map((y) => {
                        const yearStr = `${y}-${y + 1}`;
                        return (
                            <SelectItem key={yearStr} value={yearStr}>
                                {formatHebrewYear(yearStr)}
                            </SelectItem>
                        );
                    })}
                </SelectContent>
            </Select>
            {isDetected && (
                <span title={t("detected.fromFilename")}>
                    <Wand2 className="size-3 text-muted-foreground shrink-0" />
                </span>
            )}
        </div>
    );
}

export function StagedUploadTable({ files, onUpdate, onRemove, onRetry }: StagedUploadTableProps) {
    const { t } = useTranslation("upload");

    if (files.length === 0) return null;

    return (
        <div className="rounded-md border overflow-hidden">
            <Table>
                <TableHeader>
                    <TableRow className="bg-accent/50">
                        <TableHead className="text-xs font-bold w-8 text-right">#</TableHead>
                        <TableHead className="text-xs font-bold">{t("history.file")}</TableHead>
                        <TableHead className="text-xs font-bold">{t("fileType.label")}</TableHead>
                        <TableHead className="text-xs font-bold">{t("period.label")}</TableHead>
                        <TableHead className="text-xs font-bold">{t("year.label")}</TableHead>
                        <TableHead className="text-xs font-bold">{t("history.status")}</TableHead>
                        <TableHead className="w-8" />
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {files.map((sf, index) => (
                        <TableRow key={sf.id} className={rowClass(sf)}>
                            <TableCell className="text-xs text-muted-foreground py-2">{index + 1}</TableCell>
                            <TableCell className="text-sm py-2 max-w-[200px]">
                                <span className="truncate block font-medium" title={sf.filename}>
                                    {sf.filename}
                                </span>
                            </TableCell>
                            <TableCell className="py-1.5">
                                <FileTypeSelect sf={sf} onUpdate={(patch) => onUpdate(sf.id, patch)} />
                            </TableCell>
                            <TableCell className="py-1.5">
                                <PeriodSelect sf={sf} onUpdate={(patch) => onUpdate(sf.id, patch)} />
                            </TableCell>
                            <TableCell className="py-1.5">
                                <YearSelect sf={sf} onUpdate={(patch) => onUpdate(sf.id, patch)} />
                            </TableCell>
                            <TableCell className="py-1.5 max-w-[220px]">
                                <StatusCell sf={sf} onRetry={() => onRetry(sf.id)} />
                            </TableCell>
                            <TableCell className="py-1.5">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 w-7 p-0"
                                    onClick={() => onRemove(sf.id)}
                                    disabled={sf.uploadStatus === "uploading"}
                                >
                                    <X className="size-3.5 text-muted-foreground" />
                                </Button>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}
