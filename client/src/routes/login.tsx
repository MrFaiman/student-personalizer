import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { GraduationCap, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useAuthStore } from "@/lib/auth-store";
import { authApi } from "@/lib/api/auth";
import { loginSchema, registerSchema } from "@/lib/schemas/auth";
import type { ZodError } from "zod";

type Action = "login" | "register";

function fieldError(error: ZodError | null, field: string): string | undefined {
  return error?.issues.find((i) => i.path[0] === field)?.message;
}

export const Route = createFileRoute("/login")({ component: AuthPage });

function AuthPage() {
  const { t } = useTranslation();
  const [action, setAction] = useState<Action>("login");

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-background p-4"
      dir="rtl"
    >
      <Card className="w-full max-w-md">
        <CardHeader className="text-center space-y-4">
          <div className="flex justify-center">
            <div className="bg-primary/10 rounded-full p-3">
              <GraduationCap className="size-8 text-primary" />
            </div>
          </div>
          <div>
            <h1 className="text-2xl font-bold">{t("appName")}</h1>
            <p className="text-muted-foreground text-sm">
              {action === "login"
                ? t("auth.loginSubtitle")
                : t("auth.registerSubtitle")}
            </p>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {action === "login" ? (
            <LoginForm />
          ) : (
            <RegisterForm />
          )}
          <p className="text-sm text-center text-muted-foreground">
            {action === "login"
              ? t("auth.noAccountYet")
              : t("auth.alreadyHaveAccount")}{" "}
            <button
              type="button"
              onClick={() => setAction(action === "login" ? "register" : "login")}
              className="text-primary font-medium hover:underline"
            >
              {action === "login" ? t("auth.register") : t("auth.login")}
            </button>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function LoginForm() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [validationError, setValidationError] = useState<ZodError | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setValidationError(null);

    const result = loginSchema.safeParse({ email, password });
    if (!result.success) {
      setValidationError(result.error);
      return;
    }

    setLoading(true);
    try {
      await login(result.data.email, result.data.password);
      navigate({ to: "/dashboard" });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.loginFailed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">{t("auth.email")}</Label>
        <Input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="user@school.local"
          dir="ltr"
        />
        {fieldError(validationError, "email") && (
          <p className="text-xs text-destructive">
            {t("auth.validation.email")}
          </p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">{t("auth.password")}</Label>
        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          dir="ltr"
        />
        {fieldError(validationError, "password") && (
          <p className="text-xs text-destructive">
            {t("auth.validation.password")}
          </p>
        )}
      </div>
      {error && (
        <p className="text-sm text-destructive text-center">{error}</p>
      )}
      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          t("auth.login")
        )}
      </Button>
    </form>
  );
}

function RegisterForm() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [validationError, setValidationError] = useState<ZodError | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setValidationError(null);

    const result = registerSchema.safeParse({ fullName, email, password });
    if (!result.success) {
      setValidationError(result.error);
      return;
    }

    setLoading(true);
    try {
      await authApi.register({
        email: result.data.email,
        password: result.data.password,
        full_name: result.data.fullName,
        role: "viewer",
      });
      await login(result.data.email, result.data.password);
      navigate({ to: "/dashboard" });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.registerFailed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="fullName">{t("auth.fullName")}</Label>
        <Input
          id="fullName"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
        {fieldError(validationError, "fullName") && (
          <p className="text-xs text-destructive">
            {t("auth.validation.fullName")}
          </p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="regEmail">{t("auth.email")}</Label>
        <Input
          id="regEmail"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          dir="ltr"
        />
        {fieldError(validationError, "email") && (
          <p className="text-xs text-destructive">
            {t("auth.validation.email")}
          </p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="regPassword">{t("auth.password")}</Label>
        <Input
          id="regPassword"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          dir="ltr"
        />
        {fieldError(validationError, "password") && (
          <p className="text-xs text-destructive">
            {t("auth.validation.passwordMin")}
          </p>
        )}
      </div>
      {error && (
        <p className="text-sm text-destructive text-center">{error}</p>
      )}
      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          t("auth.register")
        )}
      </Button>
    </form>
  );
}
