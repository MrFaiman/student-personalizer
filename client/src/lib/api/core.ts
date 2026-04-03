import type { z } from "zod";

import { useAuthStore } from "../auth-store";
import { ApiError } from "../api-error";

import { API_BASE_URL } from "./base-url";

export { API_BASE_URL };

let _refreshPromise: Promise<boolean> | null = null;

export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
  schema?: z.ZodType<T>,
): Promise<T> {
  const { accessToken, refresh } = useAuthStore.getState();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
    credentials: "include",
  });

  // On 401 try a single token refresh
  if (response.status === 401 && accessToken) {
    if (!_refreshPromise) {
      _refreshPromise = refresh().finally(() => {
        _refreshPromise = null;
      });
    }
    const ok = await _refreshPromise;
    if (ok) {
      const newToken = useAuthStore.getState().accessToken;
      const retryHeaders = { ...headers, Authorization: `Bearer ${newToken}` };
      const retry = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: retryHeaders,
        credentials: "include",
      });
      if (!retry.ok) {
        const errorData = await retry.json().catch(() => ({}));
        throw ApiError.fromResponse(retry, errorData);
      }
      const retryData = await retry.json();
      if (schema) {
        const result = schema.safeParse(retryData);
        if (!result.success) {
          console.error(
            `[API] Validation failed for ${endpoint}:`,
            result.error.issues,
          );
          throw new ApiError(422, `Invalid API response from ${endpoint}`, {
            detail: result.error.issues.map((i) => i.message).join(", "),
          });
        }
        return result.data;
      }
      return retryData as T;
    }
    // Refresh failed, redirect to login
    useAuthStore.getState().logout();
    window.location.href = "/login";
    throw new ApiError(401, "Session expired", {});
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw ApiError.fromResponse(response, errorData);
  }

  const data = await response.json();

  if (schema) {
    const result = schema.safeParse(data);
    if (!result.success) {
      console.error(
        `[API] Validation failed for ${endpoint}:`,
        result.error.issues,
      );
      throw new ApiError(422, `Invalid API response from ${endpoint}`, {
        detail: result.error.issues.map((i) => i.message).join(", "),
      });
    }
    return result.data;
  }

  return data as T;
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
