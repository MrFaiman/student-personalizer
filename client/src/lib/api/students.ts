import { fetchApi, buildQueryString } from "./core";

import type {
  StudentListResponse,
  StudentDetailResponse,
  GradeResponse,
  AttendanceResponse,
  ClassResponse,
  DashboardStats,
} from "../types";

export const studentsApi = {
  list: (
    params: {
      class_id?: string;
      search?: string;
      at_risk_only?: boolean;
      period?: string;
      page?: number;
      page_size?: number;
    } = {},
  ) =>
    fetchApi<StudentListResponse>(`/api/students${buildQueryString(params)}`),

  get: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi<StudentDetailResponse>(
      `/api/students/${encodeURIComponent(studentTz)}${buildQueryString(params)}`,
    ),

  getGrades: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi<GradeResponse[]>(
      `/api/students/${encodeURIComponent(studentTz)}/grades${buildQueryString(params)}`,
    ),

  getAttendance: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi<AttendanceResponse[]>(
      `/api/students/${encodeURIComponent(studentTz)}/attendance${buildQueryString(params)}`,
    ),

  getDashboardStats: (params: { class_id?: string; period?: string } = {}) =>
    fetchApi<DashboardStats>(
      `/api/students/dashboard${buildQueryString(params)}`,
    ),

  getClasses: (params: { period?: string } = {}) =>
    fetchApi<ClassResponse[]>(
      `/api/classes${buildQueryString(params)}`,
    ),
};
