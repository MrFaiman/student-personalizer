import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { useState, useCallback } from "react";
import { Helmet } from "react-helmet-async";
import {
    Upload,
    FileSpreadsheet,
    CheckCircle,
    XCircle,
    Clock,
    AlertTriangle,
    Trash2,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
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
import { ingestionApi } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import { formatHebrewYear } from "@/lib/hebrew-year";
import { useAppForm } from "@/lib/form";
import { TablePagination } from "@/components/TablePagination";
import { SortableTableHead } from "@/components/SortableTableHead";
import { useTableSort } from "@/hooks/useTableSort";
import type { ImportResponse } from "@/lib/types";
import { MAX_DISPLAYED_ERRORS } from "@/lib/constants";
import { useConfigStore } from "@/lib/config-store";

export const Route = createFileRoute("/upload")({
    component: UploadPage,
});


function UploadPage() {
    const { t } = useTranslation("upload");
    const { t: tc } = useTranslation();
    const queryClient = useQueryClient();
    const [dragActive, setDragActive] = useState(false);
    const form = useAppForm({
        defaultValues: {
            fileType: "__auto__" as "grades" | "events" | "__auto__",
            period: "Q1",
            year: "2024-2025",
        },
    });
    const [uploadResults, setUploadResults] = useState<Array<{ filename: string; result?: ImportResponse; error?: string; isDuplicate?: boolean }>>([]);
    const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number } | null>(null);
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
    const [batchToDelete, setBatchToDelete] = useState<string | null>(null);
    const defaultPageSize = useConfigStore((s) => s.defaultPageSize);
    const [logPage, setLogPage] = useState(1);
    const logPageSize = defaultPageSize;
    const { sort: logSort, toggleSort: toggleLogSort } = useTableSort<string>();

    const { data: logs, isLoading: logsLoading } = useQuery({
        queryKey: ["import-logs", logPage, logSort.column, logSort.direction],
        queryFn: () => ingestionApi.getLogs({
            page: logPage, page_size: logPageSize,
            sort_by: logSort.column || undefined, sort_order: logSort.direction,
        }),
        placeholderData: keepPreviousData,
    });

    const uploadFiles = useCallback(
        async (files: File[]) => {
            if (files.length === 0) return;

            setUploadResults([]);
            setUploadProgress({ current: 0, total: files.length });

            const results: Array<{ filename: string; result?: ImportResponse; error?: string; isDuplicate?: boolean }> = [];

            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                setUploadProgress({ current: i + 1, total: files.length });

                try {
                    const values = form.state.values;
                    const result = await ingestionApi.upload(file, {
                        file_type: values.fileType === "__auto__" ? undefined : values.fileType,
                        period: values.period || undefined,
                        year: values.year || undefined,
                    });
                    results.push({ filename: file.name, result });
                } catch (error) {
                    const isDuplicate = ApiError.isApiError(error) && error.status === 409;
                    results.push({
                        filename: file.name,
                        error: error instanceof Error ? error.message : "Upload failed",
                        isDuplicate,
                    });
                }
            }

            setUploadResults(results);
            setUploadProgress(null);

            queryClient.invalidateQueries({ queryKey: ["import-logs"] });
            queryClient.invalidateQueries({ queryKey: ["students"] });
            queryClient.invalidateQueries({ queryKey: ["classes"] });
            queryClient.invalidateQueries({ queryKey: ["kpis"] });
        },
        [form, queryClient]
    );

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

    const handleDeleteClick = (batchId: string) => {
        setBatchToDelete(batchId);
        setDeleteConfirmOpen(true);
    };

    const handleDeleteConfirm = () => {
        if (batchToDelete) {
            deleteMutation.mutate(batchToDelete);
        }
    };

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            e.stopPropagation();
            setDragActive(false);
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                const filesArray = Array.from(e.dataTransfer.files);
                uploadFiles(filesArray);
            }
        },
        [uploadFiles]
    );

    const handleFileSelect = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            if (e.target.files && e.target.files.length > 0) {
                const filesArray = Array.from(e.target.files);
                uploadFiles(filesArray);
            }
        },
        [uploadFiles]
    );

    return (
        <div className="space-y-4">
            <Helmet>
                <title>{`${t("title")} | ${tc("appName")}`}</title>
            </Helmet>
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold">{t("title")}</h1>
                <p className="text-sm text-muted-foreground">
                    {t("subtitle")}
                </p>
            </div>

            {/* Compact Upload Card */}
            <Card
                className={`border-2 border-dashed transition-colors ${dragActive
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50"
                    }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
            >
                <CardContent className="p-6">
                    {/* Upload Options Row */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
                        <form.Field name="fileType">
                            {(field) => (
                                <div>
                                    <label className="block text-xs font-medium mb-1.5">{t("fileType.label")}</label>
                                    <Select value={field.state.value} onValueChange={(v) => field.handleChange(v as typeof field.state.value)}>
                                        <SelectTrigger className="h-9">
                                            <SelectValue placeholder={t("fileType.placeholder")} />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="__auto__">{t("fileType.auto")}</SelectItem>
                                            <SelectItem value="grades">{t("fileType.grades")}</SelectItem>
                                            <SelectItem value="events">{t("fileType.events")}</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            )}
                        </form.Field>
                        <form.Field name="period">
                            {(field) => (
                                <div>
                                    <label className="block text-xs font-medium mb-1.5">{t("period.label")}</label>
                                    <Select value={field.state.value} onValueChange={(v) => field.handleChange(v as typeof field.state.value)}>
                                        <SelectTrigger className="h-9">
                                            <SelectValue placeholder={t("period.placeholder")} />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="Q1">{t("period.quarter", { number: 1 })}</SelectItem>
                                            <SelectItem value="Q2">{t("period.quarter", { number: 2 })}</SelectItem>
                                            <SelectItem value="Q3">{t("period.quarter", { number: 3 })}</SelectItem>
                                            <SelectItem value="Q4">{t("period.quarter", { number: 4 })}</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            )}
                        </form.Field>
                        <form.Field name="year">
                            {(field) => (
                                <div>
                                    <label className="block text-xs font-medium mb-1.5">{t("year.label", "שנה")}</label>
                                    <Select value={field.state.value} onValueChange={(v) => field.handleChange(v as typeof field.state.value)} dir="rtl">
                                        <SelectTrigger className="h-9">
                                            <SelectValue placeholder={t("year.placeholder", "בחר שנה")} />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {Array.from({ length: 10 }, (_, i) => 2021 + i).map((y) => {
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
                            )}
                        </form.Field>
                    </div>

                    {/* Drop Zone */}
                    <div className="flex flex-col items-center text-center py-8">
                        {uploadProgress ? (
                            <>
                                <div className="animate-pulse">
                                    <FileSpreadsheet className="size-12 text-primary mb-3" />
                                </div>
                                <p className="text-base font-medium">
                                    {t("dropzone.uploadingProgress", { current: uploadProgress.current, total: uploadProgress.total })}
                                </p>
                                <Progress className="w-48 mt-3" value={(uploadProgress.current / uploadProgress.total) * 100} />
                            </>
                        ) : (
                            <>
                                <Upload className="size-12 text-muted-foreground mb-3" />
                                <p className="text-base font-medium mb-1">{t("dropzone.dragHere")}</p>
                                <p className="text-sm text-muted-foreground mb-3">{t("dropzone.orClick")}</p>
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
                            </>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Upload Results */}
            {uploadResults.length > 0 && (
                <div className="space-y-3">
                    {uploadResults.map((item, index) => (
                        item.result ? (
                            <Card key={index} className="border-green-200 bg-green-50">
                                <CardContent className="p-4">
                                    <div className="flex items-start gap-3">
                                        <CheckCircle className="size-5 text-green-600 shrink-0 mt-0.5" />
                                        <div className="flex-1 min-w-0">
                                            <h3 className="text-base font-bold text-green-800 mb-2">
                                                {t("success.title")} - {item.filename}
                                            </h3>
                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                                <div>
                                                    <p className="text-xs text-green-700">{t("success.fileType")}</p>
                                                    <p className="font-semibold text-sm">{item.result.file_type}</p>
                                                </div>
                                                <div>
                                                    <p className="text-xs text-green-700">{t("success.rows")}</p>
                                                    <p className="font-semibold text-sm">{item.result.rows_imported}</p>
                                                </div>
                                                <div>
                                                    <p className="text-xs text-green-700">{t("success.newStudents")}</p>
                                                    <p className="font-semibold text-sm">{item.result.students_created}</p>
                                                </div>
                                                <div>
                                                    <p className="text-xs text-green-700">{t("success.newClasses")}</p>
                                                    <p className="font-semibold text-sm">{item.result.classes_created}</p>
                                                </div>
                                            </div>
                                            {item.result.rows_failed > 0 && (
                                                <div className="mt-3 p-2 bg-yellow-100 rounded">
                                                    <p className="text-sm text-yellow-800 flex items-center gap-2">
                                                        <AlertTriangle className="size-3.5" />
                                                        {t("success.partialSuccess", { count: item.result.rows_failed })}
                                                    </p>
                                                </div>
                                            )}
                                            {item.result.errors.length > 0 && (
                                                <div className="mt-3">
                                                    <p className="text-xs font-medium text-red-700 mb-1">{t("errors.title")}</p>
                                                    <ul className="text-xs text-red-600 list-disc list-inside space-y-0.5">
                                                        {item.result.errors.slice(0, MAX_DISPLAYED_ERRORS).map((err: string, i: number) => (
                                                            <li key={i}>{err}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ) : item.isDuplicate ? (
                            <Card key={index} className="border-yellow-200 bg-yellow-50">
                                <CardContent className="p-4">
                                    <div className="flex items-center gap-3">
                                        <AlertTriangle className="size-5 text-yellow-600 shrink-0" />
                                        <div className="min-w-0">
                                            <h3 className="text-base font-bold text-yellow-800">
                                                {t("errors.duplicate")} - {item.filename}
                                            </h3>
                                            <p className="text-sm text-yellow-700 mt-0.5">{item.error}</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ) : (
                            <Card key={index} className="border-red-200 bg-red-50">
                                <CardContent className="p-4">
                                    <div className="flex items-center gap-3">
                                        <XCircle className="size-5 text-red-600 shrink-0" />
                                        <div className="min-w-0">
                                            <h3 className="text-base font-bold text-red-800">
                                                {t("errors.uploadFailed")} - {item.filename}
                                            </h3>
                                            <p className="text-sm text-red-700 mt-0.5">{item.error}</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        )
                    ))}
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
                            <TableHead className="text-right font-bold w-12 text-xs">#</TableHead>
                            <SortableTableHead column="filename" sort={logSort} onSort={toggleLogSort} className="text-xs">{t("history.file")}</SortableTableHead>
                            <SortableTableHead column="file_type" sort={logSort} onSort={toggleLogSort} className="text-xs">{t("history.type")}</SortableTableHead>
                            <SortableTableHead column="year" sort={logSort} onSort={toggleLogSort} className="text-xs">{t("history.year", "שנה")}</SortableTableHead>
                            <SortableTableHead column="period" sort={logSort} onSort={toggleLogSort} className="text-xs">{t("history.period")}</SortableTableHead>
                            <SortableTableHead column="rows_imported" sort={logSort} onSort={toggleLogSort} className="text-xs">{t("history.rows")}</SortableTableHead>
                            <SortableTableHead column="created_at" sort={logSort} onSort={toggleLogSort} className="text-xs">{t("history.date")}</SortableTableHead>
                            <TableHead className="text-right font-bold text-xs">{t("history.status")}</TableHead>
                            <TableHead className="text-right font-bold w-12 text-xs">{t("history.actions")}</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {logsLoading ? (
                            Array.from({ length: 5 }).map((_, i) => (
                                <TableRow key={i}>
                                    <TableCell className="py-2"><Skeleton className="h-4 w-8" /></TableCell>
                                    <TableCell className="py-2"><Skeleton className="h-4 w-40" /></TableCell>
                                    <TableCell className="py-2"><Skeleton className="h-4 w-16" /></TableCell>
                                    <TableCell className="py-2"><Skeleton className="h-4 w-12" /></TableCell>
                                    <TableCell className="py-2"><Skeleton className="h-4 w-20" /></TableCell>
                                    <TableCell className="py-2"><Skeleton className="h-4 w-12" /></TableCell>
                                    <TableCell className="py-2"><Skeleton className="h-4 w-24" /></TableCell>
                                    <TableCell className="py-2"><Skeleton className="h-4 w-16" /></TableCell>
                                    <TableCell className="py-2"><Skeleton className="h-4 w-8" /></TableCell>
                                </TableRow>
                            ))
                        ) : logs?.items?.length ? (
                            logs.items.map((log, index) => (
                                <TableRow key={log.batch_id}>
                                    <TableCell className="text-muted-foreground text-xs py-2">{(logPage - 1) * logPageSize + index + 1}</TableCell>
                                    <TableCell className="font-medium text-sm py-2">{log.filename}</TableCell>
                                    <TableCell className="py-2">
                                        <Badge variant="outline" className="text-xs">
                                            {log.file_type === "grades" ? t("fileType.grades") : t("fileType.events")}
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="text-sm py-2" dir="ltr">{formatHebrewYear(log.year)}</TableCell>
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
                                            <Badge className="bg-green-100 text-green-700 text-xs">{t("history.success")}</Badge>
                                        ) : (
                                            <Badge className="bg-yellow-100 text-yellow-700 text-xs">{t("history.partial")}</Badge>
                                        )}
                                    </TableCell>
                                    <TableCell className="py-2">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-8 w-8 p-0"
                                            onClick={() => handleDeleteClick(log.batch_id)}
                                            disabled={deleteMutation.isPending}
                                        >
                                            <Trash2 className="size-4 text-red-600" />
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell colSpan={9} className="text-center text-muted-foreground py-8 text-sm">
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

            {/* Delete Confirmation Dialog */}
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
                            onClick={handleDeleteConfirm}
                            disabled={deleteMutation.isPending}
                            className="bg-red-600 hover:bg-red-700"
                        >
                            {deleteMutation.isPending ? t("delete.deleting") : t("delete.confirm")}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
