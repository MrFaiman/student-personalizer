import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
    PieChart, Pie, Cell, BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { ChevronDown, ChevronUp, PieChart as PieChartIcon, BarChart2 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, ChartLegend, ChartLegendContent, type ChartConfig } from "@/components/ui/chart";
import { getBarColor } from "@/lib/utils";
import type { OpenDayStats } from "@/lib/types";

interface OpenDayChartsProps {
    stats: OpenDayStats;
}

export function OpenDayCharts({ stats }: OpenDayChartsProps) {
    const { t } = useTranslation("openDay");
    const [chartType, setChartType] = useState<"pie" | "bar">("pie");
    const [chartsCollapsed, setChartsCollapsed] = useState(false);

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between" dir="rtl">
                <button
                    onClick={() => setChartsCollapsed((c) => !c)}
                    className="flex items-center gap-1.5 text-sm font-semibold hover:text-primary transition-colors"
                >
                    {chartsCollapsed ? <ChevronDown className="size-4" /> : <ChevronUp className="size-4" />}
                    {t("charts.title")}
                </button>
                <div className="flex border rounded-md overflow-hidden">
                    <button
                        onClick={() => setChartType("pie")}
                        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors ${chartType === "pie" ? "bg-primary text-primary-foreground" : "hover:bg-accent"}`}
                    >
                        <PieChartIcon className="size-3.5" />
                        {t("charts.pie")}
                    </button>
                    <button
                        onClick={() => setChartType("bar")}
                        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors ${chartType === "bar" ? "bg-primary text-primary-foreground" : "hover:bg-accent"}`}
                    >
                        <BarChart2 className="size-3.5" />
                        {t("charts.bar")}
                    </button>
                </div>
            </div>

            {!chartsCollapsed && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[
                        { title: t("charts.byGrade"), data: stats.by_grade },
                        { title: t("charts.byTrack"), data: stats.by_track },
                    ].map(({ title, data }) => {
                        const chartData = Object.entries(data).map(([name, value]) => ({ name, value }));
                        const config = Object.fromEntries(chartData.map((d, i) => [d.name, { label: d.name, color: getBarColor(i) }])) satisfies ChartConfig;
                        return (
                            <Card key={title}>
                                <CardContent className="p-4">
                                    <p className="text-sm font-semibold mb-3">{title}</p>
                                    <ChartContainer config={config} className="h-[260px] w-full">
                                        {chartType === "pie" ? (
                                            <PieChart>
                                                <Pie
                                                    data={chartData}
                                                    cx="50%"
                                                    cy="50%"
                                                    innerRadius={55}
                                                    outerRadius={90}
                                                    paddingAngle={2}
                                                    dataKey="value"
                                                    nameKey="name"
                                                >
                                                    {chartData.map((_, i) => (
                                                        <Cell key={i} fill={getBarColor(i)} />
                                                    ))}
                                                </Pie>
                                                <ChartTooltip content={(props) => <ChartTooltipContent {...props} nameKey="name" />} />
                                                <ChartLegend content={(props) => <ChartLegendContent {...props} nameKey="name" />} />
                                            </PieChart>
                                        ) : (
                                            <BarChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
                                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                                                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                                                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                                                <ChartTooltip content={(props) => <ChartTooltipContent {...props} />} />
                                                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                                                    {chartData.map((_, i) => (
                                                        <Cell key={i} fill={getBarColor(i)} />
                                                    ))}
                                                </Bar>
                                            </BarChart>
                                        )}
                                    </ChartContainer>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            )}

            {!chartsCollapsed && (() => {
                const schoolData = Object.entries(stats.by_school).map(([name, value]) => ({ name, value }));
                const timelineData = Object.entries(stats.by_date).map(([date, value]) => ({ date, value }));
                const allTracks = Array.from(new Set(Object.values(stats.track_by_grade).flatMap(Object.keys)));
                const crossTabData = Object.entries(stats.track_by_grade).map(([grade, tracks]) => ({
                    grade,
                    ...Object.fromEntries(allTracks.map((tr) => [tr, tracks[tr] ?? 0])),
                }));

                return (
                    <div className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {schoolData.length > 0 && (
                                <Card>
                                    <CardContent className="p-4">
                                        <p className="text-sm font-semibold mb-3">{t("charts.bySchool")}</p>
                                        <ChartContainer config={{ value: { label: t("charts.count") } } satisfies ChartConfig} className="h-[260px] w-full">
                                            <BarChart data={schoolData} layout="vertical" margin={{ top: 4, right: 16, left: -16, bottom: 4 }}>
                                                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
                                                <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                                                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={120} />
                                                <ChartTooltip content={(props) => <ChartTooltipContent {...props} />} />
                                                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                                                    {schoolData.map((_, i) => <Cell key={i} fill={getBarColor(i)} />)}
                                                </Bar>
                                            </BarChart>
                                        </ChartContainer>
                                    </CardContent>
                                </Card>
                            )}
                            {timelineData.length >= 2 && (
                                <Card>
                                    <CardContent className="p-4">
                                        <p className="text-sm font-semibold mb-3">{t("charts.timeline")}</p>
                                        <ChartContainer config={{ value: { label: t("charts.count"), color: getBarColor(0) } } satisfies ChartConfig} className="h-[260px] w-full">
                                            <AreaChart data={timelineData} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
                                                <defs>
                                                    <linearGradient id="timelineGradient" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="5%" stopColor={getBarColor(0)} stopOpacity={0.3} />
                                                        <stop offset="95%" stopColor={getBarColor(0)} stopOpacity={0} />
                                                    </linearGradient>
                                                </defs>
                                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                                                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(d) => new Date(d).toLocaleDateString("he-IL")} />
                                                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                                                <ChartTooltip content={(props) => <ChartTooltipContent {...props} labelFormatter={(d) => new Date(String(d)).toLocaleDateString("he-IL")} />} />
                                                <Area type="monotone" dataKey="value" stroke={getBarColor(0)} fill="url(#timelineGradient)" strokeWidth={2} name={t("charts.count")} />
                                            </AreaChart>
                                        </ChartContainer>
                                    </CardContent>
                                </Card>
                            )}
                        </div>

                        {crossTabData.length > 0 && allTracks.length > 0 && (() => {
                            const trackConfig = Object.fromEntries(allTracks.map((track, i) => [track, { label: track, color: getBarColor(i) }])) satisfies ChartConfig;
                            return (
                            <Card>
                                <CardContent className="p-4">
                                    <p className="text-sm font-semibold mb-3">{t("charts.trackByGrade")}</p>
                                    <ChartContainer config={trackConfig} className="h-[280px] w-full">
                                        <BarChart data={crossTabData} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                                            <XAxis dataKey="grade" tick={{ fontSize: 11 }} />
                                            <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                                            <ChartTooltip content={(props) => <ChartTooltipContent {...props} />} />
                                            <ChartLegend content={(props) => <ChartLegendContent {...props} />} />
                                            {allTracks.map((track, i) => (
                                                <Bar key={track} dataKey={track} fill={getBarColor(i)} radius={[4, 4, 0, 0]} stackId={undefined} />
                                            ))}
                                        </BarChart>
                                    </ChartContainer>
                                </CardContent>
                            </Card>
                            );
                        })()}
                    </div>
                );
            })()}
        </div>
    );
}
