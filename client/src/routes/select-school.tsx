import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import { School } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/auth-store";
import { authApi } from "@/lib/api/auth";

export const Route = createFileRoute("/select-school")({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated;
    if (!isAuthenticated) throw redirect({ to: "/login" });
  },
  component: SelectSchoolPage,
});

function SelectSchoolPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const token = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const selectSchool = useAuthStore((s) => s.selectSchool);

  const enabled = !!token && (user?.role === "teacher" || user?.role === "school_admin");

  const { data, isLoading, error } = useQuery({
    queryKey: ["my-schools"],
    enabled,
    queryFn: () => authApi.mySchools(token!),
    staleTime: 60_000,
  });

  // If not applicable, just go home.
  if (!enabled) {
    navigate({ to: "/" });
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
            {t("auth.loginSubtitle")}
          </p>
        </div>

        <Card>
          <CardContent className="p-6 space-y-3">
            {isLoading ? (
              <div className="text-sm text-muted-foreground">{t("general.loading")}</div>
            ) : error ? (
              <div className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
                {(error as Error).message}
              </div>
            ) : !data?.length ? (
              <div className="text-sm text-muted-foreground">{t("general.noData")}</div>
            ) : (
              <div className="space-y-2">
                {data.map((s) => (
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
                    <span className="text-xs opacity-70">{s.school_id}</span>
                  </Button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

