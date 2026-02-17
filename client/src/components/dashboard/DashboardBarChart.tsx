import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    Rectangle,
} from "recharts";
import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CLASS_COLORS } from "@/lib/utils";
import { TOOLTIP_STYLE } from "@/lib/chart-styles";

interface DashboardBarChartProps {
    title: string;
    subtitle: string;
    highlightValue: string;
    highlightLabel: string;
    isLoading: boolean;
    data: Record<string, unknown>[];
    dataKey: string;
    tooltipLabel: string;
    yDomain?: [number, number];
    formatTooltip?: (value: number) => string;
}

export function DashboardBarChart({
    title,
    subtitle,
    highlightValue,
    highlightLabel,
    isLoading,
    data,
    dataKey,
    tooltipLabel,
    yDomain,
    formatTooltip,
}: DashboardBarChartProps) {
    const { t } = useTranslation();

    return (
        <Card className="shadow-sm">
            <CardContent className="p-8">
                <div className="flex flex-col gap-6">
                    <div>
                        <h3 className="text-lg font-bold">{title}</h3>
                        <p className="text-muted-foreground text-sm">{subtitle}</p>
                    </div>
                    <div className="flex items-baseline gap-2">
                        {isLoading ? (
                            <Skeleton className="h-10 w-24" />
                        ) : (
                            <>
                                <p className="text-4xl font-bold tabular-nums">{highlightValue}</p>
                                <p className="text-muted-foreground text-base">{highlightLabel}</p>
                            </>
                        )}
                    </div>
                    <div className="h-[30vh]">
                        {isLoading ? (
                            <Skeleton className="h-full w-full" />
                        ) : data.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={data} layout="horizontal">
                                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                                    <YAxis domain={yDomain} tick={{ fontSize: 12 }} />
                                    <Tooltip
                                        contentStyle={TOOLTIP_STYLE}
                                        formatter={(value) => [
                                            formatTooltip ? formatTooltip(Number(value)) : value,
                                            tooltipLabel,
                                        ]}
                                    />
                                    <Bar
                                        dataKey={dataKey}
                                        radius={[4, 4, 0, 0]}
                                        shape={(props) => (
                                            <Rectangle {...props} fill={CLASS_COLORS[props.index % CLASS_COLORS.length]} />
                                        )}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex items-center justify-center h-full text-muted-foreground">
                                {t("noData")}
                            </div>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
