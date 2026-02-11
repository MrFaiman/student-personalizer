import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";

interface StatusBadgeProps {
    isAtRisk: boolean;
}

export function StatusBadge({ isAtRisk }: StatusBadgeProps) {
    const { t } = useTranslation();

    if (isAtRisk) {
        return (
            <Badge className="bg-red-100 text-red-700 hover:bg-red-100">{t("status.highRisk")}</Badge>
        );
    }
    return <Badge variant="secondary">{t("status.normal")}</Badge>;
}
