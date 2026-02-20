import { z } from "zod";

export const TeacherListItemSchema = z.object({
    id: z.string(),
    name: z.string(),
    subjects: z.array(z.string()),
    student_count: z.number(),
    average_grade: z.number().nullable(),
});
export type TeacherListItem = z.infer<typeof TeacherListItemSchema>;

export const TeacherDetailStatsSchema = z.object({
    student_count: z.number(),
    average_grade: z.number(),
    at_risk_count: z.number(),
    classes_count: z.number(),
});
export type TeacherDetailStats = z.infer<typeof TeacherDetailStatsSchema>;

export const TeacherClassDetailSchema = z.object({
    id: z.string(),
    name: z.string(),
    student_count: z.number(),
    average_grade: z.number(),
    at_risk_count: z.number(),
});
export type TeacherClassDetail = z.infer<typeof TeacherClassDetailSchema>;

export const GradeHistogramBinSchema = z.object({
    grade: z.number(),
    count: z.number(),
});
export type GradeHistogramBin = z.infer<typeof GradeHistogramBinSchema>;

export const TeacherDetailResponseSchema = z.object({
    id: z.string(),
    name: z.string(),
    stats: TeacherDetailStatsSchema,
    subjects: z.array(z.string()),
    classes: z.array(TeacherClassDetailSchema),
    grade_histogram: z.array(GradeHistogramBinSchema),
});
export type TeacherDetailResponse = z.infer<typeof TeacherDetailResponseSchema>;
