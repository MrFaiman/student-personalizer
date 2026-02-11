/**
 * API client for the pedagogical dashboard backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorData.detail || `HTTP error ${response.status}`
    );
  }

  return response.json();
}

// Query params helper
function buildQueryString(params: Record<string, string | number | boolean | undefined>): string {
  const searchParams = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") searchParams.set(k, String(v));
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

// Analytics API

import type {
  LayerKPIsResponse,
  ClassComparisonItem,
  HeatmapData,
  TopBottomResponse,
  TeacherStatsResponse,
  SubjectGradeItem,
  MetadataResponse,
  TeacherListItem,
  TeacherDetailResponse,
} from "./types";

export const analyticsApi = {
  getKPIs: (params: { period?: string; grade_level?: string } = {}) =>
    fetchApi<LayerKPIsResponse>(`/api/analytics/kpis${buildQueryString(params)}`),

  getClassComparison: (params: { period?: string; grade_level?: string } = {}) =>
    fetchApi<ClassComparisonItem[]>(`/api/analytics/class-comparison${buildQueryString(params)}`),

  getClassHeatmap: (classId: string, params: { period?: string } = {}) =>
    fetchApi<HeatmapData>(`/api/analytics/class/${classId}/heatmap${buildQueryString(params)}`),

  getClassRankings: (
    classId: string,
    params: { period?: string; top_n?: number; bottom_n?: number } = {}
  ) =>
    fetchApi<TopBottomResponse>(
      `/api/analytics/class/${classId}/rankings${buildQueryString(params)}`
    ),

  getTeacherStats: (teacherName: string, params: { period?: string } = {}) =>
    fetchApi<TeacherStatsResponse>(
      `/api/analytics/teacher/${encodeURIComponent(teacherName)}/stats${buildQueryString(params)}`
    ),

  getStudentRadar: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi<SubjectGradeItem[]>(
      `/api/analytics/student/${encodeURIComponent(studentTz)}/radar${buildQueryString(params)}`
    ),

  getTeachers: (params: { period?: string } = {}) =>
    fetchApi<string[]>(`/api/analytics/teachers${buildQueryString(params)}`),

  getTeachersList: (params: { period?: string; grade_level?: string } = {}) =>
    fetchApi<TeacherListItem[]>(`/api/analytics/teachers/list${buildQueryString(params)}`),

  getTeacherDetail: (teacherId: string, params: { period?: string } = {}) =>
    fetchApi<TeacherDetailResponse>(
      `/api/analytics/teacher/${encodeURIComponent(teacherId)}/detail${buildQueryString(params)}`
    ),

  getMetadata: () => fetchApi<MetadataResponse>("/api/analytics/metadata"),
};

// Students API

import type {
  StudentListResponse,
  StudentDetailResponse,
  GradeResponse,
  AttendanceResponse,
  ClassResponse,
  DashboardStats,
} from "./types";

export const studentsApi = {
  list: (
    params: {
      class_id?: string;
      search?: string;
      at_risk_only?: boolean;
      period?: string;
      page?: number;
      page_size?: number;
    } = {}
  ) => fetchApi<StudentListResponse>(`/api/students${buildQueryString(params)}`),

  get: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi<StudentDetailResponse>(
      `/api/students/${encodeURIComponent(studentTz)}${buildQueryString(params)}`
    ),

  getGrades: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi<GradeResponse[]>(
      `/api/students/${encodeURIComponent(studentTz)}/grades${buildQueryString(params)}`
    ),

  getAttendance: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi<AttendanceResponse[]>(
      `/api/students/${encodeURIComponent(studentTz)}/attendance${buildQueryString(params)}`
    ),

  getDashboardStats: (params: { class_id?: string; period?: string } = {}) =>
    fetchApi<DashboardStats>(`/api/students/dashboard${buildQueryString(params)}`),

  getClasses: (params: { period?: string } = {}) =>
    fetchApi<ClassResponse[]>(`/api/students/classes${buildQueryString(params)}`),
};

// Ingestion API

import type { ImportResponse, ImportLogListResponse, ImportLogResponse } from "./types";

export const ingestionApi = {
  upload: async (
    file: File,
    params: { file_type?: "grades" | "events"; period?: string } = {}
  ): Promise<ImportResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    const queryString = buildQueryString(params);
    const response = await fetch(`${API_BASE_URL}/api/ingest/upload${queryString}`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(response.status, errorData.detail || `HTTP error ${response.status}`);
    }

    return response.json();
  },

  getLogs: (params: { page?: number; page_size?: number } = {}) =>
    fetchApi<ImportLogListResponse>(`/api/ingest/logs${buildQueryString(params)}`),

  getLog: (batchId: string) =>
    fetchApi<ImportLogResponse>(`/api/ingest/logs/${encodeURIComponent(batchId)}`),

  deleteLog: (batchId: string) =>
    fetchApi<{ message: string; batch_id: string; records_deleted: number }>(
      `/api/ingest/logs/${encodeURIComponent(batchId)}`,
      { method: "DELETE" }
    ),

  resetDatabase: (params: { reload_data?: boolean } = { reload_data: true }) =>
    fetchApi<{ message: string; students_loaded: number; events_loaded: number }>(
      `/api/ingest/reset${buildQueryString(params)}`,
      { method: "POST" }
    ),
};

// ML API

import type {
  TrainResponse,
  StudentPrediction,
  BatchPredictionResponse,
  ModelStatusResponse,
} from "./types";

export const mlApi = {
  train: (params: { period?: string } = {}) =>
    fetchApi<TrainResponse>(`/api/ml/train${buildQueryString(params)}`, { method: "POST" }),

  predictStudent: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi<StudentPrediction>(
      `/api/ml/predict/${encodeURIComponent(studentTz)}${buildQueryString(params)}`
    ),

  predictAll: (params: { period?: string; page?: number; page_size?: number } = {}) =>
    fetchApi<BatchPredictionResponse>(`/api/ml/predict${buildQueryString(params)}`),

  getStatus: () => fetchApi<ModelStatusResponse>("/api/ml/status"),
};

export { ApiError };
