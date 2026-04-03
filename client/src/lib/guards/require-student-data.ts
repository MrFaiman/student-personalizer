import { isRedirect, redirect } from "@tanstack/react-router";
import { analyticsApi } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import { useAuthStore } from "@/lib/auth-store";
import { queryClient } from "@/lib/query-client";

function isSchoolScopeRequiredError(error: unknown): boolean {
  if (!ApiError.isApiError(error) || error.status !== 403) return false;
  const detail = error.data?.detail;
  return detail === "School scope required" || error.message === "School scope required";
}

function usesSelectSchoolFlow(user: { role: string } | null | undefined): boolean {
  if (!user) return false;
  return (
    user.role === "teacher" ||
    user.role === "school_admin" ||
    user.role === "super_admin" ||
    user.role === "system_admin"
  );
}

export async function requireStudentData(): Promise<void> {
  const { user } = useAuthStore.getState();
  if (user?.school_id == null) {
    if (usesSelectSchoolFlow(user)) {
      throw redirect({ to: "/select-school" });
    }
    throw redirect({ to: "/upload" });
  }

  try {
    const kpis = await queryClient.ensureQueryData({
      queryKey: ["kpis-global"],
      queryFn: () => analyticsApi.getKPIs({}),
    });
    if (kpis.total_students === 0) {
      throw redirect({ to: "/upload" });
    }
  } catch (e) {
    if (isRedirect(e)) throw e;
    if (isSchoolScopeRequiredError(e)) {
      const u = useAuthStore.getState().user;
      if (usesSelectSchoolFlow(u)) {
        throw redirect({ to: "/select-school" });
      }
      throw redirect({ to: "/upload" });
    }
    throw e;
  }
}
