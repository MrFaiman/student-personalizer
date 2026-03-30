import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { GraduationCap, Lock, Mail } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/lib/auth-store";
import { ChangePasswordDialog } from "@/components/ChangePasswordDialog";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      const currentUser = useAuthStore.getState().user;
      if (currentUser?.must_change_password) {
        setShowChangePassword(true);
      } else {
        navigate({ to: "/" });
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("auth.loginError"));
    } finally {
      setLoading(false);
    }
  }

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
        <form onSubmit={handleSubmit} className="space-y-4">
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
      </div>

      {showChangePassword && (
        <ChangePasswordDialog
          open={showChangePassword}
          onSuccess={() => {
            setShowChangePassword(false);
            navigate({ to: "/" });
          }}
        />
      )}
    </div>
  );
}
