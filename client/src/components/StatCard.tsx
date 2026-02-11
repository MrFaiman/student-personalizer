import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
    icon: LucideIcon;
    iconClassName: string;
    iconBgClassName: string;
    value: React.ReactNode;
    valueClassName?: string;
    label: string;
}

export function StatCard({
    icon: Icon,
    iconClassName,
    iconBgClassName,
    value,
    valueClassName,
    label,
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
                </div>
            </CardContent>
        </Card>
    );
}
