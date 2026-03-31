import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authApi } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/auth-store";

interface Props {
  open: boolean;
  onSuccess: () => void;
}

export function ChangePasswordDialog({ open, onSuccess }: Props) {
  const { t } = useTranslation();
  const accessToken = useAuthStore((s) => s.accessToken);

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrors([]);

    if (next !== confirm) {
      setErrors([t("auth.passwordMismatch")]);
      return;
    }

    if (!accessToken) {
      setErrors([t("auth.sessionExpired", "פג תוקף החיבור. התחבר מחדש.")]);
      return;
    }

    setLoading(true);
    try {
      await authApi.changePassword(accessToken, current, next);
      onSuccess();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : t("auth.changePasswordError");
      // Try to parse password errors from server
      try {
        const parsed = JSON.parse(msg);
        const raw = (parsed as { password_errors?: unknown } | null)?.password_errors;
        if (typeof raw === "string") {
          setErrors([raw]);
          return;
        }
        if (Array.isArray(raw)) {
          const normalized = raw.filter((v): v is string => typeof v === "string");
          if (normalized.length > 0) {
            setErrors(normalized);
            return;
          }
          return;
        }
      } catch {
        console.warn("Failed to parse error message as JSON:", msg);
      }
      setErrors([msg]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      dir="rtl"
    >
      <div className="bg-background rounded-xl shadow-xl w-full max-w-sm p-6 space-y-5">
        <div>
          <h2 className="text-lg font-bold">{t("auth.changePassword")}</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {t("auth.changePasswordRequired")}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {t("auth.currentPassword")}
            </label>
            <Input
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
              dir="ltr"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {t("auth.newPassword")}
            </label>
            <Input
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
              dir="ltr"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {t("auth.confirmPassword")}
            </label>
            <Input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              dir="ltr"
            />
          </div>

          {errors.length > 0 && (
            <ul className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2 space-y-1">
              {errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}

          <Button type="submit" className="w-full" disabled={loading || !accessToken}>
            {loading ? t("auth.saving") : t("auth.changePassword")}
          </Button>
        </form>
      </div>
    </div>
  );
}
