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
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  GraduationCap,
  LayoutDashboard,
  Users,
  School,
  Upload,
  Brain,
  Search,
  UserCheck,
  BarChart3,
  Book,
  CalendarDays,
} from "lucide-react";
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

export function AppSidebar() {
  const { t } = useTranslation();
  const { setOpenMobile } = useSidebar();
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const { year, period, gradeLevel, setFilter } = useFilterStore();

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
    <Sidebar side="right" dir="rtl" collapsible="offcanvas">
      <SidebarHeader className="p-6">
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 rounded-full p-2">
            <GraduationCap className="size-7 text-primary" />
          </div>
          <div className="flex flex-col">
            <h1 className="text-lg font-bold leading-tight">{t("appName")}</h1>
            <p className="text-muted-foreground text-xs">{t("appTagline")}</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        {/* Navigation */}
        <SidebarGroup>
          <SidebarMenu>
            {navItems.map((item) => {
              const isActive =
                currentPath === item.path ||
                (item.path !== "/" && currentPath.startsWith(item.path));
              const isDisabled =
                isEmptyState &&
                item.path !== "/upload" &&
                item.path !== "/open-day";

              return (
                <SidebarMenuItem key={item.path}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive}
                    disabled={isDisabled}
                    className={isDisabled ? "opacity-50 grayscale" : ""}
                    onClick={() => setOpenMobile(false)}
                  >
                    <Link to={item.path}>
                      <item.icon aria-hidden="true" />
                      <span>{t(item.labelKey)}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            })}
          </SidebarMenu>
        </SidebarGroup>

        {/* Filters */}
        <SidebarGroup
          className={
            isEmptyState ? "opacity-50 pointer-events-none grayscale" : ""
          }
        >
          <SidebarGroupLabel className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
            {t("filters.title")}
          </SidebarGroupLabel>
          <div className="flex flex-col gap-3 px-2 pt-1">
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
                    <SelectValue
                      placeholder={t("filters.allYears", "כל השנים")}
                    />
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
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-6">
        <Link
          to="/students"
          className={isEmptyState ? "pointer-events-none" : ""}
        >
          <Button className="w-full gap-2" disabled={isEmptyState}>
            <Search className="size-4" />
            <span>{t("filters.searchStudent")}</span>
          </Button>
        </Link>
      </SidebarFooter>
    </Sidebar>
  );
}
