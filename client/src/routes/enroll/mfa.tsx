import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Helmet } from "react-helmet-async";
import { ShieldCheck } from "lucide-react";

import { useAuthStore } from "@/lib/auth-store";
import { useConfigStore } from "@/lib/config-store";
import { MfaEnrollPanel } from "@/components/MfaEnrollPanel";
import { MfaPageTitle } from "@/components/mfa/MfaPageTitle";

export const Route = createFileRoute("/enroll/mfa")({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated;
    if (!isAuthenticated) throw redirect({ to: "/login" });
  },
  component: EnrollMfaPage,
});

function EnrollMfaPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const enforcedRoles = useConfigStore((s) => s.mfaEnforcedRoles);

  const role = user?.role ?? null;
  const isEnforced = role ? enforcedRoles.includes(role) : false;

  useEffect(() => {
    if (!user) return;
    if (!isEnforced) {
      navigate({ to: "/" });
      return;
    }
    if (user.mfa_enabled) {
      navigate({ to: "/" });
    }
  }, [user, isEnforced, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4" dir="rtl">
      <Helmet>
        <title>{`${t("security.mfa.title")} | ${t("appName")}`}</title>
      </Helmet>
      <div className="w-full max-w-md space-y-6">
        <MfaPageTitle
          variant="centered"
          icon={<ShieldCheck className="size-10 text-primary" />}
          title={t("security.mfa.enrollTitle")}
          subtitle={t("security.mfa.enrollSubtitle")}
        />

        <MfaEnrollPanel
          onEnrolled={() => {
            navigate({ to: "/" });
          }}
        />
      </div>
    </div>
  );
}

