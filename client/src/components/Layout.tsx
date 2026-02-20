import { Link, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import {
  GraduationCap,
  LayoutDashboard,
  Users,
  School,
  Upload,
  Brain,
  Search,
  Menu,
  UserCheck,
  BarChart3,
} from "lucide-react";
import { useFilters } from "./FilterContext";
import { analyticsApi } from "@/lib/api";
import { METADATA_STALE_TIME_MS } from "@/lib/constants";
import type { ReactNode } from "react";
import { useState } from "react";

const navItems = [
  { icon: LayoutDashboard, labelKey: "nav.dashboard", path: "/" },
  {
    icon: BarChart3,
    labelKey: "nav.advancedAnalytics",
    path: "/advanced-analytics",
  },
  { icon: Users, labelKey: "nav.students", path: "/students" },
  { icon: School, labelKey: "nav.classes", path: "/classes" },
  { icon: UserCheck, labelKey: "nav.teachers", path: "/teachers" },
  { icon: Brain, labelKey: "nav.predictions", path: "/predictions" },
  { icon: Upload, labelKey: "nav.upload", path: "/upload" },
];

export function Layout({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden" dir="rtl">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-72 bg-card border-l border-border flex-col shrink-0">
        <SidebarContent />
      </aside>

      {/* Mobile sidebar */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="right" className="w-72 p-0" showCloseButton={true}>
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SidebarContent onNavigate={() => setSidebarOpen(false)} />
        </SheetContent>
      </Sheet>

      <main className="flex-1 flex flex-col overflow-y-auto">
        <Header onMenuClick={() => setSidebarOpen(true)} />
        <div className="p-4 md:p-8 space-y-4 md:space-y-8">{children}</div>
      </main>
    </div>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void } = {}) {
  const { t } = useTranslation();
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const { filters, setFilter } = useFilters();

  const { data: metadata } = useQuery({
    queryKey: ["metadata"],
    queryFn: analyticsApi.getMetadata,
    staleTime: METADATA_STALE_TIME_MS,
  });

  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ["kpis-global"],
    queryFn: () => analyticsApi.getKPIs({}),
  });

  const isEmptyState = !kpisLoading && kpis?.total_students === 0;

  return (
    <div className="p-6 flex flex-col gap-6 h-full justify-between">
      <div className="flex flex-col gap-6">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 rounded-full p-2">
            <GraduationCap className="size-7 text-primary" />
          </div>
          <div className="flex flex-col">
            <h1 className="text-lg font-bold leading-tight">{t("appName")}</h1>
            <p className="text-muted-foreground text-xs">{t("appTagline")}</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => {
            const isActive =
              currentPath === item.path ||
              (item.path !== "/" && currentPath.startsWith(item.path));
            const isDisabled = isEmptyState && item.path !== "/upload";

            return (
              <Link
                key={item.path}
                to={item.path}
                disabled={isDisabled}
                onClick={onNavigate}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent"
                } ${isDisabled ? "opacity-50 pointer-events-none grayscale" : ""}`}
              >
                <item.icon className="size-5" aria-hidden="true" />
                <span
                  className={`text-sm ${isActive ? "font-semibold" : "font-medium"}`}
                >
                  {t(item.labelKey)}
                </span>
              </Link>
            );
          })}
        </nav>

        {/* Filters */}
        <div
          className={`pt-4 border-t border-border ${isEmptyState ? "opacity-50 pointer-events-none grayscale" : ""}`}
        >
          <p className="text-xs font-bold text-muted-foreground px-3 mb-3 uppercase tracking-wider">
            {t("filters.title")}
          </p>
          <div className="flex flex-col gap-3 px-1">
            {/* Period Filter */}
            <Select
              value={filters.period || "__all__"}
              onValueChange={(v) =>
                setFilter("period", v === "__all__" ? undefined : v)
              }
              disabled={isEmptyState}
              dir="rtl"
            >
              <SelectTrigger className="h-9 text-sm w-full">
                <SelectValue placeholder={t("filters.allPeriods")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">
                  {t("filters.allPeriods")}
                </SelectItem>
                {metadata?.periods.map((period) => (
                  <SelectItem key={period} value={period}>
                    {period}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Grade Level Filter */}
            <Select
              value={filters.gradeLevel || "__all__"}
              onValueChange={(v) =>
                setFilter("gradeLevel", v === "__all__" ? undefined : v)
              }
              disabled={isEmptyState}
              dir="rtl"
            >
              <SelectTrigger className="h-9 text-sm w-full">
                <SelectValue placeholder={t("filters.allGradeLevels")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">
                  {t("filters.allGradeLevels")}
                </SelectItem>
                {metadata?.grade_levels.map((level) => (
                  <SelectItem key={level} value={level}>
                    {t("filters.gradeLevel", { level })}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Bottom Actions */}
      <div className="flex flex-col gap-3">
        <Link
          to="/students"
          className={isEmptyState ? "pointer-events-none" : ""}
        >
          <Button className="w-full gap-2" disabled={isEmptyState}>
            <Search className="size-4" />
            <span>{t("filters.searchStudent")}</span>
          </Button>
        </Link>
      </div>
    </div>
  );
}

function Header({ onMenuClick }: { onMenuClick: () => void }) {
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
