import { useTranslation } from "react-i18next";
import { Upload, FileSpreadsheet, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { OpenDayUploadResponse } from "@/lib/types";

interface OpenDayUploadZoneProps {
    dragActive: boolean;
    uploading: boolean;
    uploadResult: { response?: OpenDayUploadResponse; error?: string } | null;
    handleDrag: (e: React.DragEvent) => void;
    handleDrop: (e: React.DragEvent) => void;
    handleFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function OpenDayUploadZone({
    dragActive,
    uploading,
    uploadResult,
    handleDrag,
    handleDrop,
    handleFileSelect,
}: OpenDayUploadZoneProps) {
    const { t } = useTranslation("openDay");

    return (
        <div className="w-full max-w-lg space-y-3">
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
                    <div className="flex flex-col items-center text-center py-8">
                        {uploading ? (
                            <>
                                <div className="animate-pulse">
                                    <FileSpreadsheet className="size-12 text-primary mb-3" />
                                </div>
                                <p className="text-base font-medium">{t("upload.uploadingProgress", { current: 1, total: 1 })}</p>
                                <Progress className="w-48 mt-3" value={undefined} />
                            </>
                        ) : (
                            <>
                                <Upload className="size-12 text-muted-foreground mb-3" />
                                <p className="text-base font-medium mb-1">{t("upload.dragHere")}</p>
                                <p className="text-sm text-muted-foreground mb-3">{t("upload.orClick")}</p>
                                <input
                                    type="file"
                                    accept=".xlsx,.xls,.csv"
                                    onChange={handleFileSelect}
                                    className="hidden"
                                    id="open-day-file-upload"
                                />
                                <label htmlFor="open-day-file-upload">
                                    <Button asChild size="sm">
                                        <span>{t("upload.button")}</span>
                                    </Button>
                                </label>
                            </>
                        )}
                    </div>
                </CardContent>
            </Card>

            {uploadResult && (
                uploadResult.response ? (
                    <Card className="border-green-200 bg-green-50">
                        <CardContent className="p-4">
                            <div className="flex items-start gap-3">
                                <CheckCircle className="size-5 text-green-600 shrink-0 mt-0.5" />
                                <div className="flex-1">
                                    <h3 className="text-base font-bold text-green-800 mb-2">{t("success.title")}</h3>
                                    <div className="flex gap-4 text-sm">
                                        <span className="text-green-700">{t("success.imported", { count: uploadResult.response.rows_imported })}</span>
                                        {uploadResult.response.rows_failed > 0 && (
                                            <span className="text-yellow-700">{t("success.failed", { count: uploadResult.response.rows_failed })}</span>
                                        )}
                                    </div>
                                    {uploadResult.response.errors.length > 0 && (
                                        <div className="mt-2">
                                            <p className="text-xs font-medium text-red-700 mb-1">{t("errors.title")}</p>
                                            <ul className="text-xs text-red-600 list-disc list-inside space-y-0.5">
                                                {uploadResult.response.errors.map((err, i) => (
                                                    <li key={i}>{err}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ) : (
                    <Card className="border-red-200 bg-red-50">
                        <CardContent className="p-4">
                            <div className="flex items-center gap-3">
                                <XCircle className="size-5 text-red-600 shrink-0" />
                                <div>
                                    <h3 className="text-base font-bold text-red-800">{t("errors.uploadFailed")}</h3>
                                    <p className="text-sm text-red-700 mt-0.5">{uploadResult.error}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                )
            )}
        </div>
    );
}
