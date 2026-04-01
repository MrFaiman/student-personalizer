import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { GraduationCap, Menu } from "lucide-react";
import { SchoolSwitcher } from "@/components/SchoolSwitcher";

export function Header({ onMenuClick }: { onMenuClick: () => void }) {
  const { t } = useTranslation();

  return (
    <header className="flex items-center justify-between bg-card border-b border-border px-4 md:px-8 py-4 sticky top-0 z-10">
      <div className="flex items-center gap-3 md:hidden">
        <div className="bg-primary/10 rounded-full p-1.5">
          <GraduationCap className="size-5 text-primary" />
        </div>
        <span className="text-sm font-bold">{t("appName")}</span>
      </div>
      <div className="hidden md:flex items-center gap-6">
        <SchoolSwitcher />
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={onMenuClick}
        aria-label="Open menu"
      >
        <Menu className="size-5" />
      </Button>
    </header>
  );
}
