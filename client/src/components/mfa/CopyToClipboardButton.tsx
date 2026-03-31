import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Copy } from "lucide-react";

import { Button, type ButtonProps } from "@/components/ui/button";

export function CopyToClipboardButton({
  text,
  children,
  ...buttonProps
}: Omit<ButtonProps, "onClick"> & { text: string; children?: React.ReactNode }) {
  const { t } = useTranslation();
  const [isCopying, setIsCopying] = useState(false);

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className={"gap-2"}
      onClick={async () => {
        try {
          setIsCopying(true);
          await navigator.clipboard.writeText(text);
        } finally {
          setIsCopying(false);
        }
      }}
      aria-busy={isCopying}
      {...buttonProps}
    >
      <Copy className="size-4" />
      {children ?? t("security.mfa.copy")}
    </Button>
  );
}

