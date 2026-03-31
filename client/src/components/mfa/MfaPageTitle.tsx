import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type Variant = "centered" | "inline";

export function MfaPageTitle({
  variant,
  icon,
  title,
  subtitle,
  badge,
  className,
}: {
  variant: Variant;
  icon: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  badge?: ReactNode;
  className?: string;
}) {
  if (variant === "centered") {
    return (
      <div className={cn("flex flex-col items-center gap-3", className)}>
        <div className="bg-primary/10 rounded-full p-4">{icon}</div>
        <h1 className="text-2xl font-bold">{title}</h1>
        {subtitle ? (
          <p className="text-muted-foreground text-sm text-center">{subtitle}</p>
        ) : null}
      </div>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      <h1 className="text-2xl font-bold flex items-center gap-2">
        {icon}
        {title}
      </h1>
      {(badge || subtitle) && (
        <div className="flex items-center gap-2">
          {badge}
          {subtitle ? (
            <span className="text-sm text-muted-foreground">{subtitle}</span>
          ) : null}
        </div>
      )}
    </div>
  );
}

