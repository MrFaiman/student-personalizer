import { createFileRoute } from "@tanstack/react-router";
import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import { useState, useCallback } from "react";
import { Helmet } from "react-helmet-async";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { useTranslation } from "react-i18next";

import { ingestionApi } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import { useConfigStore } from "@/lib/config-store";
import { useTableSort } from "@/hooks/useTableSort";
import {
  type StagedFile,
  type FileTypeValue,
  createStagedFile,
  revalidateAll,
  resolvedFileType,
  resolvedPeriod,
  resolvedYear,
} from "@/lib/upload-detect";
import { DebugDataGenerator } from "@/components/upload/DebugDataGenerator";
import { DropZone } from "@/components/upload/DropZone";
import { ImportHistory } from "@/components/upload/ImportHistory";
import { DeleteImportDialog } from "@/components/upload/DeleteImportDialog";
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

  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [batchToDelete, setBatchToDelete] = useState<string | null>(null);

  const defaultPageSize = useConfigStore((s) => s.defaultPageSize);
  const enableDebug = useConfigStore((s) => s.enableDebug);
  const [logPage, setLogPage] = useState(1);
  const logPageSize = defaultPageSize;
  const { sort: logSort, toggleSort: toggleLogSort } = useTableSort<string>();

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

  return (
    <div className="space-y-4">
      <Helmet>
        <title>{`${t("title")} | ${tc("appName")}`}</title>
      </Helmet>

      <div>
        <h1 className="text-2xl font-bold">{t("title")}</h1>
        <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>

      {enableDebug && <DebugDataGenerator />}

      <DropZone onFiles={addFiles} />

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

      <ImportHistory
        logs={logs}
        isLoading={logsLoading}
        page={logPage}
        pageSize={logPageSize}
        onPageChange={setLogPage}
        sort={logSort}
        onSort={toggleLogSort}
        onDelete={(batchId) => {
          setBatchToDelete(batchId);
          setDeleteConfirmOpen(true);
        }}
        isDeleting={deleteMutation.isPending}
      />

      <DeleteImportDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        onConfirm={() => batchToDelete && deleteMutation.mutate(batchToDelete)}
        isPending={deleteMutation.isPending}
      />
    </div>
  );
}
