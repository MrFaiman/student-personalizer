import { fetchApi, buildQueryString } from "./core";

import {
  StudentListResponseSchema,
  StudentDetailResponseSchema,
  GradeResponseSchema,
  AttendanceResponseSchema,
  ClassResponseSchema,
  DashboardStatsSchema,
  StudentTimelineResponseSchema,
} from "../types";
import { z } from "zod";

export const studentsApi = {
  list: (
    params: {
      class_id?: string;
      search?: string;
      at_risk_only?: boolean;
      period?: string;
      year?: string;
      page?: number;
      page_size?: number;
      sort_by?: string;
      sort_order?: string;
    } = {},
  ) =>
    fetchApi(`/api/students${buildQueryString(params)}`, undefined, StudentListResponseSchema),

  get: (studentTz: string, params: { period?: string; year?: string } = {}) =>
    fetchApi(
      `/api/students/${encodeURIComponent(studentTz)}${buildQueryString(params)}`,
      undefined,
      StudentDetailResponseSchema,
    ),

  getGrades: (studentTz: string, params: { period?: string; year?: string } = {}) =>
    fetchApi(
      `/api/students/${encodeURIComponent(studentTz)}/grades${buildQueryString(params)}`,
      undefined,
      z.array(GradeResponseSchema),
    ),

  getAttendance: (studentTz: string, params: { period?: string; year?: string } = {}) =>
    fetchApi(
      `/api/students/${encodeURIComponent(studentTz)}/attendance${buildQueryString(params)}`,
      undefined,
      z.array(AttendanceResponseSchema),
    ),

  getDashboardStats: (params: { class_id?: string; period?: string; year?: string } = {}) =>
    fetchApi(
      `/api/students/dashboard${buildQueryString(params)}`,
      undefined,
      DashboardStatsSchema,
    ),

  getClasses: (params: { period?: string; year?: string } = {}) =>
    fetchApi(
      `/api/classes${buildQueryString(params)}`,
      undefined,
      z.array(ClassResponseSchema),
    ),

  getTimeline: (studentTz: string) =>
    fetchApi(
      `/api/students/${encodeURIComponent(studentTz)}/timeline`,
      undefined,
      StudentTimelineResponseSchema,
    ),
};
