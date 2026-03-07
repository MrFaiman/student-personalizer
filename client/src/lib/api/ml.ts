import { fetchApi, buildQueryString } from "./core";

import {
  TrainResponseSchema,
  StudentPredictionSchema,
  BatchPredictionResponseSchema,
  ModelStatusResponseSchema,
} from "../types";

export const mlApi = {
  train: (params: { year?: string; period?: string } = {}) =>
    fetchApi(`/api/ml/train${buildQueryString(params)}`, {
      method: "POST",
    }, TrainResponseSchema),

  predictStudent: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi(
      `/api/ml/predict/${encodeURIComponent(studentTz)}${buildQueryString(params)}`,
      undefined,
      StudentPredictionSchema,
    ),

  predictAll: (
    params: { year?: string; period?: string; page?: number; page_size?: number; sort_by?: string; sort_order?: string } = {},
  ) =>
    fetchApi(
      `/api/ml/predict${buildQueryString(params)}`,
      undefined,
      BatchPredictionResponseSchema,
    ),

  getStatus: () =>
    fetchApi("/api/ml/status", undefined, ModelStatusResponseSchema),
};
