import { z } from "zod";

import { GradeHistogramBinSchema } from "./teacher";

export const SubjectListItemSchema = z.object({
    id: z.string().nullable(),
    name: z.string(),
    student_count: z.number(),
    average_grade: z.number().nullable(),
    teachers: z.array(z.string()),
});
export type SubjectListItem = z.infer<typeof SubjectListItemSchema>;

export const SubjectDetailStatsSchema = z.object({
    student_count: z.number(),
    average_grade: z.number().nullable(),
    at_risk_count: z.number(),
    classes_count: z.number(),
});
export type SubjectDetailStats = z.infer<typeof SubjectDetailStatsSchema>;

export const SubjectClassDetailSchema = z.object({
    id: z.string(),
    name: z.string(),
    student_count: z.number(),
    average_grade: z.number(),
    at_risk_count: z.number(),
});
export type SubjectClassDetail = z.infer<typeof SubjectClassDetailSchema>;

export const SubjectDetailResponseSchema = z.object({
    id: z.string(),
    name: z.string(),
    stats: SubjectDetailStatsSchema,
    teachers: z.array(z.string()),
    classes: z.array(SubjectClassDetailSchema),
    grade_histogram: z.array(GradeHistogramBinSchema),
});
export type SubjectDetailResponse = z.infer<typeof SubjectDetailResponseSchema>;

export const SubjectStatsResponseSchema = z.object({
    subject_name: z.string(),
    total_students: z.number(),
    average_grade: z.number().nullable(),
    distribution: z.object({
        "0-54": z.number(),
        "55-64": z.number(),
        "65-74": z.number(),
        "75-84": z.number(),
        "85-94": z.number(),
        "95-100": z.number(),
    }),
    teachers: z.array(z.string()),
});
export type SubjectStatsResponse = z.infer<typeof SubjectStatsResponseSchema>;
