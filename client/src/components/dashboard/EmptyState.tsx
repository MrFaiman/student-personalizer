import { Upload } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

export function EmptyState() {
    const { t } = useTranslation("dashboard");

    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6 text-center">
            <div className="bg-muted/30 p-6 rounded-full">
                <Upload className="size-12 text-muted-foreground" />
            </div>
            <div className="space-y-2 max-w-md">
                <h2 className="text-2xl font-bold tracking-tight">{t("emptyState.title")}</h2>
                <p className="text-muted-foreground">
                    {t("emptyState.description")}
                </p>
            </div>
            <Link to="/upload">
                <Button size="lg" className="gap-2">
                    <Upload className="size-4" />
                    {t("emptyState.button")}
                </Button>
            </Link>
        </div>
    );
}
