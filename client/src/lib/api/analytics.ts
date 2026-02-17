import { fetchApi, buildQueryString } from "./core";

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
  PeriodComparisonResponse,
  RedStudentSegmentation,
  RedStudentListResponse,
  VersusChartData,
  CascadingFilterOptions,
} from "../types";

export const analyticsApi = {
  getKPIs: (params: { period?: string; grade_level?: string } = {}) =>
    fetchApi<LayerKPIsResponse>(
      `/api/analytics/kpis${buildQueryString(params)}`,
    ),

  getClassComparison: (
    params: { period?: string; grade_level?: string } = {},
  ) =>
    fetchApi<ClassComparisonItem[]>(
      `/api/analytics/class-comparison${buildQueryString(params)}`,
    ),

  getClassHeatmap: (classId: string, params: { period?: string } = {}) =>
    fetchApi<HeatmapData>(
      `/api/classes/${classId}/heatmap${buildQueryString(params)}`,
    ),

  getClassRankings: (
    classId: string,
    params: { period?: string; top_n?: number; bottom_n?: number } = {},
  ) =>
    fetchApi<TopBottomResponse>(
      `/api/classes/${classId}/rankings${buildQueryString(params)}`,
    ),

  getTeacherStats: (teacherName: string, params: { period?: string } = {}) =>
    fetchApi<TeacherStatsResponse>(
      `/api/teachers/${encodeURIComponent(teacherName)}/stats${buildQueryString(params)}`,
    ),

  getStudentRadar: (studentTz: string, params: { period?: string } = {}) =>
    fetchApi<SubjectGradeItem[]>(
      `/api/analytics/student/${encodeURIComponent(studentTz)}/radar${buildQueryString(params)}`,
    ),

  getTeachers: (params: { period?: string } = {}) =>
    fetchApi<string[]>(`/api/teachers${buildQueryString(params)}`),

  getTeachersList: (params: { period?: string; grade_level?: string } = {}) =>
    fetchApi<TeacherListItem[]>(
      `/api/teachers/list${buildQueryString(params)}`,
    ),

  getTeacherDetail: (teacherId: string, params: { period?: string } = {}) =>
    fetchApi<TeacherDetailResponse>(
      `/api/teachers/${encodeURIComponent(teacherId)}/detail${buildQueryString(params)}`,
    ),

  getMetadata: () => fetchApi<MetadataResponse>("/api/analytics/metadata"),

  getPeriodComparison: (params: {
    period_a: string;
    period_b: string;
    comparison_type?: "class" | "subject_teacher" | "subject";
    grade_level?: string;
    class_id?: string;
  }) =>
    fetchApi<PeriodComparisonResponse>(
      `/api/analytics/period-comparison${buildQueryString(params)}`,
    ),

  getRedStudentSegmentation: (
    params: {
      period?: string;
      grade_level?: string;
    } = {},
  ) =>
    fetchApi<RedStudentSegmentation>(
      `/api/analytics/red-students/segmentation${buildQueryString(params)}`,
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
    fetchApi<RedStudentListResponse>(
      `/api/analytics/red-students/list${buildQueryString(params)}`,
    ),

  getVersusComparison: (params: {
    comparison_type: "class" | "teacher" | "layer";
    entity_ids: string;
    period?: string;
    metric?: "average_grade" | "at_risk_count";
  }) =>
    fetchApi<VersusChartData>(
      `/api/analytics/versus${buildQueryString(params)}`,
    ),

  getCascadingFilterOptions: (
    params: {
      grade_level?: string;
      class_id?: string;
      period?: string;
    } = {},
  ) =>
    fetchApi<CascadingFilterOptions>(
      `/api/analytics/filter-options${buildQueryString(params)}`,
    ),
};
