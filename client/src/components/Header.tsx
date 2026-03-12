import { useTranslation } from "react-i18next";
import { GraduationCap } from "lucide-react";
import { SidebarTrigger } from "@/components/ui/sidebar";

export function Header() {
  const { t } = useTranslation();

  return (
    <header className="flex items-center justify-between bg-card border-b border-border px-4 md:px-8 py-4 sticky top-0 z-10">
      <div className="flex items-center gap-3 md:hidden">
        <div className="bg-primary/10 rounded-full p-1.5">
          <GraduationCap className="size-5 text-primary" />
        </div>
        <span className="text-sm font-bold">{t("appName")}</span>
      </div>
      <div className="hidden md:flex items-center gap-6" />
      <SidebarTrigger className="md:hidden" />
    </header>
  );
}
