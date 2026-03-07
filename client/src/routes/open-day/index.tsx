import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { useState, useCallback } from "react";
import { Helmet } from "react-helmet-async";
import { RotateCcw } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
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
import { openDayApi } from "@/lib/api";
import { useConfigStore } from "@/lib/config-store";
import type { OpenDayUploadResponse } from "@/lib/types";

import { OpenDayStatsCards } from "@/components/open-day/OpenDayStatsCards";
import { OpenDayCharts } from "@/components/open-day/OpenDayCharts";
import { OpenDayRegistrationTable } from "@/components/open-day/OpenDayRegistrationTable";
import { OpenDayUploadHistory } from "@/components/open-day/OpenDayUploadHistory";
import { OpenDayUploadZone } from "@/components/open-day/OpenDayUploadZone";

export const Route = createFileRoute("/open-day/")({
    component: OpenDayPage,
});

function OpenDayPage() {
    const { t } = useTranslation("openDay");
    const { t: tc } = useTranslation();
    const queryClient = useQueryClient();
    const defaultPageSize = useConfigStore((s) => s.defaultPageSize);

    const [dragActive, setDragActive] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadResult, setUploadResult] = useState<{ response?: OpenDayUploadResponse; error?: string } | null>(null);

    const [search, setSearch] = useState("");
    const [searchInput, setSearchInput] = useState("");
    const [selectedTrack, setSelectedTrack] = useState("__all__");
    const [selectedGrade, setSelectedGrade] = useState("__all__");
    const [page, setPage] = useState(1);

    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
    const [importToDelete, setImportToDelete] = useState<number | null>(null);
    const [resetConfirmOpen, setResetConfirmOpen] = useState(false);

    const { data: stats, isLoading: statsLoading } = useQuery({
        queryKey: ["open-day-stats"],
        queryFn: openDayApi.getStats,
    });

    const { data: registrations, isLoading: regsLoading } = useQuery({
        queryKey: ["open-day-registrations", page, search, selectedTrack, selectedGrade],
        queryFn: () =>
            openDayApi.getRegistrations({
                page,
                page_size: defaultPageSize,
                search: search || undefined,
                track: selectedTrack !== "__all__" ? selectedTrack : undefined,
                grade: selectedGrade !== "__all__" ? selectedGrade : undefined,
            }),
        placeholderData: keepPreviousData,
    });

    const { data: imports, isLoading: importsLoading } = useQuery({
        queryKey: ["open-day-imports"],
        queryFn: openDayApi.getImports,
    });

    const resetMutation = useMutation({
        mutationFn: openDayApi.resetAll,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["open-day-registrations"] });
            queryClient.invalidateQueries({ queryKey: ["open-day-stats"] });
            queryClient.invalidateQueries({ queryKey: ["open-day-imports"] });
            setResetConfirmOpen(false);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: (importId: number) => openDayApi.deleteImport(importId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["open-day-registrations"] });
            queryClient.invalidateQueries({ queryKey: ["open-day-stats"] });
            queryClient.invalidateQueries({ queryKey: ["open-day-imports"] });
            setDeleteConfirmOpen(false);
            setImportToDelete(null);
        },
    });

    const uploadFile = useCallback(
        async (file: File) => {
            setUploading(true);
            setUploadResult(null);
            try {
                const result = await openDayApi.upload(file);
                setUploadResult({ response: result });
                queryClient.invalidateQueries({ queryKey: ["open-day-registrations"] });
                queryClient.invalidateQueries({ queryKey: ["open-day-stats"] });
                queryClient.invalidateQueries({ queryKey: ["open-day-imports"] });
            } catch (error) {
                setUploadResult({
                    error: error instanceof Error ? error.message : "Upload failed",
                });
            } finally {
                setUploading(false);
            }
        },
        [queryClient]
    );

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
        else if (e.type === "dragleave") setDragActive(false);
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            e.stopPropagation();
            setDragActive(false);
            const file = e.dataTransfer.files?.[0];
            if (file) uploadFile(file);
        },
        [uploadFile]
    );

    const handleFileSelect = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const file = e.target.files?.[0];
            if (file) uploadFile(file);
            e.target.value = "";
        },
        [uploadFile]
    );

    const handleSearch = useCallback(() => {
        setSearch(searchInput);
        setPage(1);
    }, [searchInput]);

    const handleTrackChange = (val: string) => {
        setSelectedTrack(val);
        setPage(1);
    };

    const handleGradeChange = (val: string) => {
        setSelectedGrade(val);
        setPage(1);
    };



    const hasData = !statsLoading && (stats?.total ?? 0) > 0;
    const isEmpty = !statsLoading && (stats?.total ?? 0) === 0;

    return (
        <div className="space-y-4">
            <Helmet>
                <title>{`${t("title")} | ${tc("appName")}`}</title>
            </Helmet>

            {isEmpty ? (
                <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
                    <div className="text-center">
                        <h1 className="text-2xl font-bold">{t("title")}</h1>
                        <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
                    </div>
                    <OpenDayUploadZone
                        dragActive={dragActive}
                        handleDrag={handleDrag}
                        handleDrop={handleDrop}
                        uploading={uploading}
                        uploadResult={uploadResult}
                        handleFileSelect={handleFileSelect}
                    />
                </div>
            ) : (
                <>
                    {/* Header */}
                    <div className="flex items-start justify-between gap-4">
                        <div>
                            <h1 className="text-2xl font-bold">{t("title")}</h1>
                            <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
                        </div>
                        <Button
                            variant="outline"
                            size="sm"
                            className="shrink-0 text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700"
                            onClick={() => setResetConfirmOpen(true)}
                        >
                            <RotateCcw className="size-4 me-1.5" />
                            {t("reset.button")}
                        </Button>
                    </div>

                    <OpenDayStatsCards stats={stats} statsLoading={statsLoading} imports={imports} />

                    {hasData && stats && <OpenDayCharts stats={stats} />}

                    <OpenDayRegistrationTable
                        registrations={registrations}
                        regsLoading={regsLoading}
                        page={page}
                        defaultPageSize={defaultPageSize}
                        setPage={setPage}
                        searchInput={searchInput}
                        setSearchInput={setSearchInput}
                        handleSearch={handleSearch}
                        selectedTrack={selectedTrack}
                        handleTrackChange={handleTrackChange}
                        selectedGrade={selectedGrade}
                        handleGradeChange={handleGradeChange}
                        stats={stats}
                    />

                    <OpenDayUploadHistory
                        imports={imports}
                        importsLoading={importsLoading}
                        onDeleteInitiated={(id) => {
                            setImportToDelete(id);
                            setDeleteConfirmOpen(true);
                        }}
                        isDeleting={deleteMutation.isPending}
                    />
                </>
            )}

            {/* Reset Confirmation */}
            <AlertDialog open={resetConfirmOpen} onOpenChange={setResetConfirmOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>{t("reset.title")}</AlertDialogTitle>
                        <AlertDialogDescription>{t("reset.description")}</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={resetMutation.isPending}>{t("reset.cancel")}</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => resetMutation.mutate()}
                            disabled={resetMutation.isPending}
                            className="bg-red-600 hover:bg-red-700"
                        >
                            {resetMutation.isPending ? t("reset.resetting") : t("reset.confirm")}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Delete Confirmation */}
            <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>{t("delete.title")}</AlertDialogTitle>
                        <AlertDialogDescription>{t("delete.description")}</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={deleteMutation.isPending}>{t("delete.cancel")}</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => importToDelete !== null && deleteMutation.mutate(importToDelete)}
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
