import { createFileRoute } from "@tanstack/react-router";
import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import { useState, useCallback, useMemo } from "react";
import { Helmet } from "react-helmet-async";
import {
  Upload,
  Clock,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Trash2,
  FlaskConical,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ingestionApi } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import { formatHebrewYear } from "@/lib/hebrew-year";
import { TablePagination } from "@/components/TablePagination";
import { SortableTableHead } from "@/components/SortableTableHead";
import { useTableSort } from "@/hooks/useTableSort";
import { useConfigStore } from "@/lib/config-store";
import {
  type StagedFile,
  type FileTypeValue,
  createStagedFile,
  revalidateAll,
  resolvedFileType,
  resolvedPeriod,
  resolvedYear,
} from "@/lib/upload-detect";
import { StagedUploadTable } from "@/components/upload/StagedUploadTable";
import { StagedUploadToolbar } from "@/components/upload/StagedUploadToolbar";

export const Route = createFileRoute("/upload")({
  component: UploadPage,
});

function BatchSummary({ files }: { files: StagedFile[] }) {
  const { t } = useTranslation("upload");
  const ready = files.filter(
    (f) => f.validationStatus === "ready" && f.uploadStatus === "pending",
  ).length;
  const needsInput = files.filter(
    (f) => f.validationStatus === "needs-input" && f.uploadStatus === "pending",
  ).length;
  const duplicate = files.filter(
    (f) => f.validationStatus === "duplicate" && f.uploadStatus === "pending",
  ).length;
  const success = files.filter((f) => f.uploadStatus === "success").length;
  const failed = files.filter((f) => f.uploadStatus === "failed").length;

  return (
    <div className="flex flex-wrap gap-3 text-xs mt-1">
      {ready > 0 && (
        <span className="flex items-center gap-1 text-green-700">
          <CheckCircle2 className="size-3.5" />
          {t("summary.ready", { count: ready })}
        </span>
      )}
      {needsInput > 0 && (
        <span className="flex items-center gap-1 text-yellow-700">
          <AlertTriangle className="size-3.5" />
          {t("summary.needsInput", { count: needsInput })}
        </span>
      )}
      {duplicate > 0 && (
        <span className="flex items-center gap-1 text-orange-700">
          <AlertTriangle className="size-3.5" />
          {t("summary.duplicate", { count: duplicate })}
        </span>
      )}
      {success > 0 && (
        <span className="flex items-center gap-1 text-green-700">
          <CheckCircle2 className="size-3.5" />
          {t("summary.success", { count: success })}
        </span>
      )}
      {failed > 0 && (
        <span className="flex items-center gap-1 text-red-700">
          <XCircle className="size-3.5" />
          {t("summary.failed", { count: failed })}
        </span>
      )}
    </div>
  );
}

