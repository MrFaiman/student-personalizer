import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface KPICardProps {
    title: string;
    value: string;
    isLoading: boolean;
    icon: LucideIcon;
    iconColor: string;
    footer?: React.ReactNode;
}

export function KPICard({ title, value, isLoading, icon: Icon, iconColor, footer }: KPICardProps) {
    return (
        <Card className="shadow-sm">
            <CardContent className="p-6">
                <div className="flex flex-col gap-2">
                    <div className="flex justify-between items-start">
                        <p className="text-muted-foreground text-sm font-semibold">{title}</p>
                        <div className={`${iconColor} rounded-lg p-2`}>
                            <Icon className="size-5" />
                        </div>
                    </div>
                    {isLoading ? (
                        <Skeleton className="h-9 w-20" />
                    ) : (
                        <p className="text-3xl font-bold leading-tight tabular-nums">{value}</p>
                    )}
                    {footer && (
                        <div className="flex items-center gap-1 mt-1 text-muted-foreground text-xs">
                            {footer}
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
