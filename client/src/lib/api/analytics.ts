import { fetchApi, buildQueryString } from "./core";
import { z } from "zod";

import {
  LayerKPIsResponseSchema,
  ClassComparisonItemSchema,
  HeatmapDataSchema,
  TopBottomResponseSchema,
  TeacherStatsResponseSchema,
  SubjectGradeItemSchema,
  MetadataResponseSchema,
  TeacherListItemSchema,
  TeacherDetailResponseSchema,
  PeriodComparisonResponseSchema,
  RedStudentSegmentationSchema,
  RedStudentListResponseSchema,
  VersusChartDataSchema,
  CascadingFilterOptionsSchema,
} from "../types";

export const analyticsApi = {
  getKPIs: (params: { period?: string; grade_level?: string } = {}) =>
    fetchApi(
      `/api/analytics/kpis${buildQueryString(params)}`,
      undefined,
      LayerKPIsResponseSchema,
    ),

  getClassComparison: (
    params: { period?: string; grade_level?: string } = {},
  ) =>
    fetchApi(
      `/api/analytics/class-comparison${buildQueryString(params)}`,
      undefined,
      z.array(ClassComparisonItemSchema),
    ),

  getClassHeatmap: (classId: string, params: { period?: string } = {}) =>
    fetchApi(
      `/api/classes/${classId}/heatmap${buildQueryString(params)}`,
      undefined,
      HeatmapDataSchema,
    ),

  getClassRankings: (
    classId: string,
    params: { period?: string; top_n?: number; bottom_n?: number } = {},
  ) =>
    fetchApi(
      `/api/classes/${classId}/rankings${buildQueryString(params)}`,
      undefined,
      TopBottomResponseSchema,
    ),

  getTeacherStats: (teacherName: string, params: { period?: string } = {}) =>
    fetchApi(
      `/api/teachers/${encodeURIComponent(teacherName)}/stats${buildQueryString(params)}`,
      undefined,
      TeacherStatsResponseSchema,
    ),

  getStudentRadar: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi(
      `/api/analytics/student/${encodeURIComponent(studentTz)}/radar${buildQueryString(params)}`,
      undefined,
      z.array(SubjectGradeItemSchema),
    ),

  getTeachers: (params: { period?: string } = {}) =>
    fetchApi<string[]>(`/api/teachers${buildQueryString(params)}`),

  getTeachersList: (params: { period?: string; grade_level?: string } = {}) =>
    fetchApi(
      `/api/teachers/list${buildQueryString(params)}`,
      undefined,
      z.array(TeacherListItemSchema),
    ),

  getTeacherDetail: (teacherId: string, params: { period?: string } = {}) =>
    fetchApi(
      `/api/teachers/${encodeURIComponent(teacherId)}/detail${buildQueryString(params)}`,
      undefined,
      TeacherDetailResponseSchema,
    ),

  getMetadata: () =>
    fetchApi("/api/analytics/metadata", undefined, MetadataResponseSchema),

  getPeriodComparison: (params: {
    period_a: string;
    period_b: string;
    comparison_type?: "class" | "subject_teacher" | "subject";
    grade_level?: string;
    class_id?: string;
  }) =>
    fetchApi(
      `/api/analytics/period-comparison${buildQueryString(params)}`,
      undefined,
      PeriodComparisonResponseSchema,
    ),

  getRedStudentSegmentation: (
    params: {
      period?: string;
      grade_level?: string;
    } = {},
  ) =>
    fetchApi(
      `/api/analytics/red-students/segmentation${buildQueryString(params)}`,
      undefined,
      RedStudentSegmentationSchema,
    ),

  getRedStudentList: (
    params: {
      period?: string;
      grade_level?: string;
      class_id?: string;
      teacher_name?: string;
      subject?: string;
      page?: number;
      page_size?: number;
    } = {},
  ) =>
    fetchApi(
      `/api/analytics/red-students/list${buildQueryString(params)}`,
      undefined,
      RedStudentListResponseSchema,
    ),

  getVersusComparison: (params: {
    comparison_type: "class" | "teacher" | "layer";
    entity_ids: string;
    period?: string;
    metric?: "average_grade" | "at_risk_count";
  }) =>
    fetchApi(
      `/api/analytics/versus${buildQueryString(params)}`,
      undefined,
      VersusChartDataSchema,
    ),

  getCascadingFilterOptions: (
    params: {
      grade_level?: string;
      class_id?: string;
      period?: string;
    } = {},
  ) =>
    fetchApi(
      `/api/analytics/filter-options${buildQueryString(params)}`,
      undefined,
      CascadingFilterOptionsSchema,
    ),
};
