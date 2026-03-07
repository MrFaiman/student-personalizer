import { useTranslation } from "react-i18next";
import { Clock, Trash2 } from "lucide-react";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import type { OpenDayImportListResponse } from "@/lib/types";

interface OpenDayUploadHistoryProps {
    imports?: OpenDayImportListResponse;
    importsLoading: boolean;
    onDeleteInitiated: (id: number) => void;
    isDeleting: boolean;
}

export function OpenDayUploadHistory({
    imports,
    importsLoading,
    onDeleteInitiated,
    isDeleting,
}: OpenDayUploadHistoryProps) {
    const { t } = useTranslation("openDay");

    return (
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
                        <TableHead className="text-right font-bold text-xs">{t("history.filename")}</TableHead>
                        <TableHead className="text-right font-bold text-xs">{t("history.imported")}</TableHead>
                        <TableHead className="text-right font-bold text-xs">{t("history.failed")}</TableHead>
                        <TableHead className="text-right font-bold text-xs">{t("history.date")}</TableHead>
                        <TableHead className="text-right font-bold text-xs w-12">{t("history.actions")}</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {importsLoading ? (
                        Array.from({ length: 3 }).map((_, i) => (
                            <TableRow key={i}>
                                {Array.from({ length: 5 }).map((_, j) => (
                                    <TableCell key={j} className="py-2">
                                        <Skeleton className="h-4 w-full" />
                                    </TableCell>
                                ))}
                            </TableRow>
                        ))
                    ) : imports?.items.length ? (
                        imports.items.map((imp) => (
                            <TableRow key={imp.id}>
                                <TableCell className="font-medium text-sm py-2">{imp.filename}</TableCell>
                                <TableCell className="text-sm py-2">{imp.rows_imported}</TableCell>
                                <TableCell className="py-2">
                                    {imp.rows_failed > 0 ? (
                                        <span className="text-red-600 text-xs">
                                            {t("history.failedRows", { count: imp.rows_failed })}
                                        </span>
                                    ) : (
                                        <Badge className="bg-green-100 text-green-700 text-xs">✓</Badge>
                                    )}
                                </TableCell>
                                <TableCell className="text-muted-foreground text-xs py-2">
                                    {new Date(imp.import_date).toLocaleDateString("he-IL")}
                                </TableCell>
                                <TableCell className="py-2">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 w-8 p-0"
                                        onClick={() => onDeleteInitiated(imp.id)}
                                        disabled={isDeleting}
                                    >
                                        <Trash2 className="size-4 text-red-600" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))
                    ) : (
                        <TableRow>
                            <TableCell colSpan={5} className="text-center text-muted-foreground py-8 text-sm">
                                {t("history.noHistory")}
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </Card>
    );
}
