import { fetchApi, buildQueryString, API_BASE_URL } from "./core";
import { ApiError } from "../api-error";
import {
    OpenDayUploadResponseSchema,
    OpenDayRegistrationListResponseSchema,
    OpenDayImportListResponseSchema,
    OpenDayStatsSchema,
} from "../types";

export const openDayApi = {
    upload: async (file: File) => {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(`${API_BASE_URL}/api/open-day/upload`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw ApiError.fromResponse(response, errorData);
        }

        const data = await response.json();
        const result = OpenDayUploadResponseSchema.safeParse(data);
        if (!result.success) {
            console.error("[API] Validation failed for open-day upload:", result.error.issues);
            throw new ApiError(422, "Invalid API response from open-day upload", {
                detail: result.error.issues.map((i) => i.message).join(", "),
            });
        }
        return result.data;
    },

    getRegistrations: (params: {
        page?: number;
        page_size?: number;
        search?: string;
        track?: string;
        grade?: string;
        import_id?: number;
    } = {}) =>
        fetchApi(
            `/api/open-day/registrations${buildQueryString(params)}`,
            undefined,
            OpenDayRegistrationListResponseSchema,
        ),

    getStats: () =>
        fetchApi("/api/open-day/stats", undefined, OpenDayStatsSchema),

    getImports: () =>
        fetchApi("/api/open-day/imports", undefined, OpenDayImportListResponseSchema),

    deleteImport: (importId: number) =>
        fetchApi<{ message: string; import_id: number }>(
            `/api/open-day/imports/${importId}`,
            { method: "DELETE" },
        ),

    resetAll: () =>
        fetchApi<{ message: string }>("/api/open-day/reset", { method: "DELETE" }),
};
