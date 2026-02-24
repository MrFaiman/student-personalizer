import { z } from "zod";

export const LayerKPIsResponseSchema = z.object({
    layer_average: z.number().nullable(),
    avg_absences: z.number(),
    at_risk_students: z.number(),
    total_students: z.number(),
});
export type LayerKPIsResponse = z.infer<typeof LayerKPIsResponseSchema>;

export const ClassComparisonItemSchema = z.object({
    id: z.string(),
    class_name: z.string(),
    average_grade: z.number(),
    student_count: z.number(),
});
export type ClassComparisonItem = z.infer<typeof ClassComparisonItemSchema>;

export const HeatmapStudentSchema = z.object({
    student_name: z.string(),
    student_tz: z.string(),
    grades: z.record(z.string(), z.number().nullable()),
    average: z.number(),
});
export type HeatmapStudent = z.infer<typeof HeatmapStudentSchema>;

export const HeatmapDataSchema = z.object({
    subjects: z.array(z.string()),
    students: z.array(HeatmapStudentSchema),
});
export type HeatmapData = z.infer<typeof HeatmapDataSchema>;

export const StudentRankingSchema = z.object({
    student_name: z.string(),
    student_tz: z.string(),
    average: z.number(),
});
export type StudentRanking = z.infer<typeof StudentRankingSchema>;

export const TopBottomResponseSchema = z.object({
    top: z.array(StudentRankingSchema),
    bottom: z.array(StudentRankingSchema),
});
export type TopBottomResponse = z.infer<typeof TopBottomResponseSchema>;

export const TeacherStatsResponseSchema = z.object({
    teacher_name: z.string(),
    total_students: z.number(),
    average_grade: z.number(),
    distribution: z.object({
        fail: z.number(),
        medium: z.number(),
        good: z.number(),
        excellent: z.number(),
    }),
});
export type TeacherStatsResponse = z.infer<typeof TeacherStatsResponseSchema>;

export const SubjectGradeItemSchema = z.object({
    subject: z.string(),
    grade: z.number(),
});
export type SubjectGradeItem = z.infer<typeof SubjectGradeItemSchema>;

export const MetadataResponseSchema = z.object({
    periods: z.array(z.string()),
    grade_levels: z.array(z.string()),
    teachers: z.array(z.string()),
});
export type MetadataResponse = z.infer<typeof MetadataResponseSchema>;

export const PeriodComparisonItemSchema = z.object({
    id: z.string(),
    name: z.string(),
    period_a_average: z.number().nullable(),
    period_b_average: z.number().nullable(),
    change: z.number().nullable(),
    change_percent: z.number().nullable(),
    student_count_a: z.number(),
    student_count_b: z.number(),
    teacher_name: z.string().nullish(),
    subject: z.string().nullish(),
    class_name: z.string().nullish(),
});
export type PeriodComparisonItem = z.infer<typeof PeriodComparisonItemSchema>;

export const PeriodComparisonResponseSchema = z.object({
    comparison_type: z.enum(["class", "subject_teacher", "subject"]),
    period_a: z.string(),
    period_b: z.string(),
    data: z.array(PeriodComparisonItemSchema),
});
export type PeriodComparisonResponse = z.infer<typeof PeriodComparisonResponseSchema>;

export const RedStudentGroupSchema = z.object({
    id: z.string(),
    name: z.string(),
    red_student_count: z.number(),
    total_student_count: z.number(),
    percentage: z.number(),
    average_grade: z.number(),
});
export type RedStudentGroup = z.infer<typeof RedStudentGroupSchema>;

export const FailingSubjectSchema = z.object({
    subject: z.string(),
    teacher_name: z.string().nullable(),
    grade: z.number(),
});
export type FailingSubject = z.infer<typeof FailingSubjectSchema>;

export const RedStudentDetailSchema = z.object({
    student_tz: z.string(),
    student_name: z.string(),
    class_name: z.string().nullable(),
    grade_level: z.string().nullable(),
    average_grade: z.number(),
    failing_subjects: z.array(FailingSubjectSchema),
});
export type RedStudentDetail = z.infer<typeof RedStudentDetailSchema>;

export const RedStudentSegmentationSchema = z.object({
    total_red_students: z.number(),
    threshold: z.number(),
    by_class: z.array(RedStudentGroupSchema),
    by_layer: z.array(RedStudentGroupSchema),
    by_teacher: z.array(RedStudentGroupSchema),
    by_subject: z.array(RedStudentGroupSchema),
});
export type RedStudentSegmentation = z.infer<typeof RedStudentSegmentationSchema>;

export const RedStudentListResponseSchema = z.object({
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
    students: z.array(RedStudentDetailSchema),
});
export type RedStudentListResponse = z.infer<typeof RedStudentListResponseSchema>;

export const VersusSeriesItemSchema = z.object({
    id: z.string(),
    name: z.string(),
    value: z.number(),
    student_count: z.number(),
    subjects: z.array(z.string()).nullish(),
    teacher_name: z.string().nullish(),
});
export type VersusSeriesItem = z.infer<typeof VersusSeriesItemSchema>;

export const VersusChartDataSchema = z.object({
    comparison_type: z.enum(["class", "teacher", "layer"]),
    metric: z.string(),
    series: z.array(VersusSeriesItemSchema),
});
export type VersusChartData = z.infer<typeof VersusChartDataSchema>;

export const ClassOptionSchema = z.object({
    id: z.string(),
    class_name: z.string(),
    grade_level: z.string(),
});
export type ClassOption = z.infer<typeof ClassOptionSchema>;

export const TeacherOptionSchema = z.object({
    id: z.string().nullable(),
    name: z.string(),
    subjects: z.array(z.string()),
});
export type TeacherOption = z.infer<typeof TeacherOptionSchema>;

export const CascadingFilterOptionsSchema = z.object({
    classes: z.array(ClassOptionSchema),
    teachers: z.array(TeacherOptionSchema),
    subjects: z.array(z.string()),
});
export type CascadingFilterOptions = z.infer<typeof CascadingFilterOptionsSchema>;
