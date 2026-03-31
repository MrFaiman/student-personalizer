import { useEffect, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { GraduationCap, Lock, LogIn, Mail, ShieldCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/lib/auth-store";
import { authApi } from "@/lib/api/auth";
import { ChangePasswordDialog } from "@/components/ChangePasswordDialog";
import { API_BASE_URL } from "@/lib/api/core";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const completeMfa = useAuthStore((s) => s.completeMfa);
  const mfaPending = useAuthStore((s) => s.mfaPending);
  const clearMfaPending = useAuthStore((s) => s.clearMfaPending);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [ssoEnabled, setSsoEnabled] = useState(false);

  useEffect(() => {
    authApi.ssoStatus().then((s) => setSsoEnabled(s.sso_enabled)).catch(() => {});
  }, []);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      // If mfaPending was set by login(), stay on this page to show MFA form
      const state = useAuthStore.getState();
      if (state.mfaPending) return;
      if (state.user?.must_change_password) {
        setShowChangePassword(true);
      } else {
        const enforcedRoles = (await import("@/lib/config-store")).useConfigStore.getState().mfaEnforcedRoles;
        if (state.user?.role && enforcedRoles.includes(state.user.role) && !state.user.mfa_enabled) {
          navigate({ to: "/enroll/mfa" });
        } else {
          navigate({ to: "/" });
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("auth.loginError"));
    } finally {
      setLoading(false);
    }
  }

  async function handleMfa(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await completeMfa(mfaCode);
      const currentUser = useAuthStore.getState().user;
      if (currentUser?.must_change_password) {
        setShowChangePassword(true);
      } else {
        const enforcedRoles = (await import("@/lib/config-store")).useConfigStore.getState().mfaEnforcedRoles;
        if (currentUser?.role && enforcedRoles.includes(currentUser.role) && !currentUser.mfa_enabled) {
          navigate({ to: "/enroll/mfa" });
        } else {
          navigate({ to: "/" });
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("auth.mfaError"));
    } finally {
      setLoading(false);
    }
  }

  function handleBackToLogin() {
    clearMfaPending();
    setMfaCode("");
    setError(null);
  }

  // --- MFA step ---
  if (mfaPending) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4" dir="rtl">
        <div className="w-full max-w-sm space-y-8">
          <div className="flex flex-col items-center gap-3">
            <div className="bg-primary/10 rounded-full p-4">
              <ShieldCheck className="size-10 text-primary" />
            </div>
            <h1 className="text-2xl font-bold">{t("auth.mfaRequired")}</h1>
            <p className="text-muted-foreground text-sm text-center">{t("auth.mfaSubtitle")}</p>
          </div>

          <form onSubmit={handleMfa} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="mfa-code" className="text-sm font-medium">
                {t("auth.mfaCode")}
              </label>
              <Input
                id="mfa-code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                placeholder={t("auth.mfaCodePlaceholder")}
                required
                maxLength={8}
                className="text-center tracking-widest text-lg"
                dir="ltr"
                autoFocus
              />
            </div>

            {error && (
              <div className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
                {error}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={loading || mfaCode.length < 6}>
              {loading ? t("auth.mfaVerifying") : t("auth.mfaVerify")}
            </Button>

            <Button type="button" variant="ghost" className="w-full" onClick={handleBackToLogin}>
              {t("auth.mfaBackToLogin")}
            </Button>
          </form>
        </div>
      </div>
    );
  }

  // --- Login step ---
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4" dir="rtl">
      <div className="w-full max-w-sm space-y-8">
        {/* Logo */}
        <div className="flex flex-col items-center gap-3">
          <div className="bg-primary/10 rounded-full p-4">
            <GraduationCap className="size-10 text-primary" />
          </div>
          <h1 className="text-2xl font-bold">{t("appName")}</h1>
          <p className="text-muted-foreground text-sm text-center">{t("auth.loginSubtitle")}</p>
        </div>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">
              {t("auth.email")}
            </label>
            <div className="relative">
              <Mail className="absolute right-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t("auth.emailPlaceholder")}
                required
                autoComplete="email"
                className="pr-10"
                dir="ltr"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">
              {t("auth.password")}
            </label>
            <div className="relative">
              <Lock className="absolute right-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t("auth.passwordPlaceholder")}
                required
                autoComplete="current-password"
                className="pr-10"
                dir="ltr"
              />
            </div>
          </div>

          {error && (
            <div className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
              {error}
            </div>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? t("auth.signingIn") : t("auth.signIn")}
          </Button>
        </form>

        {/* SSO button */}
        {ssoEnabled && (
          <>
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">{t("auth.orDivider")}</span>
              </div>
            </div>
            <Button
              type="button"
              variant="outline"
              className="w-full gap-2"
              onClick={() => { window.location.href = `${API_BASE_URL}/api/auth/sso/login`; }}
            >
              <LogIn className="size-4" />
              {t("auth.ssoSignIn")}
            </Button>
          </>
        )}
      </div>

      {showChangePassword && (
        <ChangePasswordDialog
          open={showChangePassword}
          onSuccess={async () => {
            setShowChangePassword(false);
            const u = useAuthStore.getState().user;
            const enforcedRoles = (await import("@/lib/config-store")).useConfigStore.getState().mfaEnforcedRoles;
            if (u?.role && enforcedRoles.includes(u.role) && !u.mfa_enabled) {
              navigate({ to: "/enroll/mfa" });
              return;
            }
            navigate({ to: "/" });
          }}
        />
      )}
    </div>
  );
}