function UploadPage() {
  const { t } = useTranslation("upload");
  const { t: tc } = useTranslation();
  const queryClient = useQueryClient();

  const [dragActive, setDragActive] = useState(false);
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [batchToDelete, setBatchToDelete] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateResult, setGenerateResult] = useState<{
    rows: number;
    students: number;
  } | null>(null);
  const [debugStudents, setDebugStudents] = useState(120);
  const [debugStartYear, setDebugStartYear] = useState(2024);
  const [debugEndYear, setDebugEndYear] = useState(2025);

  const defaultPageSize = useConfigStore((s) => s.defaultPageSize);
  const enableDebug = useConfigStore((s) => s.enableDebug);
  const [logPage, setLogPage] = useState(1);
  const logPageSize = defaultPageSize;
  const { sort: logSort, toggleSort: toggleLogSort } = useTableSort<string>();

  const debugYearOptions = useMemo<number[]>(
    () => Array.from({ length: 15 }, (_, i) => 2021 + i),
    [],
  );
  const debugYears = useMemo(() => {
    const start = Math.min(debugStartYear, debugEndYear);
    const end = Math.max(debugStartYear, debugEndYear);
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }, [debugStartYear, debugEndYear]);

  const { data: logs, isLoading: logsLoading } = useQuery({
    queryKey: ["import-logs", logPage, logSort.column, logSort.direction],
    queryFn: () =>
      ingestionApi.getLogs({
        page: logPage,
        page_size: logPageSize,
        sort_by: logSort.column || undefined,
        sort_order: logSort.direction,
      }),
    placeholderData: keepPreviousData,
  });

  const addFiles = useCallback((newFiles: File[]) => {
    setStagedFiles((prev) => {
      const added = newFiles.map((f) => createStagedFile(f, prev));
      return revalidateAll([...prev, ...added]);
    });
  }, []);

  const updateFile = useCallback((id: string, patch: Partial<StagedFile>) => {
    setStagedFiles((prev) =>
      revalidateAll(prev.map((f) => (f.id === id ? { ...f, ...patch } : f))),
    );
  }, []);

  const removeFile = useCallback((id: string) => {
    setStagedFiles((prev) => revalidateAll(prev.filter((f) => f.id !== id)));
  }, []);

  const retryFile = useCallback((id: string) => {
    setStagedFiles((prev) =>
      revalidateAll(
        prev.map((f) =>
          f.id === id
            ? {
                ...f,
                uploadStatus: "pending",
                error: undefined,
                result: undefined,
              }
            : f,
        ),
      ),
    );
  }, []);

  const clearAll = useCallback(() => setStagedFiles([]), []);

  const bulkApply = useCallback(
    (patch: {
      overrideFileType?: FileTypeValue | "__auto__";
      overridePeriod?: string;
      overrideYear?: string;
    }) => {
      setStagedFiles((prev) =>
        revalidateAll(
          prev.map((f) =>
            f.uploadStatus !== "pending" ? f : { ...f, ...patch },
          ),
        ),
      );
    },
    [],
  );

  const executeUpload = useCallback(async () => {
    if (isUploading) return;
    const toUpload = stagedFiles.filter(
      (f) => f.validationStatus === "ready" && f.uploadStatus === "pending",
    );
    if (toUpload.length === 0) return;

    setIsUploading(true);

    for (const sf of toUpload) {
      setStagedFiles((prev) =>
        prev.map((f) =>
          f.id === sf.id ? { ...f, uploadStatus: "uploading" } : f,
        ),
      );

      try {
        const result = await ingestionApi.upload(sf.file, {
          file_type: resolvedFileType(sf),
          period: resolvedPeriod(sf),
          year: resolvedYear(sf),
        });
        setStagedFiles((prev) =>
          prev.map((f) =>
            f.id === sf.id ? { ...f, uploadStatus: "success", result } : f,
          ),
        );
      } catch (error) {
        const isDuplicate = ApiError.isApiError(error) && error.status === 409;
        setStagedFiles((prev) =>
          prev.map((f) =>
            f.id === sf.id
              ? {
                  ...f,
                  uploadStatus: "failed",
                  validationStatus: isDuplicate
                    ? "duplicate"
                    : f.validationStatus,
                  error:
                    error instanceof Error ? error.message : "Upload failed",
                }
              : f,
          ),
        );
      }
    }

    setIsUploading(false);
    queryClient.invalidateQueries({ queryKey: ["import-logs"] });
    queryClient.invalidateQueries({ queryKey: ["students"] });
    queryClient.invalidateQueries({ queryKey: ["classes"] });
    queryClient.invalidateQueries({ queryKey: ["kpis"] });
  }, [stagedFiles, isUploading, queryClient]);

  const deleteMutation = useMutation({
    mutationFn: (batchId: string) => ingestionApi.deleteLog(batchId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["import-logs"] });
      queryClient.invalidateQueries({ queryKey: ["students"] });
      queryClient.invalidateQueries({ queryKey: ["classes"] });
      queryClient.invalidateQueries({ queryKey: ["kpis"] });
      setDeleteConfirmOpen(false);
      setBatchToDelete(null);
    },
  });

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (e.dataTransfer.files?.length)
        addFiles(Array.from(e.dataTransfer.files));
    },
    [addFiles],
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.length) {
        addFiles(Array.from(e.target.files));
        e.target.value = "";
      }
    },
    [addFiles],
  );

  const handleGenerateDebugData = useCallback(async () => {
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
    <div className="space-y-4">
      <Helmet>
        <title>{`${t("title")} | ${tc("appName")}`}</title>
      </Helmet>

      <div>
        <h1 className="text-2xl font-bold">{t("title")}</h1>
        <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>

      {/* Drop Zone */}
      <Card
        className={`border-2 border-dashed transition-colors ${
          dragActive
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50"
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <CardContent className="p-6">
          <div className="flex flex-col items-center text-center py-6">
            <Upload className="size-10 text-muted-foreground mb-3" />
            <p className="text-base font-medium mb-1">
              {t("dropzone.dragHere")}
            </p>
            <p className="text-sm text-muted-foreground mb-3">
              {t("dropzone.orClick")}
            </p>
            <input
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={handleFileSelect}
              className="hidden"
              id="file-upload"
              multiple
            />
            <label htmlFor="file-upload">
              <Button asChild size="sm">
                <span>{t("dropzone.button")}</span>
              </Button>
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Debug Data Generator */}
      {enableDebug && (
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
                  <label className="text-xs font-medium text-yellow-800">
                    {t("debug.studentsLabel")}
                  </label>
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
                    className="w-28 h-8 bg-white"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-yellow-800">
                    {t("debug.startYearLabel")}
                  </label>
                  <Select
                    value={String(debugStartYear)}
                    onValueChange={(v) => setDebugStartYear(Number(v))}
                  >
                    <SelectTrigger className="w-32 h-8 bg-white">
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
                  <label className="text-xs font-medium text-yellow-800">
                    {t("debug.endYearLabel")}
                  </label>
                  <Select
                    value={String(debugEndYear)}
                    onValueChange={(v) => setDebugEndYear(Number(v))}
                  >
                    <SelectTrigger className="w-32 h-8 bg-white">
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
                  onClick={handleGenerateDebugData}
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
      )}

      {/* Staged Queue */}
      {stagedFiles.length > 0 && (
        <div className="space-y-3">
          <div>
            <h2 className="text-base font-semibold">
              {t("staging.title")} ({stagedFiles.length})
            </h2>
            <BatchSummary files={stagedFiles} />
          </div>
          <StagedUploadToolbar
            files={stagedFiles}
            onUpload={executeUpload}
            onClearAll={clearAll}
            onBulkApply={bulkApply}
            isUploading={isUploading}
          />
          <StagedUploadTable
            files={stagedFiles}
            onUpdate={updateFile}
            onRemove={removeFile}
            onRetry={retryFile}
          />
        </div>
      )}

      {/* Import History */}
      <Card>
        <div className="p-4 border-b">
          <h3 className="text-base font-bold flex items-center gap-2">
            <Clock className="size-4 text-muted-foreground" />
            {t("history.title")}
          </h3>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="bg-accent/50">
              <TableHead className="text-right font-bold w-12 text-xs">
                #
              </TableHead>
              <SortableTableHead
                column="filename"
                sort={logSort}
                onSort={toggleLogSort}
                className="text-xs"
              >
                {t("history.file")}
              </SortableTableHead>
              <SortableTableHead
                column="file_type"
                sort={logSort}
                onSort={toggleLogSort}
                className="text-xs"
              >
                {t("history.type")}
              </SortableTableHead>
              <SortableTableHead
                column="year"
                sort={logSort}
                onSort={toggleLogSort}
                className="text-xs"
              >
                {t("history.year")}
              </SortableTableHead>
              <SortableTableHead
                column="period"
                sort={logSort}
                onSort={toggleLogSort}
                className="text-xs"
              >
                {t("history.period")}
              </SortableTableHead>
              <SortableTableHead
                column="rows_imported"
                sort={logSort}
                onSort={toggleLogSort}
                className="text-xs"
              >
                {t("history.rows")}
              </SortableTableHead>
              <SortableTableHead
                column="created_at"
                sort={logSort}
                onSort={toggleLogSort}
                className="text-xs"
              >
                {t("history.date")}
              </SortableTableHead>
              <TableHead className="text-right font-bold text-xs">
                {t("history.status")}
              </TableHead>
              <TableHead className="text-right font-bold w-12 text-xs">
                {t("history.actions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {logsLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 9 }).map((__, j) => (
                    <TableCell key={j} className="py-2">
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : logs?.items?.length ? (
              logs.items.map((log, index) => (
                <TableRow key={log.batch_id}>
                  <TableCell className="text-muted-foreground text-xs py-2">
                    {(logPage - 1) * logPageSize + index + 1}
                  </TableCell>
                  <TableCell className="font-medium text-sm py-2">
                    {log.filename}
                  </TableCell>
                  <TableCell className="py-2">
                    <Badge variant="outline" className="text-xs">
                      {log.file_type === "grades"
                        ? t("fileType.grades")
                        : t("fileType.events")}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm py-2" dir="ltr">
                    {formatHebrewYear(log.year)}
                  </TableCell>
                  <TableCell className="text-sm py-2">{log.period}</TableCell>
                  <TableCell className="text-sm py-2">
                    {log.rows_imported}
                    {log.rows_failed > 0 && (
                      <span className="text-red-600 mr-1 text-xs">
                        {t("history.failedRows", { count: log.rows_failed })}
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs py-2">
                    {new Date(log.created_at).toLocaleDateString("he-IL")}
                  </TableCell>
                  <TableCell className="py-2">
                    {log.rows_failed === 0 ? (
                      <Badge className="bg-green-100 text-green-700 text-xs">
                        {t("history.success")}
                      </Badge>
                    ) : (
                      <Badge className="bg-yellow-100 text-yellow-700 text-xs">
                        {t("history.partial")}
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="py-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0"
                      onClick={() => {
                        setBatchToDelete(log.batch_id);
                        setDeleteConfirmOpen(true);
                      }}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="size-4 text-red-600" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={9}
                  className="text-center text-muted-foreground py-8 text-sm"
                >
                  {t("history.noHistory")}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <TablePagination
          page={logPage}
          totalPages={Math.ceil((logs?.total || 0) / logPageSize)}
          onPageChange={setLogPage}
        />
      </Card>

      {/* Delete Confirmation */}
      <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("delete.title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("delete.description")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>
              {t("delete.cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() =>
                batchToDelete && deleteMutation.mutate(batchToDelete)
              }
              disabled={deleteMutation.isPending}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleteMutation.isPending
                ? t("delete.deleting")
                : t("delete.confirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
