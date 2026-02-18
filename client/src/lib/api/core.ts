import { ApiError } from "../api-error";
import { useAuthStore } from "../auth-store";

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = useAuthStore.getState().token;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401 && !endpoint.includes("/api/auth/login")) {
      useAuthStore.getState().logout();
    }
    const errorData = await response.json().catch(() => ({}));
    throw ApiError.fromResponse(response, errorData);
  }

  return response.json();
}

// Query params helper
export function buildQueryString(
  params: Record<string, string | number | boolean | undefined>,
): string {
  const searchParams = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "")
      searchParams.set(k, String(v));
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}
