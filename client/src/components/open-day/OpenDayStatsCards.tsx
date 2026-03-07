import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Users, BookOpen, CalendarDays, FileSpreadsheet } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { OpenDayStats, OpenDayImportListResponse } from "@/lib/types";

function StatCard({
    icon: Icon,
    label,
    value,
}: {
    icon: React.ElementType;
    label: string;
    value: string | number;
}) {
    return (
        <Card>
            <CardContent className="p-4">
                <div className="flex items-center gap-3">
                    <div className="bg-primary/10 rounded-lg p-2 shrink-0">
                        <Icon className="size-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                        <p className="text-xs text-muted-foreground truncate">{label}</p>
                        <p className="text-xl font-bold leading-tight">{value}</p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

interface OpenDayStatsCardsProps {
    statsLoading: boolean;
    stats?: OpenDayStats;
    imports?: OpenDayImportListResponse;
}

export function OpenDayStatsCards({ statsLoading, stats, imports }: OpenDayStatsCardsProps) {
    const { t } = useTranslation("openDay");

    if (statsLoading) {
        return (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Array.from({ length: 4 }).map((_, i) => (
                    <Card key={i}>
                        <CardContent className="p-4">
                            <Skeleton className="h-12 w-full" />
                        </CardContent>
                    </Card>
                ))}
            </div>
        );
    }

    const trackOptionsCount = stats ? Object.keys(stats.by_track).length : 0;
    const gradeOptionsCount = stats ? Object.keys(stats.by_grade).length : 0;

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard icon={Users} label={t("stats.total")} value={stats?.total ?? 0} />
            <StatCard icon={BookOpen} label={t("stats.tracks")} value={trackOptionsCount} />
            <StatCard icon={CalendarDays} label={t("stats.grades")} value={gradeOptionsCount} />
            <StatCard icon={FileSpreadsheet} label={t("stats.uploads")} value={imports?.total ?? 0} />
        </div>
    );
}
