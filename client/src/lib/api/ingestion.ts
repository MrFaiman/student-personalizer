import { fetchApi, buildQueryString, API_BASE_URL } from "./core";
import { ApiError } from "../api-error";
import { useAuthStore } from "../auth-store";

import type {
  ImportResponse,
  ImportLogListResponse,
  ImportLogResponse,
} from "../types";

export const ingestionApi = {
  upload: async (
    file: File,
    params: { file_type?: "grades" | "events"; period?: string } = {},
  ): Promise<ImportResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    const queryString = buildQueryString(params);
    const token = useAuthStore.getState().token;
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    const response = await fetch(
      `${API_BASE_URL}/api/ingest/upload${queryString}`,
      {
        method: "POST",
        headers,
        body: formData,
      },
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw ApiError.fromResponse(response, errorData);
    }

    return response.json();
  },

  getLogs: (params: { page?: number; page_size?: number } = {}) =>
    fetchApi<ImportLogListResponse>(
      `/api/ingest/logs${buildQueryString(params)}`,
    ),

  getLog: (batchId: string) =>
    fetchApi<ImportLogResponse>(
      `/api/ingest/logs/${encodeURIComponent(batchId)}`,
    ),

  deleteLog: (batchId: string) =>
    fetchApi<{ message: string; batch_id: string; records_deleted: number }>(
      `/api/ingest/logs/${encodeURIComponent(batchId)}`,
      { method: "DELETE" },
    ),

  resetDatabase: (params: { reload_data?: boolean } = { reload_data: true }) =>
    fetchApi<{
      message: string;
      students_loaded: number;
      events_loaded: number;
    }>(`/api/ingest/reset${buildQueryString(params)}`, { method: "POST" }),
};
