import { createFileRoute, redirect } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, LockOpen } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/lib/auth-store";
import { authApi } from "@/lib/api/auth";
import { MfaEnrollPanel } from "@/components/MfaEnrollPanel";

export const Route = createFileRoute("/security/mfa")({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated;
    if (!isAuthenticated) throw redirect({ to: "/login" });
  },
  component: MfaSettingsPage,
});

function MfaSettingsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const token = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);

  const [disableCode, setDisableCode] = useState("");

  const enabled = !!user?.mfa_enabled;

  const disableMutation = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("No access token");
      await authApi.mfaDisable(token, disableCode);
    },
    onSuccess: async () => {
      setDisableCode("");
      const freshUser = await authApi.me(token!);
      useAuthStore.getState().setUser(freshUser);
      await qc.invalidateQueries();
    },
  });

  const statusBadge = useMemo(() => {
    return enabled ? (
      <Badge className="bg-green-100 text-green-700">{t("security.mfa.enabled")}</Badge>
    ) : (
      <Badge className="bg-muted text-muted-foreground">{t("security.mfa.disabled")}</Badge>
    );
  }, [enabled, t]);

  return (
    <div className="space-y-4" dir="rtl">
      <Helmet>
        <title>{`${t("security.mfa.title")} | ${t("appName")}`}</title>
      </Helmet>

      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <ShieldCheck className="size-6 text-muted-foreground" />
          {t("security.mfa.title")}
        </h1>
        <div className="flex items-center gap-2 mt-2">
          {statusBadge}
          <span className="text-sm text-muted-foreground">
            {t("security.mfa.subtitle")}
          </span>
        </div>
      </div>

      {!enabled && <MfaEnrollPanel />}

      {enabled && (
        <Card>
          <CardContent className="p-6 space-y-3">
            <h3 className="text-lg font-bold">{t("security.mfa.disableTitle")}</h3>
            <p className="text-sm text-muted-foreground">{t("security.mfa.disableDescription")}</p>
            <div className="flex gap-2">
              <Input
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value)}
                placeholder="000000"
                dir="ltr"
                inputMode="numeric"
              />
              <Button
                variant="destructive"
                onClick={() => disableMutation.mutate()}
                disabled={disableMutation.isPending || disableCode.trim().length < 6}
                className="gap-2"
              >
                <LockOpen className="size-4" />
                {disableMutation.isPending ? t("general.loading") : t("security.mfa.disable")}
              </Button>
            </div>
            {disableMutation.error && (
              <div className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
                {(disableMutation.error as Error).message}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

