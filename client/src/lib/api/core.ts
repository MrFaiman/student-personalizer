import type { z } from "zod";

import { ApiError } from "../api-error";

export const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
  schema?: z.ZodType<T>,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw ApiError.fromResponse(response, errorData);
  }

  const data = await response.json();

  if (schema) {
    const result = schema.safeParse(data);
    if (!result.success) {
      console.error(`[API] Validation failed for ${endpoint}:`, result.error.issues);
      throw new ApiError(
        422,
        `Invalid API response from ${endpoint}`,
        { detail: result.error.issues.map((i) => i.message).join(", ") },
      );
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
