import { useEffect, useMemo, useState } from "react";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import { School } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/lib/auth-store";
import { authApi } from "@/lib/api/auth";
import type { UserRole } from "@/lib/types/auth";

export const Route = createFileRoute("/select-school")({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated;
    if (!isAuthenticated) throw redirect({ to: "/login" });
  },
  component: SelectSchoolPage,
});

function isGlobalAdminRole(role: UserRole | undefined): boolean {
  return role === "super_admin" || role === "system_admin";
}

function isMembershipSchoolRole(role: UserRole | undefined): boolean {
  return role === "teacher" || role === "school_admin";
}

function SelectSchoolPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const token = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const selectSchool = useAuthStore((s) => s.selectSchool);

  const [authHydrated, setAuthHydrated] = useState(() => useAuthStore.persist.hasHydrated());
  const [filter, setFilter] = useState("");

  useEffect(() => useAuthStore.persist.onFinishHydration(() => setAuthHydrated(true)), []);

  const pageReady = authHydrated && !!token;
  const globalAdmin = isGlobalAdminRole(user?.role);
  const membershipRole = isMembershipSchoolRole(user?.role);
  const canSelectSchool = pageReady && (membershipRole || globalAdmin);

  useEffect(() => {
    if (!authHydrated) return;
    if (!canSelectSchool) {
      navigate({ to: "/", replace: true });
    }
  }, [authHydrated, canSelectSchool, navigate]);

  const membershipQuery = useQuery({
    queryKey: ["my-schools"],
    enabled: pageReady && membershipRole,
    queryFn: () => authApi.mySchools(token!),
    staleTime: 60_000,
  });

  const mashovQuery = useQuery({
    queryKey: ["auth-schools-mashov"],
    enabled: pageReady && globalAdmin,
    queryFn: () => authApi.schools(),
    staleTime: 3_600_000,
  });

  const { data, isLoading, error } = globalAdmin ? mashovQuery : membershipQuery;

  const filteredSchools = useMemo(() => {
    if (!data?.length) return [];
    const q = filter.trim().toLowerCase();
    if (!q) return data;
    return data.filter(
      (s) =>
        s.school_name.toLowerCase().includes(q) || String(s.school_id).includes(q),
    );
  }, [data, filter]);

  if (!authHydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4" dir="rtl">
        <div className="text-sm text-muted-foreground">{t("general.loading")}</div>
      </div>
    );
  }

  if (!canSelectSchool) {
    return null;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4" dir="rtl">
      <Helmet>
        <title>{`${t("schools.selectSchool")} | ${t("appName")}`}</title>
      </Helmet>
      <div className="w-full max-w-md space-y-6">
        <div className="flex flex-col items-center gap-3">
          <div className="bg-primary/10 rounded-full p-4">
            <School className="size-10 text-primary" />
          </div>
          <h1 className="text-2xl font-bold">{t("schools.selectSchool")}</h1>
          <p className="text-muted-foreground text-sm text-center">
            {globalAdmin ? t("schools.selectSchoolPrompt") : t("auth.loginSubtitle")}
          </p>
        </div>

        <Card>
          <CardContent className="p-6 space-y-3">
            {globalAdmin && (
              <Input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder={t("general.search")}
                aria-label={t("general.search")}
              />
            )}
            {isLoading ? (
              <div className="text-sm text-muted-foreground">{t("general.loading")}</div>
            ) : error ? (
              <div className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
                {(error as Error).message}
              </div>
            ) : !data?.length ? (
              <div className="text-sm text-muted-foreground">{t("general.noData")}</div>
            ) : (
              <div className="max-h-[min(24rem,50vh)] space-y-2 overflow-y-auto pe-1">
                {filteredSchools.length === 0 ? (
                  <div className="text-sm text-muted-foreground py-4 text-center">
                    {t("general.noData")}
                  </div>
                ) : (
                  filteredSchools.map((s) => (
                    <Button
                      key={s.school_id}
                      variant={user?.school_id === s.school_id ? "default" : "outline"}
                      className="w-full justify-between"
                      onClick={async () => {
                        await selectSchool(s.school_id);
                        navigate({ to: "/" });
                      }}
                    >
                      <span className="truncate">{s.school_name}</span>
                      <span className="text-xs opacity-70 shrink-0">{s.school_id}</span>
                    </Button>
                  ))
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
