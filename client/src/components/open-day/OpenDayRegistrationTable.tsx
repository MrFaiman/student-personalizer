import { useTranslation } from "react-i18next";
import { Search } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { TablePagination } from "@/components/TablePagination";
import type { OpenDayRegistrationListResponse, OpenDayStats } from "@/lib/types";
import { useAppForm } from "@/lib/form";
import { useEffect } from "react";

interface OpenDayRegistrationTableProps {
    registrations?: OpenDayRegistrationListResponse;
    regsLoading: boolean;
    page: number;
    defaultPageSize: number;
    setPage: (p: number) => void;
    searchInput: string;
    setSearchInput: (s: string) => void;
    handleSearch: () => void;
    selectedTrack: string;
    handleTrackChange: (t: string) => void;
    selectedGrade: string;
    handleGradeChange: (g: string) => void;
    stats?: OpenDayStats;
}

export function OpenDayRegistrationTable({
    registrations,
    regsLoading,
    page,
    defaultPageSize,
    setPage,
    searchInput,
    setSearchInput,
    handleSearch,
    selectedTrack,
    handleTrackChange,
    selectedGrade,
    handleGradeChange,
    stats,
}: OpenDayRegistrationTableProps) {
    const { t } = useTranslation("openDay");

    const trackOptions = stats ? Object.keys(stats.by_track) : [];
    const gradeOptions = stats ? Object.keys(stats.by_grade) : [];
    const totalPages = Math.ceil((registrations?.total ?? 0) / defaultPageSize);

    const form = useAppForm({
        defaultValues: {
            searchInput: searchInput,
            track: selectedTrack,
            grade: selectedGrade,
        },
    });

    useEffect(() => {
        form.setFieldValue("searchInput", searchInput);
        form.setFieldValue("track", selectedTrack);
        form.setFieldValue("grade", selectedGrade);
    }, [searchInput, selectedTrack, selectedGrade, form]);

    return (
        <Card>
            <div className="p-4 border-b flex flex-col md:flex-row gap-3">
                <div className="flex gap-2 flex-1">
                    <form.Field name="searchInput">
                        {(field) => (
                            <Input
                                placeholder={t("filters.searchPlaceholder")}
                                value={field.state.value}
                                onChange={(e) => {
                                    field.handleChange(e.target.value);
                                    setSearchInput(e.target.value);
                                }}
                                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                                className="h-9"
                            />
                        )}
                    </form.Field>
                    <Button size="sm" variant="outline" onClick={handleSearch} className="shrink-0">
                        <Search className="size-4" />
                    </Button>
                </div>
                <div className="flex gap-2">
                    <form.Field name="track">
                        {(field) => (
                            <Select
                                value={field.state.value}
                                onValueChange={(v) => {
                                    field.handleChange(v as typeof field.state.value);
                                    handleTrackChange(v);
                                }}
                                dir="rtl"
                            >
                                <SelectTrigger className="h-9 w-44">
                                    <SelectValue placeholder={t("filters.allTracks")} />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__all__">{t("filters.allTracks")}</SelectItem>
                                    {trackOptions.map((track) => (
                                        <SelectItem key={track} value={track}>
                                            {track} ({stats?.by_track[track]})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        )}
                    </form.Field>
                    <form.Field name="grade">
                        {(field) => (
                            <Select
                                value={field.state.value}
                                onValueChange={(v) => {
                                    field.handleChange(v as typeof field.state.value);
                                    handleGradeChange(v);
                                }}
                                dir="rtl"
                            >
                                <SelectTrigger className="h-9 w-36">
                                    <SelectValue placeholder={t("filters.allGrades")} />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__all__">{t("filters.allGrades")}</SelectItem>
                                    {gradeOptions.map((grade) => (
                                        <SelectItem key={grade} value={grade}>
                                            {grade} ({stats?.by_grade[grade]})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        )}
                    </form.Field>
                </div>
            </div>

            <div className="overflow-x-auto">
                <Table>
                    <TableHeader>
                        <TableRow className="bg-accent/50">
                            <TableHead className="text-right font-bold text-xs w-10">#</TableHead>
                            <TableHead className="text-right font-bold text-xs">{t("table.firstName")}</TableHead>
                            <TableHead className="text-right font-bold text-xs">{t("table.lastName")}</TableHead>
                            <TableHead className="text-right font-bold text-xs">{t("table.studentId")}</TableHead>
                            <TableHead className="text-right font-bold text-xs">{t("table.nextGrade")}</TableHead>
                            <TableHead className="text-right font-bold text-xs">{t("table.interestedTrack")}</TableHead>
                            <TableHead className="text-right font-bold text-xs">{t("table.currentSchool")}</TableHead>
                            <TableHead className="text-right font-bold text-xs">{t("table.parentName")}</TableHead>
                            <TableHead className="text-right font-bold text-xs">{t("table.phone")}</TableHead>
                            <TableHead className="text-right font-bold text-xs">{t("table.referralSource")}</TableHead>
                            <TableHead className="text-right font-bold text-xs">{t("table.submittedAt")}</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {regsLoading ? (
                            Array.from({ length: 5 }).map((_, i) => (
                                <TableRow key={i}>
                                    {Array.from({ length: 11 }).map((_, j) => (
                                        <TableCell key={j} className="py-2">
                                            <Skeleton className="h-4 w-full" />
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        ) : registrations?.items.length ? (
                            registrations.items.map((reg, index) => (
                                <TableRow key={reg.id}>
                                    <TableCell className="text-muted-foreground text-xs py-2">
                                        {(page - 1) * defaultPageSize + index + 1}
                                    </TableCell>
                                    <TableCell className="font-medium text-sm py-2">{reg.first_name}</TableCell>
                                    <TableCell className="text-sm py-2">{reg.last_name}</TableCell>
                                    <TableCell className="text-sm py-2 font-mono">{reg.student_id ?? "—"}</TableCell>
                                    <TableCell className="py-2">
                                        {reg.next_grade && (
                                            <Badge variant="outline" className="text-xs">{reg.next_grade}</Badge>
                                        )}
                                    </TableCell>
                                    <TableCell className="text-sm py-2">{reg.interested_track ?? "—"}</TableCell>
                                    <TableCell className="text-sm py-2 max-w-32 truncate" title={reg.current_school ?? ""}>
                                        {reg.current_school ?? "—"}
                                    </TableCell>
                                    <TableCell className="text-sm py-2">{reg.parent_name ?? "—"}</TableCell>
                                    <TableCell className="text-sm py-2 font-mono">{reg.phone ? reg.phone.replace(/^(\d{3})(\d{3})(\d{4})$/, "$1-$2-$3") : "—"}</TableCell>
                                    <TableCell className="text-sm py-2 max-w-32 truncate" title={reg.referral_source ?? ""}>
                                        {reg.referral_source ?? "—"}
                                    </TableCell>
                                    <TableCell className="text-muted-foreground text-xs py-2">
                                        {reg.submitted_at
                                            ? new Date(reg.submitted_at).toLocaleDateString("he-IL")
                                            : "—"}
                                    </TableCell>
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell colSpan={11} className="text-center text-muted-foreground py-8 text-sm">
                                    {t("noData")}
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>

            <TablePagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </Card>
    );
}
