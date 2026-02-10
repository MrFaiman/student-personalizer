import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { useState, useCallback } from "react";
import {
	Upload,
    FileSpreadsheet,
    CheckCircle,
    XCircle,
    Clock,
    AlertTriangle,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
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
import { TablePagination } from "@/components/TablePagination";
import type { ImportResponse } from "@/lib/types";

export const Route = createFileRoute("/upload")({
    component: UploadPage,
});


function UploadPage() {
    const { t } = useTranslation("upload");
    const queryClient = useQueryClient();
    const [dragActive, setDragActive] = useState(false);
    const [fileType, setFileType] = useState<"grades" | "events" | "__auto__">("__auto__");
    const [period, setPeriod] = useState("Q1");
    const [uploadResult, setUploadResult] = useState<ImportResponse | null>(null);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [logPage, setLogPage] = useState(1);
    const logPageSize = 20;

    const { data: logs, isLoading: logsLoading } = useQuery({
        queryKey: ["import-logs", logPage],
        queryFn: () => ingestionApi.getLogs({ page: logPage, page_size: logPageSize }),
        placeholderData: keepPreviousData,
    });

    const uploadMutation = useMutation({
        mutationFn: (file: File) =>
            ingestionApi.upload(file, {
                file_type: fileType === "__auto__" ? undefined : fileType,
                period: period || undefined,
            }),
        onSuccess: (result) => {
            setUploadResult(result);
            setUploadError(null);
            queryClient.invalidateQueries({ queryKey: ["import-logs"] });
            queryClient.invalidateQueries({ queryKey: ["students"] });
            queryClient.invalidateQueries({ queryKey: ["classes"] });
            queryClient.invalidateQueries({ queryKey: ["kpis"] });
        },
        onError: (error: Error) => {
            setUploadError(error.message);
            setUploadResult(null);
        },
    });

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
            if (e.dataTransfer.files?.[0]) {
                uploadMutation.mutate(e.dataTransfer.files[0]);
            }
        },
        [uploadMutation]
    );

    const handleFileSelect = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            if (e.target.files?.[0]) {
                uploadMutation.mutate(e.target.files[0]);
            }
        },
        [uploadMutation]
    );

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold">{t("title")}</h1>
                <p className="text-muted-foreground">
                    {t("subtitle")}
                </p>
            </div>

            {/* Upload Options */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                    <CardContent className="p-4">
                        <label className="block text-sm font-medium mb-2">{t("fileType.label")}</label>
                        <Select value={fileType} onValueChange={(v) => setFileType(v as typeof fileType)}>
                            <SelectTrigger>
                                <SelectValue placeholder={t("fileType.placeholder")} />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="__auto__">{t("fileType.auto")}</SelectItem>
                                <SelectItem value="grades">{t("fileType.grades")}</SelectItem>
                                <SelectItem value="events">{t("fileType.events")}</SelectItem>
                            </SelectContent>
                        </Select>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4">
                        <label className="block text-sm font-medium mb-2">{t("period.label")}</label>
                        <Select value={period} onValueChange={setPeriod}>
                            <SelectTrigger>
                                <SelectValue placeholder={t("period.placeholder")} />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="Q1">{t("period.quarter", { number: 1 })}</SelectItem>
                                <SelectItem value="Q2">{t("period.quarter", { number: 2 })}</SelectItem>
                                <SelectItem value="Q3">{t("period.quarter", { number: 3 })}</SelectItem>
                                <SelectItem value="Q4">{t("period.quarter", { number: 4 })}</SelectItem>
                            </SelectContent>
                        </Select>
                    </CardContent>
                </Card>
            </div>

            {/* Drop Zone */}
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
                <CardContent className="p-12">
                    <div className="flex flex-col items-center text-center">
                        {uploadMutation.isPending ? (
                            <>
                                <div className="animate-pulse">
                                    <FileSpreadsheet className="size-16 text-primary mb-4" />
                                </div>
                                <p className="text-lg font-medium">{t("dropzone.uploading")}</p>
                                <Progress className="w-64 mt-4" value={undefined} />
                            </>
                        ) : (
                            <>
                                <Upload className="size-16 text-muted-foreground mb-4" />
                                <p className="text-lg font-medium mb-2">{t("dropzone.dragHere")}</p>
                                <p className="text-muted-foreground mb-4">{t("dropzone.orClick")}</p>
                                <input
                                    type="file"
                                    accept=".xlsx,.xls,.csv"
                                    onChange={handleFileSelect}
                                    className="hidden"
                                    id="file-upload"
                                />
                                <label htmlFor="file-upload">
                                    <Button asChild>
                                        <span>{t("dropzone.button")}</span>
                                    </Button>
                                </label>
                            </>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Upload Result */}
            {uploadResult && (
                <Card className="border-green-200 bg-green-50">
                    <CardContent className="p-6">
                        <div className="flex items-start gap-4">
                            <CheckCircle className="size-8 text-green-600 shrink-0" />
                            <div className="flex-1">
                                <h3 className="text-lg font-bold text-green-800">{t("success.title")}</h3>
                                <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <div>
                                        <p className="text-sm text-green-700">{t("success.fileType")}</p>
                                        <p className="font-semibold">{uploadResult.file_type}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-green-700">{t("success.rows")}</p>
                                        <p className="font-semibold">{uploadResult.rows_imported}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-green-700">{t("success.newStudents")}</p>
                                        <p className="font-semibold">{uploadResult.students_created}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-green-700">{t("success.newClasses")}</p>
                                        <p className="font-semibold">{uploadResult.classes_created}</p>
                                    </div>
                                </div>
                                {uploadResult.rows_failed > 0 && (
                                    <div className="mt-4 p-3 bg-yellow-100 rounded-lg">
                                        <p className="text-yellow-800 flex items-center gap-2">
                                            <AlertTriangle className="size-4" />
                                            {t("success.partialSuccess", { count: uploadResult.rows_failed })}
                                        </p>
                                    </div>
                                )}
                                {uploadResult.errors.length > 0 && (
                                    <div className="mt-4">
                                        <p className="text-sm font-medium text-red-700 mb-2">{t("errors.title")}</p>
                                        <ul className="text-sm text-red-600 list-disc list-inside">
                                            {uploadResult.errors.slice(0, 5).map((err, i) => (
                                                <li key={i}>{err}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Upload Error */}
            {uploadError && (
                <Card className="border-red-200 bg-red-50">
                    <CardContent className="p-6">
                        <div className="flex items-center gap-4">
                            <XCircle className="size-8 text-red-600 shrink-0" />
                            <div>
                                <h3 className="text-lg font-bold text-red-800">{t("errors.uploadFailed")}</h3>
                                <p className="text-red-700 mt-1">{uploadError}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Import History */}
            <Card>
                <div className="p-6 border-b">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                        <Clock className="size-5 text-muted-foreground" />
                        {t("history.title")}
                    </h3>
                </div>
                <Table>
                    <TableHeader>
                        <TableRow className="bg-accent/50">
                            <TableHead className="text-right font-bold w-12">#</TableHead>
                            <TableHead className="text-right font-bold">{t("history.file")}</TableHead>
                            <TableHead className="text-right font-bold">{t("history.type")}</TableHead>
                            <TableHead className="text-right font-bold">{t("history.period")}</TableHead>
                            <TableHead className="text-right font-bold">{t("history.rows")}</TableHead>
                            <TableHead className="text-right font-bold">{t("history.date")}</TableHead>
                            <TableHead className="text-right font-bold">{t("history.status")}</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {logsLoading ? (
                            Array.from({ length: 5 }).map((_, i) => (
                                <TableRow key={i}>
                                    <TableCell><Skeleton className="h-5 w-8" /></TableCell>
                                    <TableCell><Skeleton className="h-5 w-40" /></TableCell>
                                    <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                                    <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                                    <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                                </TableRow>
                            ))
                        ) : logs?.items?.length ? (
                            logs.items.map((log, index) => (
                                <TableRow key={log.batch_id}>
                                    <TableCell className="text-muted-foreground">{(logPage - 1) * logPageSize + index + 1}</TableCell>
                                    <TableCell className="font-medium">{log.filename}</TableCell>
                                    <TableCell>
                                        <Badge variant="outline">
                                            {log.file_type === "grades" ? t("fileType.grades") : t("fileType.events")}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>{log.period}</TableCell>
                                    <TableCell>
                                        {log.rows_imported}
                                        {log.rows_failed > 0 && (
                                            <span className="text-red-600 mr-1">
                                                {t("history.failedRows", { count: log.rows_failed })}
                                            </span>
                                        )}
                                    </TableCell>
                                    <TableCell className="text-muted-foreground">
                                        {new Date(log.created_at).toLocaleDateString("he-IL")}
                                    </TableCell>
                                    <TableCell>
                                        {log.rows_failed === 0 ? (
                                            <Badge className="bg-green-100 text-green-700">{t("history.success")}</Badge>
                                        ) : (
                                            <Badge className="bg-yellow-100 text-yellow-700">{t("history.partial")}</Badge>
                                        )}
                                    </TableCell>
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell colSpan={7} className="text-center text-muted-foreground py-12">
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
        </div>
    );
}
