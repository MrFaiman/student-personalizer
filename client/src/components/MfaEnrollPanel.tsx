import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import * as QRCode from "qrcode";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { authApi } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/auth-store";
import { CopyToClipboardButton } from "@/components/mfa/CopyToClipboardButton";
import { MfaCodeInput } from "@/components/mfa/MfaCodeInput";

export function MfaEnrollPanel({ onEnrolled }: { onEnrolled?: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const token = useAuthStore((s) => s.accessToken);

  const [setupData, setSetupData] = useState<{ provisioningUri: string; secret: string } | null>(null);
  const [verifyCode, setVerifyCode] = useState("");
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null);

  const setupMutation = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("No access token");
      return authApi.mfaSetup(token);
    },
    onSuccess: (data) => {
      setBackupCodes(null);
      setVerifyCode("");
      setSetupData({ provisioningUri: data.provisioning_uri, secret: data.secret });
    },
  });

  const verifyMutation = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("No access token");
      return authApi.mfaVerify(token, verifyCode);
    },
    onSuccess: async (data) => {
      setBackupCodes(data.backup_codes);
      setSetupData(null);
      setVerifyCode("");
      const currentToken = useAuthStore.getState().accessToken;
      if (!currentToken) return;
      const freshUser = await authApi.me(currentToken);
      useAuthStore.getState().setUser(freshUser);
      await qc.invalidateQueries();
      onEnrolled?.();
    },
  });

  const { data: qrDataUrl, isLoading: qrLoading } = useQuery({
    queryKey: ["mfa-qr", setupData?.provisioningUri],
    enabled: !!setupData?.provisioningUri,
    queryFn: async () => {
      return QRCode.toDataURL(setupData!.provisioningUri, {
        margin: 2,
        scale: 6,
        errorCorrectionLevel: "M",
      });
    },
    staleTime: Infinity,
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-6 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <h3 className="text-lg font-bold">{t("security.mfa.enableTitle")}</h3>
              <p className="text-sm text-muted-foreground">
                {t("security.mfa.enableDescription")}
              </p>
            </div>
            <Button
              onClick={() => setupMutation.mutate()}
              disabled={setupMutation.isPending}
              className="gap-2"
            >
              <KeyRound className="size-4" />
              {setupMutation.isPending
                ? t("general.loading")
                : t("security.mfa.generateSecret")}
            </Button>
          </div>

          {setupMutation.error && (
            <div className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
              {(setupMutation.error as Error).message}
            </div>
          )}

          {setupData && (
            <div className="space-y-3">
              <div className="rounded-md border p-4 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium">{t("security.mfa.qrCode")}</div>
                  <CopyToClipboardButton text={setupData.provisioningUri} />
                </div>

                <div className="flex items-center justify-center">
                  {qrLoading ? (
                    <div className="text-sm text-muted-foreground">
                      {t("general.loading")}
                    </div>
                  ) : qrDataUrl ? (
                    <img
                      src={qrDataUrl}
                      alt={t("security.mfa.qrCodeAlt")}
                      className="size-48 rounded-md border bg-white p-2"
                    />
                  ) : (
                    <div className="text-sm text-muted-foreground">
                      {t("general.error")}
                    </div>
                  )}
                </div>

                <div className="text-xs text-muted-foreground">
                  {t("security.mfa.qrCodeHint")}
                </div>
              </div>

              <div className="rounded-md border p-4 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium">{t("security.mfa.secret")}</div>
                  <CopyToClipboardButton text={setupData.secret} />
                </div>
                <div className="font-mono text-sm break-all" dir="ltr">
                  {setupData.secret}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">
                  {t("security.mfa.verifyCode")}
                </label>
                <div className="flex gap-2">
                  <MfaCodeInput
                    value={verifyCode}
                    onChange={(e) => setVerifyCode(e.target.value)}
                  />
                  <Button
                    onClick={() => verifyMutation.mutate()}
                    disabled={verifyMutation.isPending || verifyCode.trim().length < 6}
                  >
                    {verifyMutation.isPending ? t("general.loading") : t("security.mfa.verify")}
                  </Button>
                </div>
                {verifyMutation.error && (
                  <div className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
                    {(verifyMutation.error as Error).message}
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {backupCodes && (
        <Card>
          <CardContent className="p-6 space-y-3">
            <h3 className="text-lg font-bold">{t("security.mfa.backupCodesTitle")}</h3>
            <p className="text-sm text-muted-foreground">
              {t("security.mfa.backupCodesDescription")}
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2" dir="ltr">
              {backupCodes.map((c) => (
                <div
                  key={c}
                  className="rounded-md border px-3 py-2 font-mono text-sm text-center"
                >
                  {c}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

