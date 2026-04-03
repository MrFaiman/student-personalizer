import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { School } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/auth-store";
import { cn } from "@/lib/utils";

type Props = {
  /** e.g. close mobile drawer when navigating */
  onNavigate?: () => void;
  className?: string;
};

export function GlobalAdminSchoolButton({ onNavigate, className }: Props) {
  const { t } = useTranslation();
  const isGlobalAdmin = useAuthStore((s) => s.hasRole("super_admin", "system_admin"));

  if (!isGlobalAdmin) return null;

  return (
    <Button asChild variant="outline" size="sm" className={cn("h-8 gap-2 font-normal", className)}>
      <Link to="/select-school" onClick={onNavigate}>
        <School className="size-4 shrink-0" aria-hidden />
        <span className="truncate">{t("schools.changeSchool")}</span>
      </Link>
    </Button>
  );
}
