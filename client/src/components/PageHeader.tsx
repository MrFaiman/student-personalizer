import { ArrowRight } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface StatPill {
    value: React.ReactNode;
    label: string;
    valueClassName?: string;
}

interface PageHeaderProps {
    backTo: string;
    backLabel: string;
    title: string;
    subtitle?: string;
    stats?: StatPill[];
    trailing?: React.ReactNode;
}

export function PageHeader({ backTo, backLabel, title, subtitle, stats, trailing }: PageHeaderProps) {
    return (
        <div className="space-y-4">
            <Link to={backTo}>
                <Button variant="ghost" className="gap-2">
                    <ArrowRight className="size-4" />
                    {backLabel}
                </Button>
            </Link>
            <div className="flex justify-between items-start">
                <div className="flex-1">
                    <h1 className="text-2xl font-bold">{title}</h1>
                    {subtitle && <p className="text-muted-foreground">{subtitle}</p>}
                </div>
                {trailing}
                {stats && (
                    <div className="flex gap-4">
                        {stats.map((stat) => (
                            <Card key={String(stat.label)} className="px-4 py-2">
                                <div className="text-center">
                                    <div className={`text-2xl font-bold tabular-nums ${stat.valueClassName ?? "text-primary"}`}>
                                        {stat.value}
                                    </div>
                                    <div className="text-xs text-muted-foreground">{stat.label}</div>
                                </div>
                            </Card>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
