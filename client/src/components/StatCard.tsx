import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface StatCardProps {
    icon: LucideIcon;
    iconClassName: string;
    iconBgClassName: string;
    value: React.ReactNode;
    valueClassName?: string;
    label: string;
    trend?: {
        value: number;
        label: string;
        invertColors?: boolean;
    };
}

export function StatCard({
    icon: Icon,
    iconClassName,
    iconBgClassName,
    value,
    valueClassName,
    label,
    trend,
}: StatCardProps) {
    return (
        <Card>
            <CardContent className="p-4 flex items-center gap-4">
                <div className={`${iconBgClassName} rounded-lg p-2`}>
                    <Icon className={`size-5 ${iconClassName}`} />
                </div>
                <div>
                    <p className={`text-2xl font-bold tabular-nums ${valueClassName ?? ""}`}>{value}</p>
                    <p className="text-sm text-muted-foreground">{label}</p>
                    {trend && (
                        <div className={`flex items-center gap-1 text-xs mt-1 font-medium ${trend.value === 0 ? "text-muted-foreground" :
                                trend.value > 0
                                    ? (trend.invertColors ? "text-red-600" : "text-green-600")
                                    : (trend.invertColors ? "text-green-600" : "text-red-600")
                            }`}>
                            {trend.value > 0 ? <TrendingUp className="size-3" /> : trend.value < 0 ? <TrendingDown className="size-3" /> : <Minus className="size-3" />}
                            <span>{Math.abs(trend.value).toFixed(1)}%</span>
                            <span className="text-muted-foreground font-normal ml-1">{trend.label}</span>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
