import { fetchApi, buildQueryString, API_BASE_URL } from "./core";
import { ApiError } from "../api-error";

import {
  ImportResponseSchema,
  ImportLogListResponseSchema,
  ImportLogResponseSchema,
} from "../types";

export const ingestionApi = {
  upload: async (
    file: File,
    params: { file_type?: "grades" | "events"; period?: string } = {},
  ) => {
    const formData = new FormData();
    formData.append("file", file);

    const queryString = buildQueryString(params);
    const response = await fetch(
      `${API_BASE_URL}/api/ingest/upload${queryString}`,
      {
        method: "POST",
        body: formData,
      },
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw ApiError.fromResponse(response, errorData);
    }

    const data = await response.json();
    const result = ImportResponseSchema.safeParse(data);
    if (!result.success) {
      console.error("[API] Validation failed for upload:", result.error.issues);
      throw new ApiError(422, "Invalid API response from upload", {
        detail: result.error.issues.map((i) => i.message).join(", "),
      });
    }
    return result.data;
  },

  getLogs: (params: { page?: number; page_size?: number } = {}) =>
    fetchApi(
      `/api/ingest/logs${buildQueryString(params)}`,
      undefined,
      ImportLogListResponseSchema,
    ),

  getLog: (batchId: string) =>
    fetchApi(
      `/api/ingest/logs/${encodeURIComponent(batchId)}`,
      undefined,
      ImportLogResponseSchema,
    ),

  deleteLog: (batchId: string) =>
    fetchApi<{ message: string; batch_id: string; records_deleted: number }>(
      `/api/ingest/logs/${encodeURIComponent(batchId)}`,
      { method: "DELETE" },
    ),
};
