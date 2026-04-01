import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
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
import {
  GraduationCap,
  LayoutDashboard,
  Users,
  Shield,
  School,
  Upload,
  Brain,
  Search,
  UserCheck,
  BarChart3,
  Book,
  CalendarDays,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { useFilterStore } from "@/lib/filter-store";
import { formatHebrewYear } from "@/lib/hebrew-year";
import { analyticsApi } from "@/lib/api";
import { METADATA_STALE_TIME_MS } from "@/lib/constants";
import { useAppForm } from "@/lib/form";

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
  { icon: Book, labelKey: "nav.subjects", path: "/subjects" },
  { icon: Brain, labelKey: "nav.predictions", path: "/predictions" },
  { icon: CalendarDays, labelKey: "nav.openDay", path: "/open-day" },
  { icon: Upload, labelKey: "nav.upload", path: "/upload" },
];

export function SidebarContent({ onNavigate }: { onNavigate?: () => void } = {}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const { year, period, gradeLevel, setFilter } = useFilterStore();
  const user = useAuthStore((s) => s.user);
  const isAdmin = useAuthStore((s) => s.hasRole("super_admin", "system_admin"));
  const logout = useAuthStore((s) => s.logout);

  async function handleLogout() {
    await logout();
    navigate({ to: "/login" });
  }

  const form = useAppForm({
    defaultValues: {
      year: year || "__all__",
      period: period || "__all__",
      gradeLevel: gradeLevel || "__all__",
    },
  });

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
            const isDisabled = isEmptyState && item.path !== "/upload" && item.path !== "/open-day";

            return (
              <Link
                key={item.path}
                to={item.path}
                disabled={isDisabled}
                onClick={onNavigate}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${isActive
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

          {isAdmin && (
            <Link
              to="/admin/users"
              onClick={onNavigate}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                currentPath.startsWith("/admin")
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent"
              }`}
            >
              <Shield className="size-5" aria-hidden="true" />
              <span
                className={`text-sm ${
                  currentPath.startsWith("/admin") ? "font-semibold" : "font-medium"
                }`}
              >
                {t("nav.userManagement")}
              </span>
            </Link>
          )}
        </nav>

        {/* Filters */}
        <div
          className={`pt-4 border-t border-border ${isEmptyState ? "opacity-50 pointer-events-none grayscale" : ""}`}
        >
          <p className="text-xs font-bold text-muted-foreground px-3 mb-3 uppercase tracking-wider">
            {t("filters.title")}
          </p>
          <div className="flex flex-col gap-3 px-1">
            {/* Year Filter */}
            <form.Field name="year">
              {(field) => (
                <Select
                  value={field.state.value}
                  onValueChange={(v) => {
                    field.handleChange(v as typeof field.state.value);
                    setFilter("year", v === "__all__" ? undefined : v);
                  }}
                  disabled={isEmptyState}
                  dir="rtl"
                >
                  <SelectTrigger className="h-9 text-sm w-full">
                    <SelectValue placeholder={t("filters.allYears", "כל השנים")} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">
                      {t("filters.allYears", "כל השנים")}
                    </SelectItem>
                    {metadata?.years.map((year) => (
                      <SelectItem key={year} value={year}>
                        {formatHebrewYear(year)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </form.Field>

            {/* Period Filter */}
            <form.Field name="period">
              {(field) => (
                <Select
                  value={field.state.value}
                  onValueChange={(v) => {
                    field.handleChange(v as typeof field.state.value);
                    setFilter("period", v === "__all__" ? undefined : v);
                  }}
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
              )}
            </form.Field>

            {/* Grade Level Filter */}
            <form.Field name="gradeLevel">
              {(field) => (
                <Select
                  value={field.state.value}
                  onValueChange={(v) => {
                    field.handleChange(v as typeof field.state.value);
                    setFilter("gradeLevel", v === "__all__" ? undefined : v);
                  }}
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
              )}
            </form.Field>
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

        {user && (
          <div className="pt-3 border-t border-border space-y-2">
            <div className="px-3 py-1">
              <p className="text-sm font-medium truncate">{user.display_name}</p>
              <p className="text-xs text-muted-foreground truncate">{t(`auth.role.${user.role}`)}</p>
            </div>
            <Link to="/security/mfa" onClick={onNavigate}>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
              >
                <ShieldCheck className="size-4" />
                <span>{t("security.mfa.title")}</span>
              </Button>
            </Link>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
              onClick={handleLogout}
            >
              <LogOut className="size-4" />
              <span>{t("auth.signOut")}</span>
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
