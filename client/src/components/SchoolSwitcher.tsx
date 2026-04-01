import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { authApi } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/auth-store";
import type { SchoolOption } from "@/lib/types/auth";

function isSelectableRole(role: string | undefined | null) {
  return role === "teacher" || role === "school_admin";
}

export function SchoolSwitcher() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.accessToken);
  const selectSchool = useAuthStore((s) => s.selectSchool);

  const enabled = !!token && isSelectableRole(user?.role);

  const { data, isLoading } = useQuery({
    queryKey: ["my-schools"],
    enabled,
    queryFn: () => authApi.mySchools(token!),
    staleTime: 60_000,
  });

  const options = (data ?? []) as SchoolOption[];
  const value = useMemo(() => {
    // When no school is selected yet, keep Select uncontrolled (value=undefined)
    // so the placeholder is shown (instead of value="" which matches no SelectItem).
    return user?.school_id != null ? String(user.school_id) : undefined;
  }, [user?.school_id]);

  if (!enabled) return null;

  return (
    <Select
      value={value}
      onValueChange={async (v) => {
        const parsed = Number(v);
        if (!Number.isFinite(parsed)) return;
        await selectSchool(parsed);
      }}
      dir="rtl"
      disabled={isLoading || options.length === 0}
    >
      <SelectTrigger className="h-8 w-[220px]">
        <SelectValue placeholder={t("schools.selectSchool")} />
      </SelectTrigger>
      <SelectContent>
        {options.map((o) => (
          <SelectItem key={o.school_id} value={String(o.school_id)}>
            {o.school_name} ({o.school_id})
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

