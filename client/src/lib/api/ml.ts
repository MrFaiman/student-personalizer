import { fetchApi, buildQueryString } from "./core";

import type {
  TrainResponse,
  StudentPrediction,
  BatchPredictionResponse,
  ModelStatusResponse,
} from "../types";

export const mlApi = {
  train: (params: { period?: string } = {}) =>
    fetchApi<TrainResponse>(`/api/ml/train${buildQueryString(params)}`, {
      method: "POST",
    }),

  predictStudent: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi<StudentPrediction>(
      `/api/ml/predict/${encodeURIComponent(studentTz)}${buildQueryString(params)}`,
    ),

  predictAll: (
    params: { period?: string; page?: number; page_size?: number } = {},
  ) =>
    fetchApi<BatchPredictionResponse>(
      `/api/ml/predict${buildQueryString(params)}`,
    ),

  getStatus: () => fetchApi<ModelStatusResponse>("/api/ml/status"),
};
