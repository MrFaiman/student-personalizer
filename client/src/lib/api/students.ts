import { fetchApi, buildQueryString } from "./core";

import {
  StudentListResponseSchema,
  StudentDetailResponseSchema,
  GradeResponseSchema,
  AttendanceResponseSchema,
  ClassResponseSchema,
  DashboardStatsSchema,
} from "../types";
import { z } from "zod";

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
    fetchApi(`/api/students${buildQueryString(params)}`, undefined, StudentListResponseSchema),

  get: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi(
      `/api/students/${encodeURIComponent(studentTz)}${buildQueryString(params)}`,
      undefined,
      StudentDetailResponseSchema,
    ),

  getGrades: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi(
      `/api/students/${encodeURIComponent(studentTz)}/grades${buildQueryString(params)}`,
      undefined,
      z.array(GradeResponseSchema),
    ),

  getAttendance: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi(
      `/api/students/${encodeURIComponent(studentTz)}/attendance${buildQueryString(params)}`,
      undefined,
      z.array(AttendanceResponseSchema),
    ),

  getDashboardStats: (params: { class_id?: string; period?: string } = {}) =>
    fetchApi(
      `/api/students/dashboard${buildQueryString(params)}`,
      undefined,
      DashboardStatsSchema,
    ),

  getClasses: (params: { period?: string } = {}) =>
    fetchApi(
      `/api/classes${buildQueryString(params)}`,
      undefined,
      z.array(ClassResponseSchema),
    ),
};
